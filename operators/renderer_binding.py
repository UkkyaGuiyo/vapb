"""Explicit, undoable Blender confirmation of one Renderer occurrence."""

from __future__ import annotations

import json

import bpy

from ..blender.renderer_binding import (BindingError, validate_binding,
                                        validate_existing_binding, make_skin_binding,
                                        _skin_ids)


def _display_error(error):
    message = str(error)
    if message.startswith("共有メッシュです"):
        return message
    if message.startswith("Material slot "):
        return "対象スロットの素材を一意に特定できません。素材の出所とローカルIDを確認してください"
    if "Material" in message or "material" in message:
        return "素材情報が未確定または不完全です。バインドは実行されませんでした"
    if "Root" in message or "root" in message or "projection" in message:
        return "選択したルートとRendererの出所が一致しません"
    if "owner" in message or "Owner" in message:
        return "Rendererの所有オブジェクトを一意に確認できません"
    if "armature" in message.lower():
        return "Armatureの対象または出所を確認できません"
    if "receipt" in message.lower() or "Mesh" in message or "mesh" in message:
        return "メッシュの出所または受領情報を確認できません"
    if "already" in message or "Non-unique" in message:
        return "このRendererまたはオブジェクトは既に使用中、または識別子が重複しています"
    return "Rendererとメッシュの対応を確認できません"


def projection_records(root):
    raw = root.get("_vapb_renderer_occurrences", "") if root else ""
    try:
        projection = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return []
    return projection.get("records", []) if isinstance(projection, dict) else []


def _confirmed_renderer(mesh, root):
    raw = mesh.get("_vapb_renderer_binding")
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError) as exc:
        raise BindingError("Renderer binding is malformed") from exc
    if not isinstance(value, dict):
        raise BindingError("Renderer binding is missing")
    return validate_existing_binding(value, root, mesh, bpy.data.objects)


def _unconfirm_skin_row(row, _context):
    row.confirmed = False


class VAPB_PG_skin_mapping_row(bpy.types.PropertyGroup):
    target_transform_file_id: bpy.props.StringProperty()
    display_name: bpy.props.StringProperty()
    target_name: bpy.props.StringProperty(update=_unconfirm_skin_row)
    confirmed: bpy.props.BoolProperty(default=False)


class VAPB_PG_skin_mapping_state(bpy.types.PropertyGroup):
    renderer_occurrence_id: bpy.props.StringProperty()
    root_context_id: bpy.props.StringProperty()
    mesh_realization_id: bpy.props.StringProperty()
    source_revision_sha256: bpy.props.StringProperty()
    root_bone_target_transform_file_id: bpy.props.StringProperty()
    rows: bpy.props.CollectionProperty(type=VAPB_PG_skin_mapping_row)


