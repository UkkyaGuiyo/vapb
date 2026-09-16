"""UIH-001..003: fresh foreground process, REAL props dialogs and RET input.

Run with --factory-startup --enable-event-simulate --python this_file -- OUTPUT.
Optional local-only env: UNITYPACKAGE_UIH_PRIMARY / UNITYPACKAGE_UIH_PREFAB.
No invoke-to-execute substitution. Caller must verify result.json success.
"""
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import unitypackage_blender_importer as addon
from unitypackage_blender_importer.operators import import_unitypackage as m
from unitypackage_blender_importer.tests.blender_cross_package_dependency_test import package, material, make_fbx
from unitypackage_blender_importer.tests.blender_group_import_e2e_test import prefab


def main():
    args = sys.argv[sys.argv.index('--')+1:]
    out = Path(args[0]); out.mkdir(parents=True, exist_ok=True)
    reject_once = '--reject-once' in args
    started = time.perf_counter(); trace = []
    state = dict(stage='', drawn=False, prefab_invoke=0, siblings_invoke=0,
                 prefab_execute=0, siblings_execute=0, prepared_result=None,
                 pumps=0, rejected=0, error=None)

    def log(event, sid='', **values):
        session = m._PREPARED_SESSIONS.get(sid)
        trace.append(dict(t=time.perf_counter()-started, event=event, session_id=sid,
            session_exists=session is not None,
            age=time.perf_counter()-session.created_at if session else None,
            pending=session.pending_stage if session else '',
            active=session.active_stage if session else '', **values))
        (out/'trace.json').write_text(json.dumps(trace, indent=2), encoding='utf-8')

    original_register = bpy.app.timers.register

    def register(callback, **kwargs):
        state['pumps'] += 1
        log('TIMER_REGISTER', callback=callback.__qualname__, **kwargs)
        fired_count = 0
        def fired():
            nonlocal fired_count
            fired_count += 1
            for sid, session in m._PREPARED_SESSIONS.items():
                if fired_count <= 2 or session.pending_stage:
                    log('TIMER_FIRED', sid)
            return callback()
        return original_register(fired, **kwargs)
    bpy.app.timers.register = register
    original_schedule = m._schedule_prepared_session
    def schedule(sid, **kwargs):
        log('SCHEDULE', sid, **kwargs)
        return original_schedule(sid, **kwargs)
    m._schedule_prepared_session = schedule

    def install(cls, stage):
        invoke0, draw0, execute0 = cls.invoke, cls.draw, cls.execute
        def invoke(self, context, event):
            if reject_once and stage == 'siblings' and not state['rejected']:
                state['rejected'] += 1
                log('INVOKE_REJECTED', self.session_id)
                return {'CANCELLED'}
            if stage == 'prefab':
                self.prefab_choice = os.environ.get('UNITYPACKAGE_UIH_PREFAB', 'PREFAB_1')
            else:
                self.import_action = 'TOGETHER'
            state[stage+'_invoke'] += 1
            state.update(stage=stage, drawn=False)
            log('INVOKE', self.session_id, stage=stage)
            result = invoke0(self, context, event)
            log('INVOKE_RETURN', self.session_id, result=sorted(result))
            return result
        def draw(self, context):
            draw0(self, context)
            if not state['drawn']:
                log('DRAW', self.session_id, stage=stage)
            state['drawn'] = True
        def execute(self, context):
            state[stage+'_execute'] += 1
            log('EXECUTE', self.session_id, stage=stage)
            result = execute0(self, context)
            log('EXECUTE_RETURN', self.session_id, result=sorted(result))
            state.update(stage='', drawn=False)
            return result
        cls.invoke, cls.draw, cls.execute = invoke, draw, execute
    install(m.UNITYPACKAGE_OT_import_prefab, 'prefab')
    install(m.UNITYPACKAGE_OT_import_siblings, 'siblings')
    prepared0 = m.UNITYPACKAGE_OT_import_prepared.execute
    def prepared(self, context):
        session = m._PREPARED_SESSIONS[self.session_id]
        selected = session.operator._selected_prefab(session.operator._prefab_paths)
        state['selected_prefab'] = selected.stem if selected else ''
        log('IMPORT', self.session_id)
        result = prepared0(self, context)
        state['prepared_result'] = sorted(result)
        log('IMPORT_RETURN', self.session_id, result=sorted(result))
        return result
    m.UNITYPACKAGE_OT_import_prepared.execute = prepared

    temp = tempfile.TemporaryDirectory(prefix='foreground_handoff_')
    root = Path(temp.name)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    real = os.environ.get('UNITYPACKAGE_UIH_PRIMARY', '')
    if real:
        primary = Path(real)
    else:
        primary = root/'Geometry.unitypackage'
        package(primary, [('a'*32,'Assets/Body.fbx',make_fbx())]+[
            (str(i)*32, f'Assets/Prefab{label}.prefab', prefab('a'*32,'b'*32))
            for i,label in enumerate(('A','B','C'),1)])
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
        package(root/'Appearance.unitypackage', [('b'*32,'Assets/M.mat',material('c'*32)), ('c'*32,'Assets/I.png',png)])
    addon.register()
    def start():
        log('ROOT_IMPORT')
        result = bpy.ops.import_scene.unitypackage(filepath=str(primary), keep_extracted=False)
        log('ROOT_RETURN', result=sorted(result))
        return None
    original_register(start, first_interval=0.3)
    sent = set()
    def input_pump():
        stage = state['stage']
        if state['drawn'] and stage and stage not in sent:
            sent.add(stage); log('REAL_RET_INPUT', stage=stage)
            win = bpy.context.window_manager.windows[0]
            win.event_simulate(type='RET', value='PRESS', x=win.width//2, y=win.height//2)
            win.event_simulate(type='RET', value='RELEASE', x=win.width//2, y=win.height//2)
        if state['prepared_result'] is not None or time.perf_counter()-started > (240 if real else 30):
            success = (state['prepared_result'] == ['FINISHED'] and not m._PREPARED_SESSIONS
                and all(state[k] == 1 for k in ('prefab_invoke','siblings_invoke','prefab_execute','siblings_execute'))
                and state['pumps'] == 1)
            if not real:
                success = success and state.get('selected_prefab') == 'PrefabB'
            log('FINAL', success=success)
            (out/'result.json').write_text(json.dumps(dict(success=success, state=state,
                stale_sessions=len(m._PREPARED_SESSIONS)), indent=2), encoding='utf-8')
            for sid in list(m._PREPARED_SESSIONS):
                m._discard_prepared_session(sid, bpy.context)
            temp.cleanup()
            print('UIH_FOREGROUND_OK' if success else 'UIH_FOREGROUND_FAILED', flush=True)
            bpy.ops.wm.quit_blender()
            return None
        return 0.05
    original_register(input_pump, first_interval=0.5)


if __name__ == '__main__':
    main()
