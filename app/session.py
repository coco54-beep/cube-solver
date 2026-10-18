"""Bounded JSON checkpoints for puzzle state; never deserialize executable code."""
import hashlib
import importlib
import json
import logging
import os
import tempfile
import threading
from pathlib import Path

_LOG = logging.getLogger(__name__)
_CUBES = {
    'cube.cube2:Cube2', 'cube.cube3:Cube3', 'cube.cube4:Cube4', 'cube.cube5:Cube5',
    'cube.cube_n:CubeN', 'cube.mastermorphix:MastermorphixCube', 'cube.mirror:MirrorCube',
    'cube.shape_cube:AxisCube', 'cube.shape_cube:PandoraCube', 'cube.shape_cube:WindmillCube',
    'cube.shape_cube:FisherCube', 'cube.shape_cube:FootballCube',
    'cube.polyhedral:PolyhedralPuzzle', 'cube.mirror_tower:MirrorTowerCube', 'cube.square1:Square1Cube',
    'cube.mirror_pyraminx:MirrorPyraminxCube',
    'cube.mirror_skewb:MirrorSkewbCube',
    'cube.ghost:GhostCube',
    'cube.square_family:SquareFamilyCube',
    'cube.mirror_shape:MirrorAxisCube', 'cube.mirror_shape:MirrorFisherCube',
    'cube.mirror_shape:MirrorWindmillCube',
    'cube.mirror_shape:MirrorOffsetWindmillCube', 'cube.mirror_shape:MirrorOffsetFisherCube',
    'cube.mirror_shape:MirrorUnequalWindmillCube', 'cube.mirror_shape:MirrorUnequalFisherCube',
}
_RECORDS = {
    'cube.cubie_model:Cubie', 'cube.mastermorphix:MorphixPiece', 'cube.mirror_tower:Piece',
    'cube.polyhedral:Move', 'cube.square1:Square1Move', 'cube.square1_entry:EntryBlock',
    'cube.square_family:SquareFamilyMove', 'cube.square_family_entry:SquareFamilyBlock',
    'solver.result:SolveResult', 'solver.result:SolveStage',
}
_PLAIN = {
    'cube.square1_entry:Square1Entry': ('slots', 'middle', 'blocks'),
    'cube.square_family_entry:SquareFamilyEntry': ('puzzle_kind', 'slots', 'middle', 'blocks'),
    'renderer.cube_orientation:CubeOrientation': ('n', 'index', 'world'),
    'renderer.polyhedral_orientation:PolyhedralOrientation': ('normals', 'sequence', 'index', 'world'),
    'vision.scan_profiles:SurfaceOrientation': ('index', 'world', '_navigation'),
}


def encode(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list): return [encode(v) for v in value]
    if isinstance(value, dict): return {'@': 'dict', 'v': [[encode(k), encode(v)] for k, v in value.items()]}
    if isinstance(value, (tuple, set)):
        return {'@': 'set' if isinstance(value, set) else 'tuple', 'v': [encode(v) for v in value]}
    name = type(value).__module__+':'+type(value).__name__
    if name == 'renderer.mat4:Mat4': return {'@': name, 'v': list(value.m)}
    if name == 'numpy:ndarray': return {'@': 'array', 'v': value.tolist()}
    if name.startswith('numpy:') and hasattr(value,'item'): return encode(value.item())
    if name in _CUBES:
        fields = ('n', 'puzzle_kind', 'cubies', 'palette', 'colors', 'pieces', 'slots', 'middle')
        if name == 'cube.ghost:GhostCube':
            fields = ('n', 'puzzle_kind', 'cubies', 'palette', 'phases')
        if name == 'cube.square_family:SquareFamilyCube':
            fields = ('n', 'puzzle_kind', 'slots', 'middle')
        if name in ('cube.mirror_tower:MirrorTowerCube', 'cube.mirror_pyraminx:MirrorPyraminxCube',
                    'cube.mirror_skewb:MirrorSkewbCube'):
            # Partial shape input may repeat provisional identities. Save the
            # actual pieces, without asking for a valid labelled permutation.
            fields = ('n', 'puzzle_kind', 'pieces')
    elif name in _RECORDS:
        fields = tuple(value.__dataclass_fields__)
    elif name in _PLAIN:
        fields = _PLAIN[name]
    else:
        raise ValueError('Unsupported checkpoint type: '+name)
    return {'@': name, 'v': {key: encode(getattr(value, key)) for key in fields if hasattr(value, key)}}


