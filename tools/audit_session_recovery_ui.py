"""Exercise cold startup recovery in the real app with isolated user data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'reports/optimization/2026-11-02/session-recovery'
CASES = ('broken-json', 'interrupted', 'finish-error', 'late-enter', 'valid')


def run_case(case):
    os.environ.update(KIVY_NO_ARGS='1', KIVY_NO_FILELOG='1', KIVY_METRICS_DENSITY='1', KIVY_DPI='96')
    from app.desktop_runtime import configure_graphics
    configure_graphics()
    from kivy.config import Config
    Config.set('graphics', 'window_state', 'hidden')
    Config.set('graphics', 'width', '390')
    Config.set('graphics', 'height', '844')
    Config.remove_option('input', 'wm_pen')
    Config.remove_option('input', 'wm_touch')
    import app.prefs
    from app.application import CubeApp
    from app.session import SessionStore, encode
    from cube.cube3 import Cube3
    from kivy.clock import Clock
    from kivy.core.window import Window

    with tempfile.TemporaryDirectory(prefix='cube-recovery-') as directory:
        app.prefs._PREFS_FILE = str(Path(directory) / 'preferences.json')
        path = Path(directory) / 'last-session.json'
        state = dict(version=1, page='InputScreen', app=dict(n=3, puzzle_kind='cube', cube=Cube3.solved()),
                     screens={'InputScreen': {'_ori': 17} if case == 'finish-error' else {'_face': 'F'}}, color_info={})
        raw = b'{broken json' if case == 'broken-json' else json.dumps(encode(state)).encode()
        path.write_bytes(raw)
        if case == 'interrupted':
            path.with_name('last-session.restore-pending.json').write_text(
                json.dumps({'digest': hashlib.sha256(raw).hexdigest()}), encoding='utf-8')

        class Audit(CubeApp):
            passed = False
            def on_start(self):
                Window.size = (390, 844)
                if case == 'late-enter':
                    entry = self.root.get_screen('InputScreen')
                    def broken_enter(screen):
                        screen.unbind(on_enter=broken_enter)
                        raise IndexError('Injected late on_enter cache failure')
                    entry.bind(on_enter=broken_enter)
                self._session_store = SessionStore(self)
                self._session_store.restore()
                self.deadline = monotonic() + 20
                Clock.schedule_once(self.check, .3)

            def check(self, _dt):
                try:
                    store = self._session_store
                    if store.restoring and monotonic() < self.deadline:
                        Clock.schedule_once(self.check, .3)
                        return
                    if self.root.transition.is_active and monotonic() < self.deadline:
                        Clock.schedule_once(self.check, .1)
                        return
                    assert not store.restoring
                    assert store.recovery._handler is None
                    assert not store.recovery.marker.exists()
                    if case == 'valid':
                        assert self.root.current == 'InputScreen' and self.n == 3
                        assert path.read_bytes() == raw and store.recovery.backup is None
                    else:
                        assert self.root.current == 'HomeScreen' and self.n == 4
                        assert store.recovery.backup.read_bytes() == raw
                    Clock.schedule_once(self.open_input, .7)
                except Exception:
                    self.fail()

            def open_input(self, _dt):
                try:
                    self.layout = dict(window=list(Window.size), root=list(self.root.size),
                                       home=list(self.root.get_screen('HomeScreen').size))
                    if case != 'valid':
                        self.root.get_screen('HomeScreen').export_to_png(str(OUT / f'{case}.png'))
                        from kivy.uix.popup import Popup
                        for widget in Window.children:
                            if isinstance(widget, Popup):
                                widget.export_to_png(str(OUT / f'{case}-notice.png'))
                    # Recovery must leave normal page selection and input usable.
                    self.new_cube(3)
                    self.root.current = 'InputScreen'
                    Clock.schedule_once(self.check_input, .8)
                except Exception:
                    self.fail()

            def check_input(self, _dt):
                try:
                    screen = self.root.get_screen('InputScreen')
                    data = {face: [['R'] * 3 for _ in range(3)] for face in ('U', 'R', 'F', 'D', 'L', 'B')}
                    assert screen.set_facelets(data)
                    assert screen.collect_facelets() == data
                    self._session_store.save(synchronous=True)
                    # The backup is still byte-for-byte untouched after new input saves.
                    if case != 'valid': assert self._session_store.recovery.backup.read_bytes() == raw
                    self.passed = True
                    self.result = dict(case=case, passed=True, subsequent_input=True, layout=self.layout)
                    self.stop()
                except Exception:
                    self.fail()

            def fail(self):
                self.result = dict(case=case, passed=False, error=traceback.format_exc())
                self.stop()

        app = Audit()
        app._user_data_dir = directory
        try:
            app.run()
        finally:
            result = getattr(app, 'result', dict(case=case, passed=False, error='Application stopped early'))
            (OUT / f'{case}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        if not app.passed: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.case:
        run_case(args.case)
    else:
        rows = []
        for case in CASES:
            result = subprocess.run([sys.executable, __file__, '--case', case], cwd=ROOT,
                                    capture_output=True, timeout=45)
            (OUT / f'{case}.log').write_bytes(result.stdout + result.stderr)
            report = OUT / f'{case}.json'
            row = json.loads(report.read_text(encoding='utf-8')) if report.exists() else dict(case=case, passed=False)
            row['exit_code'] = result.returncode
            rows.append(row)
        (OUT / 'native-results.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        print(json.dumps(rows, indent=2))
        if any(not row['passed'] or row['exit_code'] for row in rows): raise SystemExit(1)
