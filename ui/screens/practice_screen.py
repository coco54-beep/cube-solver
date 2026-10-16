"""Formula-set practice for 2×2, 3×3, Square-1 and Pyraminx."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from app import prefs
from app.formula_i18n import msg, puzzle_label
from app.i18n import current_language
from demo.algorithm_library import MODES, groups, lesson, title, prerequisite
from demo.practice import DEFAULT_SETS, PRACTICE_PUZZLES, PracticeSession, format_time
from demo.learning import FILTERS
from ui.widgets.progress import load_learning_progress, save_learning_progress
from renderer.cube_view import CubeView
from ui.screens.demo_screen import _demo_view_for, _set_demo_cube
from ui.widgets import metrics as m
from ui.widgets.buttons import PrimaryButton, UIButton
from ui.widgets.dialogs import theme_popup
from ui.widgets.layouts import AdaptiveSceneLayout, ResponsiveBoxLayout
from ui.widgets.scroll_list import wrap_scroll


def autoheight(label):
    label.size_hint_y = None
    label.bind(width=lambda widget, width: setattr(widget, 'text_size', (width, None)))
    label.bind(texture_size=lambda widget, size: setattr(widget, 'height', size[1] + m.h(6)))
    return label


class PracticeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = PracticeSession(history=prefs.get('practice_history', []),
                                       progress=load_learning_progress())
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='practice-setup')
        self._setup_cancel = Event()
        self._setup_future = None
        self._setup_busy = False
        self.puzzle = '3x3'
        self._updating = False
        self._timer_event = None
        self._space_down = False
        self._start_on_release = False
        self._popup = None
        self._answer_shown = False
        self._root_layout = AdaptiveSceneLayout(gap_px=6, padding_px=[8, 6, 8, 8])
        top = ResponsiveBoxLayout(height_px=48, gap_px=6)
        back = UIButton(icon_name='back', size_hint_x=.18)
        back.bind(on_release=lambda *_: setattr(self.manager, 'current', 'FormulaLibraryScreen'))
        self.heading = Label(font_size='19sp')
        top.add_widget(back)
        top.add_widget(self.heading)
        self.help_button=UIButton(text='?',size_hint_x=.12)
        self.help_button.bind(on_release=self.show_help)
        top.add_widget(self.help_button)
        self._root_layout.add_widget(top)
        choose = ResponsiveBoxLayout(height_px=44, gap_px=6)
        self.puzzle_select = Spinner(size_hint_x=.35, font_size='15sp')
        self.puzzle_select.bind(text=self._puzzle_changed)
        self.set_button = UIButton(size_hint_x=.65, font_size='15sp')
        self.set_button.bind(width=lambda widget,width:setattr(widget,'text_size',(max(1,width-m.h(16)),None)))
        self.set_button.bind(on_release=self.choose_sets)
        choose.add_widget(self.puzzle_select)
        choose.add_widget(self.set_button)
        self._root_layout.add_widget(choose)
        filters = ResponsiveBoxLayout(height_px=42, gap_px=6)
        self.filter_select = Spinner(font_size='14sp')
        self.filter_select.bind(text=self._filter_changed)
        self.learning_button = UIButton(font_size='13sp')
        self.learning_button.bind(on_release=self.cycle_learning)
        filters.add_widget(self.filter_select)
        filters.add_widget(self.learning_button)
        self._root_layout.add_widget(filters)
        self.view = CubeView()
        panel = BoxLayout(orientation='vertical', spacing=m.h(7))
        self.selection = autoheight(Label(font_size='12sp', halign='center'))
        self.question_label = autoheight(Label(font_size='17sp', bold=True, halign='center'))
        self.scramble = autoheight(Label(font_size='16sp', halign='center'))
        self.timer = Label(text='0.00', font_size='44sp', size_hint_y=None, height=m.h(64))
        self.timer_button = PrimaryButton(size_hint_y=None, height=m.h(56), font_size='20sp')
        self.timer_button.bind(on_release=self.toggle_timer)
        self.status = autoheight(Label(font_size='13sp', halign='center'))
        self.answer = autoheight(Label(font_size='16sp', halign='center'))
        actions = ResponsiveBoxLayout(height_px=46, gap_px=6)
        self.answer_button = UIButton(font_size='14sp')
        self.answer_button.bind(on_release=self.reveal_answer)
        self.replay_button = UIButton(font_size='14sp')
        self.replay_button.bind(on_release=self.replay)
        self.next_button = PrimaryButton(font_size='14sp')
        self.next_button.bind(on_release=self.next_question)
        for button in (self.answer_button, self.replay_button, self.next_button):
            actions.add_widget(button)
        self.statistics = autoheight(Label(font_size='13sp', halign='center'))
        results = ResponsiveBoxLayout(height_px=42, gap_px=5)
        self.penalties = {}
        for value in ('OK', '+2', 'DNF'):
            button = UIButton(text=value, font_size='14sp')
            button.bind(on_release=lambda *_a, penalty=value: self.set_penalty(penalty))
            self.penalties[value] = button
            results.add_widget(button)
        self.history_button = UIButton(font_size='13sp')
        self.history_button.bind(on_release=self.show_history)
        results.add_widget(self.history_button)
        self.keys = autoheight(Label(font_size='12sp', halign='center'))
        for widget in (self.question_label, self.scramble, self.timer, self.timer_button, self.status,
                       self.answer, actions, results, self.statistics):
            panel.add_widget(widget)
        self._root_layout.set_content(self.view, panel)
        self.add_widget(self._root_layout)
        Window.bind(on_key_down=self._key_down, on_key_up=self._key_up)
        self.retranslate()

    def on_pre_enter(self, *_):
        progress = load_learning_progress()
        changed = progress.records != self.session.progress.records
        self.session.progress = progress
        if not self.session.question:
            self.select_puzzle(self.puzzle)
        else:
            if changed:
                try:
                    self.session.set_filter(self.session.filter)
                except ValueError:
                    self.session.set_filter('all')
            self._refresh()

    def select_puzzle(self, puzzle, preferred=None):
        self._cancel_setup()
        saved = prefs.get('practice_sets_' + puzzle, [DEFAULT_SETS[puzzle]])
        names = [preferred] if preferred else saved
        available = {group['id'] for group in groups(puzzle)}
        names = [name for name in names if name in available] or [DEFAULT_SETS[puzzle]]
        self.puzzle = puzzle
        self._stop_update()
        self.session.configure(puzzle, names)
        self._updating = True
        self.puzzle_select.text = puzzle_label(puzzle)
        self._updating = False
        self.next_question()

    def _puzzle_changed(self, _widget, text):
        if not self._updating:
            self.select_puzzle(next(p for p in PRACTICE_PUZZLES if puzzle_label(p) == text))

    def retranslate(self):
        self.heading.text = msg('practice')
        self.set_button.text = msg('sets')
        self.answer_button.text = msg('answer')
        self.replay_button.text = msg('replay')
        self.next_button.text = msg('next')
        self.keys.text = msg('keys')
        self.history_button.text = msg('history')
        self._updating = True
        self.puzzle_select.values = [puzzle_label(p) for p in PRACTICE_PUZZLES]
        self.puzzle_select.text = puzzle_label(self.puzzle)
        self.filter_select.values = [msg(f) for f in FILTERS]
        self.filter_select.text = msg(self.session.filter)
        self._updating = False
        if self.session.question:
            self._refresh()

    def _theme(self):
        from kivy.app import App
        return App.get_running_app().theme

    def refresh_theme(self):
        for label in (self.heading, self.selection, self.question_label, self.scramble, self.timer,
                      self.status, self.answer, self.statistics, self.keys):
            label.color = self._theme().text

    def choose_sets(self, *_):
        selected = set(self.session.selected)
        content = BoxLayout(orientation='vertical', spacing=m.h(8))
        listing = BoxLayout(orientation='vertical', spacing=m.h(6))
        content.add_widget(wrap_scroll(listing, do_scroll_x=False))
        confirm = PrimaryButton(text=msg('confirm'), size_hint_y=None, height=m.h(46))
        for group in groups(self.puzzle):
            button = UIButton(text=title(group, current_language()) + f" ({len(group['cases'])})",
                              active=group['id'] in selected, size_hint_y=None, height=m.h(46), font_size='14sp')
            def toggle(widget, group_id=group['id']):
                if group_id in selected:
                    selected.remove(group_id)
                else:
                    selected.add(group_id)
                widget.active = group_id in selected
                confirm.disabled = not selected
            button.bind(on_release=toggle)
            listing.add_widget(button)
        popup = Popup(title=msg('sets'), content=content, size_hint=(.94, .88))
        def apply(*_):
            self._stop_update()
            self.session.configure(self.puzzle, sorted(selected))
            prefs.set('practice_sets_' + self.puzzle, list(self.session.selected))
            popup.dismiss()
            self.next_question()
        confirm.bind(on_release=apply)
        content.add_widget(confirm)
        self._open_popup(popup)

    def _open_popup(self, popup):
        self._space_down = False
        self._start_on_release = False
        self._popup = popup
        popup.bind(on_dismiss=lambda *_: setattr(self, '_popup', None))
        theme_popup(popup, self._theme())
        popup.open()

    def show_help(self,*_):
        if self.session.state=='running':
            return
        content=BoxLayout(orientation='vertical',spacing=m.h(8))
        text=BoxLayout(orientation='vertical',spacing=m.h(12))
        scroll=wrap_scroll(text, do_scroll_x=False)
        lines=[self.selection.text,msg('keys'),msg('penalty_help'),msg('progress_help')]
        if self.session.question:
            lines.append(prerequisite(self.session.question['group'],current_language()))
        for line in lines:
            text.add_widget(autoheight(Label(text=line,font_size='14sp')))
        scroll.add_widget(text)
        content.add_widget(scroll)
        close=UIButton(text=msg('confirm'),size_hint_y=None,height=m.h(44))
        popup=Popup(title=msg('practice_help'),content=content,size_hint=(.9,.65))
        close.bind(on_release=popup.dismiss)
        content.add_widget(close)
        self._open_popup(popup)

    def next_question(self, *_):
        if self.session.state == 'running':
            return
        self._cancel_setup()
        self._stop_update()
        self.session.next_question()
        self._answer_shown = False
        case = self.session.question['case']
        cube = case['initial'].clone()
        self.view = _demo_view_for(cube)
        self._root_layout.replace_scene(self.view)
        _set_demo_cube(self.view, cube)
        self.view.reset_camera()
        if 'camera' in case:
            self.view.yaw, self.view.pitch, self.view.roll = case['camera']
            self.view.refresh()
        self._refresh()
        self._generate_setup()

    def _cancel_setup(self):
        self._setup_cancel.set()
        if self._setup_future:
            self._setup_future.cancel()
        self._setup_busy = False

    def _generate_setup(self):
        if self.puzzle == 'Pyraminx':
            return
        from demo.practice_scramble import generate_scramble
        question, puzzle = self.session.question, self.puzzle
        cancellation = Event()
        self._setup_cancel = cancellation
        self._setup_busy = True
        self._refresh()
        future = self._executor.submit(generate_scramble, puzzle, question['case'], cancellation.is_set)
        self._setup_future = future
        def complete(done):
            try:
                text = done.result()
            except Exception:
                text = None
            def apply(_dt):
                if cancellation.is_set() or self.session.question is not question:
                    return
                self._setup_busy = False
                if text:
                    question['case']['scramble_text'] = text
                self._refresh()
            Clock.schedule_once(apply, 0)
        future.add_done_callback(complete)

    def _filter_changed(self, _widget, text):
        if self._updating or self.session.puzzle is None:
            return
        mode = next((f for f in FILTERS if msg(f) == text), None)
        if mode is None:
            return
        try:
            self.session.set_filter(mode)
        except ValueError:
            self._updating = True
            self.filter_select.text = msg(self.session.filter)
            self._updating = False
            self._open_popup(Popup(title=msg('practice'), content=Label(text=msg('empty')), size_hint=(.88, .35)))
            return
        self.next_question()

    def cycle_learning(self, *_):
        if not self.session.question or not self._answer_shown or self.session.state == 'running':
            return
        self.session.progress.cycle(self.puzzle, self.session.question['item'])
        save_learning_progress(self.session.progress)
        try:
            self.session.set_filter(self.session.filter)
        except ValueError:
            self.session.set_filter('all')
        self._refresh()

    def set_penalty(self, penalty):
        if self.session.penalty(penalty):
            prefs.set('practice_history', self.session.history)
            self._refresh()

    def show_history(self, *_):
        if self.session.state == 'running':
            return
        content = BoxLayout(orientation='vertical', spacing=m.h(6))
        listing = BoxLayout(orientation='vertical', spacing=m.h(4))
        content.add_widget(wrap_scroll(listing, do_scroll_x=False))
        for record in reversed(self.session.records()[-50:]):
            value = self.session._time_value(record)
            text = record.get('case', '') + ' · ' + ('DNF' if value is None else format_time(value))
            if record.get('penalty') == '+2':
                text += ' (+2)'
            listing.add_widget(autoheight(Label(text=text, font_size='14sp')))
        if not self.session.records():
            listing.add_widget(Label(text=msg('empty'), size_hint_y=None, height=m.h(50)))
        close = UIButton(text=msg('confirm'), size_hint_y=None, height=m.h(44))
        popup = Popup(title=msg('history'), content=content, size_hint=(.92, .8))
        close.bind(on_release=lambda *_: popup.dismiss())
        content.add_widget(close)
        self._open_popup(popup)

    def toggle_timer(self, *_):
        if self._popup or self._setup_busy:
            return
        if self.session.state == 'running':
            if self.session.stop():
                prefs.set('practice_history', self.session.history)
            self._stop_update()
        elif self.session.start():
            self._timer_event = Clock.schedule_interval(self._tick, 1 / 30)
        self._refresh()

    def _tick(self, _dt):
        self.timer.text = format_time(self.session.time())

    def _stop_update(self):
        if self._timer_event:
            self._timer_event.cancel()
        self._timer_event = None

    def reveal_answer(self, *_):
        self.session.reveal()
        self._stop_update()
        self._answer_shown = True
        self._refresh()

    def replay(self, *_):
        self.reveal_answer()
        question = self.session.question
        steps = lesson(question['group'], question['item'], question['case']['alternative'])
        steps[0]['cases'] = [question['case']]
        self.manager.get_screen('DemoScreen').enter_case(MODES[self.puzzle], 0, 0, steps, return_screen=self.name)
        self.manager.current = 'DemoScreen'

    def _refresh(self):
        state = self.session.state
        running = state == 'running'
        self.timer.text = format_time(self.session.time())
        self.timer_button.text = msg('stop' if running else 'start')
        self.timer_button.disabled = self._setup_busy or state not in ('ready', 'running')
        self.next_button.disabled = running
        self.set_button.disabled = running
        self.puzzle_select.disabled = running
        self.replay_button.disabled = running
        self.filter_select.disabled = running
        self.history_button.disabled = running
        self.help_button.disabled = running
        self.learning_button.disabled = running or not self._answer_shown
        self.learning_button.text = msg(self.session.progress.status(self.puzzle, self.session.question['item'])) if self._answer_shown else msg('learning_status')
        self._updating = True
        self.filter_select.text = msg(self.session.filter)
        self._updating = False
        for penalty, button in self.penalties.items():
            button.disabled = running or self.session.last_record is None
            button.active = bool(self.session.last_record and self.session.last_record.get('penalty', 'OK') == penalty)
        self.question_label.text = msg('number', number=self.session.number)
        self.scramble.text = msg('generating') if self._setup_busy else self.session.setup_text()
        self.status.text = msg('practice_'+state)
        self.answer.text = (self.session.question['item']['name'] + '\n' + self.session.question['case']['text']) if self._answer_shown else ''
        self.selection.text = msg('selected', sets=' / '.join(self.session.selected), count=len(self.session.pool))
        self.set_button.text=' / '.join(self.session.selected)
        self.set_button.shorten=True
        self.set_button.shorten_from='right'
        stats = self.session.stats()
        self.statistics.text = msg('practice_stats',count=stats['count'],best=format_time(stats['best']),
                                   ao5=format_time(self.session.average(5)),ao12=format_time(self.session.average(12)))

    def _key_down(self, _window, key, *_):
        if key != 32 or not self.manager or self.manager.current != self.name or self._popup:
            return False
        if self._space_down:
            return True
        self._space_down = True
        self._start_on_release = self.session.state == 'ready'
        if self.session.state == 'running':
            self.toggle_timer()
        return True

    def _key_up(self, _window, key, *_):
        if key != 32 or not self.manager or self.manager.current != self.name:
            return False
        start = self._space_down and self._start_on_release and not self._popup
        self._space_down = False
        self._start_on_release = False
        if start:
            self.toggle_timer()
        return True

    def on_pre_leave(self, *_):
        self._cancel_setup()
        self._stop_update()
        self._space_down = False
        self._start_on_release = False
        if self.session.state == 'running':
            self.session.abort()
        if self._popup:
            self._popup.dismiss()