def decode(value):
    if isinstance(value, list): return [decode(v) for v in value]
    if not isinstance(value, dict): return value
    name, data = value['@'], value['v']
    if name == 'dict': return {decode(k): decode(v) for k, v in data}
    if name == 'tuple': return tuple(decode(v) for v in data)
    if name == 'set': return set(decode(v) for v in data)
    if name == 'array':
        import numpy as np
        return np.asarray(data, dtype=np.uint8)
    if name == 'renderer.mat4:Mat4':
        from renderer.mat4 import Mat4
        if len(data) != 16: raise ValueError('Bad checkpoint matrix')
        return Mat4(data)
    if name not in _CUBES | _RECORDS | set(_PLAIN): raise ValueError('Unknown checkpoint type')
    module, symbol = name.split(':')
    cls = getattr(importlib.import_module(module), symbol)
    data = {k: decode(v) for k, v in data.items()}
    if name in _CUBES:
        if name == 'cube.polyhedral:PolyhedralPuzzle': return cls(data['puzzle_kind'], data['n'], data['colors'])
        if name == 'cube.mirror_tower:MirrorTowerCube': return cls(data['pieces'])
        if name == 'cube.mirror_pyraminx:MirrorPyraminxCube': return cls(data['pieces'], n=data['n'])
        if name == 'cube.mirror_skewb:MirrorSkewbCube': return cls(data['pieces'], n=data['n'])
        if name == 'cube.ghost:GhostCube': return cls(data['cubies'], n=data['n'], phases=data['phases'])
        if name == 'cube.square1:Square1Cube': return cls(data['slots'], data['middle'])
        if name == 'cube.square_family:SquareFamilyCube': return cls(data['puzzle_kind'],data['slots'],data['middle'])
        if not 2 <= data['n'] <= 17: raise ValueError('Bad checkpoint order')
        if 'palette' in data: return cls(data['cubies'], palette=data['palette'], n=data['n'])
        if name == 'cube.cube_n:CubeN': return cls(data['cubies'], data['n'])
        return cls(data['cubies'])
    if name in _RECORDS: return cls(**data)
    if set(data) != set(_PLAIN[name]): raise ValueError('Bad checkpoint fields')
    obj = cls.__new__(cls)
    obj.__dict__.update(data)
    return obj


APP_FIELDS = ('n', 'puzzle_kind', 'cube', 'mastermorphix_palette', 'facelets_input', 'facelets_cache',
              'solve_result', 'polyhedral_solution', 'input_from_camera', 'camera_return_screen', 'camera_recorded',
              'morphix_twist_source')
ENTRY_FIELDS = ('_cube', '_data', '_entry', '_recorded', '_position', '_pos', '_group', '_face', '_color',
                '_axis', '_layer', '_ori', '_poly_orientation', '_view_orientation', '_slot', '_field')
PLAY_FIELDS = ('_initial', '_moves', '_work', '_cube', '_index', '_idx', '_playback', '_source', '_recorded', '_face', '_axis', '_layer')
ENTRY_NAMES = ('InputScreen', 'MastermorphixScreen', 'MirrorScreen', 'PolyhedralScreen', 'MirrorTowerScreen',
               'ShapeCubeScreen', 'Square1Screen', 'SquareFamilyScreen', 'MirrorPyraminxScreen',
               'MirrorAxisScreen', 'MirrorFisherScreen', 'MirrorWindmillScreen',
               'MirrorOffsetWindmillScreen', 'MirrorOffsetFisherScreen',
               'MirrorUnequalWindmillScreen', 'MirrorUnequalFisherScreen', 'MirrorSkewbScreen', 'GhostScreen')


