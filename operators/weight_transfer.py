"""Explicit, undoable surface based transfer from an armature's source mesh."""

from __future__ import annotations

import bpy  # type: ignore
import bmesh  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore

from ..blender.weight_transfer import closest_triangle_weights, combine_weight, crosses_declared_plane


def _mesh(obj):
    return obj is not None and obj.type == 'MESH'


def _armature(obj):
    return obj is not None and obj.type == 'ARMATURE'


def _group_weight(group, index):
    if group is None:
        return 0.0
    try:
        return group.weight(index)
    except RuntimeError:
        return 0.0


def _clear_mappings(state, _context):
    # A confirmation belongs to the selected A/rig/B tuple, not just a name.
    state.mappings.clear()


def _unconfirm_mapping(mapping, _context):
    mapping.confirmed = False


class VAPB_PG_weight_mapping(bpy.types.PropertyGroup):
    source_name: bpy.props.StringProperty(name="A のグループ", update=_unconfirm_mapping)
    target_name: bpy.props.StringProperty(name="B のグループ", update=_unconfirm_mapping)
    confirmed: bpy.props.BoolProperty(name="この対応を使用", default=False)


class VAPB_PG_weight_transfer(bpy.types.PropertyGroup):
    source: bpy.props.PointerProperty(name="A: 元メッシュ", type=bpy.types.Object, poll=lambda self, obj: _mesh(obj), update=_clear_mappings)
    armature: bpy.props.PointerProperty(name="A: 参照アーマチュア", type=bpy.types.Object, poll=lambda self, obj: _armature(obj), update=_clear_mappings)
    target: bpy.props.PointerProperty(name="B: 転送先メッシュ", type=bpy.types.Object, poll=lambda self, obj: _mesh(obj), update=_clear_mappings)
    mappings: bpy.props.CollectionProperty(type=VAPB_PG_weight_mapping)
    scope: bpy.props.EnumProperty(name="B の対象頂点", items=(
        ('ALL', '全頂点', 'B の全頂点を対象にする'),
        ('SELECTED', '選択頂点のみ', 'B の選択済み頂点だけを対象にする'),
    ), default='ALL')
    mode: bpy.props.EnumProperty(name="方針", items=(
        ('REPLACE', '置換', '対応する B の既存ウェイトを補間値で置換'),
        ('MERGE', '大きい値を保持', '対応する各ウェイトの既存値と補間値の大きい方を採用'),
        ('FILL_MISSING', '未設定のみ補充', '既存値がゼロの頂点にだけ補間値を追加'),
    ), default='REPLACE')
    blend: bpy.props.FloatProperty(name="適用率", min=0.0, max=1.0, default=1.0)
    max_distance: bpy.props.FloatProperty(name="最大距離 (ワールド単位)", min=0.0, default=0.05, precision=4,
        description="B の頂点から A の表面までのワールド空間距離。超過は変更しない")
    guard_declared_plane: bpy.props.BoolProperty(
        name="宣言した左右境界で越境を保護", default=False,
        description="ユーザーが A の参照アーマチュアのローカル X=0 を左右境界と宣言した場合だけ有効")


def register_weight_transfer_properties():
    bpy.types.Scene.vapb_weight_transfer = bpy.props.PointerProperty(type=VAPB_PG_weight_transfer)


def unregister_weight_transfer_properties():
    del bpy.types.Scene.vapb_weight_transfer


def _validate(state):
    a, rig, b = state.source, state.armature, state.target
    if not _mesh(a) or not _mesh(b) or not _armature(rig) or a == b:
        raise ValueError("異なる A/B メッシュと A のアーマチュアを選択してください")
    if b.data.users > 1 or len(b.users_scene) > 1 or b.library or b.data.library:
        raise ValueError("B のメッシュデータが共有/リンクされています。明示的に単一ユーザー化してから再実行してください")
    if a.parent != rig and not any(m.type == 'ARMATURE' and m.object == rig for m in a.modifiers):
        raise ValueError("指定アーマチュアは A の親または Armature モディファイアである必要があります")
    selected = [m for m in state.mappings if m.confirmed]
    if not selected:
        raise ValueError("骨グループの対応を個別に確認してください")
    bone_names = set(rig.data.bones.keys())
    target_names = set()
    for m in selected:
        if m.source_name not in bone_names or a.vertex_groups.get(m.source_name) is None:
            raise ValueError("A の骨グループ対応が無効です。対応を更新してください")
        if not m.target_name.strip() or m.target_name in target_names:
            raise ValueError("B のグループ名は空欄や重複にできません")
        target_names.add(m.target_name)
    return a, b, selected


