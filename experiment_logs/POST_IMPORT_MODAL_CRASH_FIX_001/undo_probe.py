import bpy

class ProbeOperator(bpy.types.Operator):
    bl_idname = "wm.probe_undo"
    bl_label = "Probe Undo"

    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        self.timer = context.window_manager.event_timer_add(0.1, window=context.window)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}
        area = next(a for a in context.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in area.regions if r.type == "WINDOW")
        with context.temp_override(window=context.window, area=area, region=region):
            bpy.ops.mesh.primitive_cube_add()
            bpy.ops.object.delete()
            print("MODAL_UNDO_POLL", bpy.ops.ed.undo.poll(), flush=True)
            try:
                print("MODAL_UNDO_RESULT", bpy.ops.ed.undo(), flush=True)
            except Exception as exc:
                print("MODAL_UNDO_EXCEPTION", repr(exc), flush=True)
        context.window_manager.event_timer_remove(self.timer)
        bpy.utils.unregister_class(ProbeOperator)
        bpy.ops.wm.quit_blender()
        return {"FINISHED"}

bpy.utils.register_class(ProbeOperator)

def probe():
    bpy.ops.wm.probe_undo()
    return None

bpy.app.timers.register(probe, first_interval=0.5)