class SessionStore:
    def __init__(self, app):
        self.app = app
        self.path = Path(app.user_data_dir)/'last-session.json'
        self.lock = threading.RLock()
        self.last = None
        self.written = None
        self.restoring = False

    def capture(self):
        app, sm = self.app, self.app.root
        active = sm.current_screen
        if active is None: return None
        view = getattr(active, 'view', None)
        moving = bool(getattr(active,'_busy',False) or getattr(active,'_pending_move',None) is not None or
                      (view is not None and (getattr(view,'_move',None) is not None or getattr(view,'_anim',None) is not None)))
        replay_to = None
        fields = {key: getattr(app, key) for key in APP_FIELDS if hasattr(app, key)}
        screens = {}
        for name in ENTRY_NAMES:
            screen = sm.get_screen(name)
            cube = getattr(screen, '_cube', None)
            if name != 'InputScreen' and (cube is None or getattr(cube, 'puzzle_kind', 'cube') != app.puzzle_kind):
                continue
            if name == 'InputScreen' and app.puzzle_kind != 'cube': continue
            screens[name] = {key: getattr(screen, key) for key in ENTRY_FIELDS if hasattr(screen, key)}
        page = sm.current
        if page == 'SolvingScreen': page = getattr(active, '_source', 'InputScreen')
        if sm.current == 'InputScreen': fields['facelets_input'] = active.collect_facelets()
        if sm.current == 'TwistScreen' and active._work is not None:
            from cube.conversion import cubies_to_facelets
            fields['facelets_input'] = cubies_to_facelets(active._work.cubies, app.n)
        if sm.current in ('PlaybackScreen', 'PolyhedralPlaybackScreen', 'Square1Screen', 'SquareFamilyScreen', 'MorphixTwistScreen', 'GhostTwistScreen', 'PolyhedralTwistScreen', 'TwistScreen'):
            screens[sm.current] = dict(screens.get(sm.current, {}), **{k: getattr(active, k) for k in PLAY_FIELDS if hasattr(active, k)})
        if moving and sm.current == 'PlaybackScreen':
            replay_to = max(-1, active._idx-1)
            screens[sm.current]['_idx'] = replay_to
            screens[sm.current]['_work'] = app.cube.clone()
        elif moving and (sm.current == 'PolyhedralPlaybackScreen' or
                         (sm.current in ('Square1Screen','SquareFamilyScreen') and active._playback)):
            replay_to = active._index
            screens[sm.current]['_work'] = active._initial.clone()
        if sm.current == 'CameraScreen':
            active._park_photo()
            screens[sm.current] = {'_data': active._data, '_ori': active._ori, '_manual_cells': active._manual_cells,
                                   '_color_samples': getattr(active, '_color_samples', {}),
                                   '_parked_quad': active._parked_quad, '_parked_face': active._parked_face, '_parked_digest': active._parked_digest}
        from app.constants import COLOR_INFO
        return encode({'version': 1, 'app': fields, 'screens': screens, 'page': page, 'replay_to': replay_to,
                       'color_info': {key: COLOR_INFO[key] for key in getattr(app.cube, 'palette', ()) if key in COLOR_INFO}})

    def save(self, synchronous=False):
        if self.restoring or self.app.root is None: return
        try:
            state = self.capture()
            if state is None: return
            text = json.dumps(state, ensure_ascii=False, separators=(',', ':'))
            digest = hashlib.sha256(text.encode('utf-8')).digest()
            with self.lock:
                if self.written == digest: return
                if self.last == digest and not synchronous: return
                self.last = digest
            def write():
                with self.lock:
                    if self.last != digest: return
                    temporary = None
                    try:
                        self.path.parent.mkdir(parents=True, exist_ok=True)
                        fd, temporary = tempfile.mkstemp(prefix='.session-', dir=self.path.parent)
                        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                            stream.write(text); stream.flush(); os.fsync(stream.fileno())
                        os.replace(temporary, self.path)
                        self.written = digest
                    except Exception:
                        self.last = None
                        _LOG.exception('Could not save session')
                    finally:
                        if temporary and os.path.exists(temporary): os.unlink(temporary)
            if synchronous: write()
            else: threading.Thread(target=write, daemon=True, name='session-save').start()
        except Exception:
            _LOG.exception('Could not capture session')

    def restore(self):
        if not self.path.is_file(): return
        try:
            if self.path.stat().st_size > 16*1024*1024: raise ValueError('Checkpoint too large')
            state = decode(json.loads(self.path.read_text(encoding='utf-8')))
            if state['version'] != 1: return
            app, sm = self.app, self.app.root
            page = state['page']
            if not sm.has_screen(page): page = 'HomeScreen'
            self.restoring = True
            for key, value in state['app'].items():
                if key in APP_FIELDS: setattr(app, key, value)
            from app.constants import COLOR_INFO
            COLOR_INFO.update(state.get('color_info', {}))
            saved = state['screens']
            if any(not sm.has_screen(name) for name in saved): raise ValueError('Unknown saved screen')
            for name, fields in saved.items():
                if name == 'CameraScreen' or (name == page and name in ENTRY_NAMES): continue
                screen = sm.get_screen(name)
                for key, value in fields.items():
                    if key in ENTRY_FIELDS+PLAY_FIELDS: setattr(screen, key, value)
            # Entry screens use object identity to decide whether to create a blank puzzle.
            source = saved.get(page, {}).get('_source', page)
            if page == 'PolyhedralTwistScreen':
                source = {'mirror_tower':'MirrorTowerScreen',
                          'mirror_skewb':'MirrorSkewbScreen',
                          'mirror_pyraminx':'MirrorPyraminxScreen'}.get(app.puzzle_kind,'PolyhedralScreen')
            if source in ENTRY_NAMES and saved.get(source,{}).get('_cube') is not None:
                app.cube = saved[source]['_cube']
            if page == 'CameraScreen':
                # Its on_enter can arrive after the checkpoint callback on a
                # slow first frame. Establish the new puzzle identity now so
                # that late entry never resets restored photographs/colours.
                camera = sm.get_screen(page)
                camera._reset_for_n(app.n)
                camera._n_for_screen = app.n
                camera._cube_for_screen = app.cube
                camera._initialized = True
            sm.current = page
            from kivy.clock import Clock
            def finish(_dt):
                if sm.current != page:
                    self.restoring = False
                    return
                try:
                    screen = sm.get_screen(page)
                    allowed = ENTRY_FIELDS+PLAY_FIELDS+('_manual_cells','_color_samples','_parked_quad','_parked_face','_parked_digest')
                    for key, value in saved.get(page, {}).items():
                        if key in allowed: setattr(screen, key, value)
                    replay_to = state.get('replay_to')
                    if replay_to is not None:
                        screen._work.apply_moves(screen._moves[:replay_to+1 if page=='PlaybackScreen' else replay_to])
                    if page == 'CameraScreen':
                        if screen._profile: screen._ori.profile = screen._profile
                        screen._restore_parked_photo()
                        screen._update_face_ui()
                    elif page == 'PlaybackScreen':
                        screen._playing = screen._busy = False
                        screen.view.set_cube(screen._work)
                        screen._update_buttons()
                    elif page == 'PolyhedralPlaybackScreen':
                        screen._playing = False
                        screen.view.set_cube(screen._work)
                        screen._checkpoints = {screen._index: tuple(screen._work.colors)}
                        screen._refresh()
                    elif page in ('Square1Screen','SquareFamilyScreen'): screen._build(); screen._refresh()
                    elif page == 'InputScreen': screen._refresh_view(); screen._update_progress()
                    elif page == 'PolyhedralTwistScreen':
                        entry = sm.get_screen(source)
                        entry._cube = app.cube = screen._cube
                        screen.view.set_cube(screen._cube)
                        screen._update_controls()
                        screen.view.refresh()
                    elif page in ('TwistScreen', 'MorphixTwistScreen', 'GhostTwistScreen'):
                        screen.view.set_cube(screen._work)
                        if page in ('MorphixTwistScreen','GhostTwistScreen'): screen.view.recorded = screen._recorded
                    elif hasattr(screen, '_refresh'): screen._refresh()
                except Exception:
                    _LOG.exception('Could not restore screen')
                    sm.current = 'HomeScreen'
                finally:
                    self.restoring = False
            Clock.schedule_once(finish, sm.transition.duration+.05)
        except Exception:
            self.restoring = False
            _LOG.exception('Could not restore session')