def calculate_transfer(state):
    """Return a weight plan and measured counts; no Blender datablock writes."""
    a, b, mappings = _validate(state)
    mesh = a.data
    mesh.calc_loop_triangles()
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    if not triangles:
        raise ValueError("A に表面三角形がありません")
    coords = [tuple(a.matrix_world @ v.co) for v in mesh.vertices]
    bvh = BVHTree.FromPolygons(coords, triangles, all_triangles=True)
    groups = [(m.source_name, m.target_name, a.vertex_groups[m.source_name]) for m in mappings]
    plan = []
    distances = []
    skipped_distance = 0
    cross_plane_indices = []
    locked = 0
    rig_inverse = state.armature.matrix_world.inverted() if state.guard_declared_plane else None
    vertices = [v for v in b.data.vertices if state.scope == 'ALL' or v.select]
    if not vertices:
        raise ValueError("B の対象頂点がありません。選択範囲を確認してください")
    unresolved_indices = []
    for vertex in vertices:
        point = b.matrix_world @ vertex.co
        hit, _normal, triangle_index, distance = bvh.find_nearest(point)
        if hit is None or distance > state.max_distance:
            skipped_distance += 1
            unresolved_indices.append(vertex.index)
            continue
        if rig_inverse is not None and crosses_declared_plane(
            (rig_inverse @ point).x, (rig_inverse @ hit).x
        ):
            cross_plane_indices.append(vertex.index)
            continue
        tri = triangles[triangle_index]
        bary = closest_triangle_weights(tuple(point), *(coords[i] for i in tri))
        distances.append(distance)
        for source_name, target_name, source_group in groups:
            target_group = b.vertex_groups.get(target_name)
            if target_group is not None and target_group.lock_weight:
                locked += 1
                continue
            sampled = sum(bary[j] * _group_weight(source_group, tri[j]) for j in range(3))
            old = _group_weight(target_group, vertex.index)
            new = combine_weight(old, sampled, state.mode, state.blend)
            if new != old:
                plan.append((target_name, vertex.index, new))
    return plan, {
        'matched': len(distances), 'unresolved': skipped_distance, 'locked': locked,
        'edits': len(plan), 'max_distance': max(distances, default=0.0),
        'unresolved_indices': tuple(unresolved_indices),
        'cross_plane': len(cross_plane_indices), 'cross_plane_indices': tuple(cross_plane_indices),
        'scope_vertices': len(vertices),
    }


class VAPB_OT_weight_mappings(bpy.types.Operator):
    bl_idname = "vapb.weight_mappings"
    bl_label = "A の骨グループを読み込む"
    bl_description = "A の骨グループを列挙します。名前が一致しても使用は個別確認が必要です"

    def execute(self, context):
        state = context.scene.vapb_weight_transfer
        a, rig = state.source, state.armature
        if not _mesh(a) or not _armature(rig):
            self.report({'ERROR'}, "A と参照アーマチュアを選択してください")
            return {'CANCELLED'}
        state.mappings.clear()
        for group in a.vertex_groups:
            if group.name in rig.data.bones:
                m = state.mappings.add()
                m.source_name = group.name
                m.target_name = group.name  # suggestion only; confirmed remains false
        self.report({'INFO'}, f"骨グループ候補: {len(state.mappings)}。各対応を確認してください")
        return {'FINISHED'}


class VAPB_OT_weight_preview(bpy.types.Operator):
    bl_idname = "vapb.weight_preview"
    bl_label = "転送をプレビュー"
    bl_description = "ウェイトを変更せず、距離と変更予定件数を確認"

    def execute(self, context):
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "オブジェクトモードで実行してください")
            return {'CANCELLED'}
        try:
            _plan, stats = calculate_transfer(context.scene.vapb_weight_transfer)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, _summary(stats))
        return {'FINISHED'}