class VAPB_OT_load_skin_mappings(bpy.types.Operator):
    bl_idname = "vapb.load_skin_mappings"
    bl_label = "Bone対応を確認"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = context.scene.vapb_renderer_root
        mesh = context.scene.vapb_renderer_mesh
        state = context.scene.vapb_skin_mapping
        state.rows.clear()
        state.renderer_occurrence_id = ""
        if root is None or mesh is None:
            self.report({"ERROR"}, "Prefabルートとメッシュを選択してください")
            return {"CANCELLED"}
        try:
            renderer = _confirmed_renderer(mesh, root)
            record = renderer["occurrence"]
            if record.get("renderer_class_id") != 137:
                raise BindingError("Skinned Rendererが必要です")
            ids, root_id = _skin_ids(record)
            labels = {row["transform_file_id"]: row["display_name"] for row in record["skin"]["bones"]}
            labels.setdefault(root_id, record["skin"].get("root_bone_display_name", "Root Bone"))
            for file_id in ids + ([] if root_id in ids else [root_id]):
                row = state.rows.add()
                row.target_transform_file_id = file_id
                row.display_name = labels[file_id]
            state.renderer_occurrence_id = renderer["occurrence_id"]
            state.root_context_id = renderer["root_context_id"]
            state.mesh_realization_id = renderer["native_realization_id"]
            state.source_revision_sha256 = record["source_revision_sha256"]
            state.root_bone_target_transform_file_id = root_id
        except (BindingError, TypeError, ValueError, KeyError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class VAPB_OT_confirm_skin_binding(bpy.types.Operator):
    bl_idname = "vapb.confirm_skin_binding"
    bl_label = "Bone対応を確定"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = context.scene.vapb_renderer_root
        mesh = context.scene.vapb_renderer_mesh
        state = context.scene.vapb_skin_mapping
        if root is None or mesh is None or not state.renderer_occurrence_id:
            self.report({"ERROR"}, "Bone対応を読み込み直してください")
            return {"CANCELLED"}
        if not state.rows or any(not row.confirmed or not row.target_name for row in state.rows):
            self.report({"ERROR"}, "各Boneの選択と確認が必要です")
            return {"CANCELLED"}
        try:
            renderer = _confirmed_renderer(mesh, root)
            record = renderer["occurrence"]
            if (state.renderer_occurrence_id != renderer["occurrence_id"]
                    or state.root_context_id != renderer["root_context_id"]
                    or state.mesh_realization_id != renderer["native_realization_id"]
                    or state.source_revision_sha256 != record["source_revision_sha256"]
                    or state.root_bone_target_transform_file_id != record["skin"]["root_bone_transform_file_id"]):
                raise BindingError("Bone対応の読込後に対象が変わりました")
            selections = {row.target_transform_file_id: row.target_name for row in state.rows}
            if len(selections) != len(state.rows):
                raise BindingError("Bone対応が重複しています")
            binding = make_skin_binding(mesh, root, bpy.data.objects, selections)
            mesh["_vapb_skin_binding"] = json.dumps(binding, sort_keys=True)
        except (BindingError, TypeError, ValueError, KeyError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "Bone対応を確定しました")
        return {"FINISHED"}


def _material_plan(record, mesh_obj):
    if record.get("material_status") != "EXACT":
        raise BindingError("Material mapping is unresolved")
    count = record.get("material_slot_count")
    values = record.get("materials")
    if not isinstance(count, int) or count < 0 or not isinstance(values, dict):
            raise BindingError("Material slot metadata is incomplete")
    if set(values) != {str(index) for index in range(count)} and set(values) != set(range(count)):
        raise BindingError("Material slots are incomplete")
    if getattr(mesh_obj, "data", None) is None or not hasattr(mesh_obj.data, "materials"):
        raise BindingError("Selected Object has no material slots")
    if count > len(mesh_obj.material_slots) and mesh_obj.data.users != 1:
        raise BindingError("共有メッシュです。Blenderでメッシュをシングルユーザー化してから再試行してください")
    plan = []
    for index in range(count):
        value = values[str(index)] if str(index) in values else values[index]
        if value is None:
            plan.append(None)
            continue
        if not isinstance(value, dict):
            raise BindingError("Malformed material reference")
        package = str(value.get("source_package_id", ""))
        guid = str(value.get("guid", "")).lower()
        file_id = str(value.get("file_id", ""))
        if not package or not guid or not file_id:
            raise BindingError("Material reference is incomplete")
        matches = [material for material in bpy.data.materials
                   if material.get("unity_source_package_id", "") == package
                   and str(material.get("unity_material_guid", "")).lower() == guid
                   and str(material.get("unity_material_file_id", "")) == file_id]
        if len(matches) != 1:
            raise BindingError(f"Material slot {index} has no unique scoped material")
        plan.append(matches[0])
    return plan


class VAPB_OT_confirm_renderer_binding(bpy.types.Operator):
    bl_idname = "vapb.confirm_renderer_binding"
    bl_label = "Rendererとメッシュを確定"
    bl_description = "選択したRendererをメッシュオブジェクトに紐付け、素材を適用します"
    bl_options = {"REGISTER", "UNDO"}

    occurrence_id: bpy.props.StringProperty(options={"HIDDEN"})

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=460)

    def draw(self, context):
        layout = self.layout
        root = context.scene.vapb_renderer_root
        mesh = context.scene.vapb_renderer_mesh
        record = next((r for r in projection_records(root) if r.get("occurrence_id") == self.occurrence_id), None)
        layout.label(text=f"対象: {record.get('owner_name', '') if record else '不明'}")
        layout.label(text=f"素材: {record.get('material_status', 'UNKNOWN') if record else 'MISSING'}")
        layout.prop(context.scene, "vapb_renderer_root", text="ルート")
        layout.prop(context.scene, "vapb_renderer_mesh", text="メッシュオブジェクト")
        if mesh:
            layout.label(text=f"選択中: {mesh.name}")
        layout.label(text="この対応と素材スロットへの適用を確定します")

    def execute(self, context):
        root = context.scene.vapb_renderer_root
        mesh = context.scene.vapb_renderer_mesh
        record = next((r for r in projection_records(root) if r.get("occurrence_id") == self.occurrence_id), None)
        if root is None or mesh is None or record is None:
            self.report({"ERROR"}, "ルート、Renderer、メッシュオブジェクトを選択してください")
            return {"CANCELLED"}
        if context.mode != "OBJECT":
            self.report({"ERROR"}, "オブジェクトモードで実行してください")
            return {"CANCELLED"}
        if not any(obj == root for obj in context.scene.objects) or not any(obj == mesh for obj in context.scene.objects):
            self.report({"ERROR"}, "ルートとメッシュは現在のシーンから選択してください")
            return {"CANCELLED"}
        if len(mesh.users_scene) != 1:
            self.report({"ERROR"}, "複数シーンで共有されたオブジェクトは対象外です")
            return {"CANCELLED"}
        if root.library is not None or mesh.library is not None or mesh.data is None or mesh.data.library is not None:
            self.report({"ERROR"}, "リンクされたオブジェクトやメッシュは編集できません")
            return {"CANCELLED"}
        try:
            link = validate_binding(record, root, mesh, bpy.data.objects)
            plan = _material_plan(record, mesh)
        except (BindingError, TypeError, ValueError) as exc:
            self.report({"ERROR"}, _display_error(exc))
            return {"CANCELLED"}
        original_count = len(mesh.data.materials)
        original_slots = [(slot.link, slot.material) for slot in mesh.material_slots]
        original_link = mesh.get("_vapb_renderer_binding")
        try:
            while len(mesh.data.materials) < len(plan):
                mesh.data.materials.append(None)
            for index in range(len(mesh.material_slots)):
                material = plan[index] if index < len(plan) else None
                slot = mesh.material_slots[index]
                slot.link = "OBJECT"
                slot.material = material
            mesh["_vapb_renderer_binding"] = json.dumps(link, sort_keys=True)
        except Exception as exc:
            for index, (link_type, material) in enumerate(original_slots):
                slot = mesh.material_slots[index]
                slot.link = link_type
                slot.material = material
            while len(mesh.data.materials) > original_count:
                mesh.data.materials.pop(index=len(mesh.data.materials) - 1)
            if original_link is None:
                if "_vapb_renderer_binding" in mesh:
                    del mesh["_vapb_renderer_binding"]
            else:
                mesh["_vapb_renderer_binding"] = original_link
            self.report({"ERROR"}, "適用に失敗したため、元の素材スロットを復元しました")
            return {"CANCELLED"}
        self.report({"INFO"}, "Rendererとメッシュの対応を確定しました")
        return {"FINISHED"}


CLASSES = (VAPB_PG_skin_mapping_row, VAPB_PG_skin_mapping_state,
           VAPB_OT_confirm_renderer_binding, VAPB_OT_load_skin_mappings,
           VAPB_OT_confirm_skin_binding)