class VAPB_OT_weight_select_unresolved(bpy.types.Operator):
    bl_idname = "vapb.weight_select_unresolved"
    bl_label = "距離超過・境界警告頂点を選択表示"
    bl_description = "明示的に B の距離超過・境界越境頂点を選択し、編集モードで表示します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "オブジェクトモードで実行してください")
            return {'CANCELLED'}
        try:
            _plan, stats = calculate_transfer(context.scene.vapb_weight_transfer)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        target = context.scene.vapb_weight_transfer.target
        if target.name not in context.view_layer.objects:
            self.report({'ERROR'}, "B は現在のビューレイヤーにありません")
            return {'CANCELLED'}
        unresolved = set(stats['unresolved_indices']) | set(stats['cross_plane_indices'])
        for vertex in target.data.vertices:
            vertex.select = vertex.index in unresolved
        for selected in context.selected_objects:
            selected.select_set(False)
        context.view_layer.objects.active = target
        target.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        context.tool_settings.mesh_select_mode = (True, False, False)
        edit_mesh = bmesh.from_edit_mesh(target.data)
        for vertex in edit_mesh.verts:
            vertex.select_set(vertex.index in unresolved)
        bmesh.update_edit_mesh(target.data)
        self.report({'INFO'}, f"距離超過 {stats['unresolved']} / 境界越境 {stats['cross_plane']} 頂点を B で選択表示しました")
        return {'FINISHED'}


def _summary(stats):
    return (f"対象 {stats['scope_vertices']} / 一致 {stats['matched']} / 距離超過・未解決 {stats['unresolved']} / "
            f"宣言境界越境 {stats['cross_plane']} / "
            f"ロック保護 {stats['locked']} / 変更予定 {stats['edits']} / "
            f"一致最大距離 {stats['max_distance']:.5f} ワールド単位")


def apply_transfer_plan(target, plan):
    """Apply a complete plan; restore touched weights/groups if Blender raises."""
    previous = {}
    created = set()
    for name, index, _weight in plan:
        group = target.vertex_groups.get(name)
        key = (name, index)
        if key not in previous:
            if group is None:
                previous[key] = None
            else:
                try:
                    previous[key] = group.weight(index)
                except RuntimeError:
                    previous[key] = None
    try:
        for name, index, weight in plan:
            group = target.vertex_groups.get(name)
            if group is None:
                group = target.vertex_groups.new(name=name)
                created.add(name)
            if weight == 0.0:
                group.remove([index])
            else:
                group.add([index], weight, 'REPLACE')
    except Exception:
        for (name, index), old in previous.items():
            if name in created:
                continue
            group = target.vertex_groups.get(name)
            if group is not None:
                if old is None:
                    try:
                        group.weight(index)
                    except RuntimeError:
                        pass
                    else:
                        group.remove([index])
                else:
                    group.add([index], old, 'REPLACE')
        for name in created:
            group = target.vertex_groups.get(name)
            if group is not None:
                target.vertex_groups.remove(group)
        raise


class VAPB_OT_weight_apply(bpy.types.Operator):
    bl_idname = "vapb.weight_apply"
    bl_label = "B にウェイトを適用"
    bl_description = "確認済みの対応だけを B に適用します。Undo 対応"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        state = context.scene.vapb_weight_transfer
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "オブジェクトモードで実行してください")
            return {'CANCELLED'}
        try:
            plan, stats = calculate_transfer(state)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        try:
            apply_transfer_plan(state.target, plan)
        except Exception as exc:
            self.report({'ERROR'}, f"適用に失敗しました: {type(exc).__name__}。復旧状態を確認してください")
            return {'CANCELLED'}
        self.report({'INFO'}, _summary(stats))
        return {'FINISHED'}


WEIGHT_TRANSFER_CLASSES = (
    VAPB_PG_weight_mapping, VAPB_PG_weight_transfer,
    VAPB_OT_weight_mappings, VAPB_OT_weight_preview,
    VAPB_OT_weight_select_unresolved, VAPB_OT_weight_apply,
)
