"""Searchable, paginated offline formula catalog with native 3-D playback."""
import math

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from app.formula_i18n import msg, puzzle_label
from app.i18n import current_language
from ui.widgets.progress import load_learning_progress, save_learning_progress
from demo.algorithm_library import MODES, PUZZLES, groups, lesson, prerequisite, search_cases, title
from ui.widgets import metrics as m
from ui.widgets.buttons import PrimaryButton, UIButton
from ui.widgets.dialogs import theme_popup
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.scroll_list import wrap_scroll


def wrap(label):
    label.bind(size=lambda widget, size: setattr(widget, 'text_size', size))
    return label


class FormulaLibraryScreen(Screen):
    PAGE_SIZE = 8

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.puzzle = '3x3'
        self.group = None
        self.page = 0
        self._revision = 0
        self._updating = False
        self._search_event = None
        self._loaded = False
        root = ResponsiveBoxLayout(orientation='vertical', gap_px=6, padding_px=[8, 6, 8, 8])
        top = ResponsiveBoxLayout(height_px=48, gap_px=6)
        back = UIButton(icon_name='back', size_hint_x=.17)
        back.bind(on_release=lambda *_: setattr(self.manager, 'current', 'HomeScreen'))
        self.heading = Label(font_size='19sp', size_hint_x=.53)
        self.practice = PrimaryButton(size_hint_x=.3, font_size='14sp')
        self.practice.bind(on_release=self.open_practice)
        for widget in (back, self.heading, self.practice):
            top.add_widget(widget)
        root.add_widget(top)
        selectors = ResponsiveBoxLayout(height_px=44, gap_px=6)
        self.puzzle_select = Spinner(size_hint_x=.3, font_size='14sp')
        self.set_select = Spinner(size_hint_x=.7, font_size='14sp')
        self.puzzle_select.bind(text=self._puzzle_changed)
        self.set_select.bind(text=self._set_changed)
        selectors.add_widget(self.puzzle_select)
        selectors.add_widget(self.set_select)
        root.add_widget(selectors)
        self.search = TextInput(multiline=False, size_hint_y=None, height=m.h(40), font_size='15sp')
        self.search.bind(text=self._schedule_search)
        root.add_widget(self.search)
        self.hint = wrap(Label(size_hint_y=None, height=m.h(68), font_size='13sp', halign='left', valign='middle'))
        root.add_widget(self.hint)
        self.rows = BoxLayout(orientation='vertical', spacing=m.h(6))
        self.scroll = wrap_scroll(self.rows, do_scroll_x=False)
        root.add_widget(self.scroll)
        pager = ResponsiveBoxLayout(height_px=44, gap_px=6)
        self.previous = UIButton(text='<', size_hint_x=.14)
        self.previous.bind(on_release=lambda *_: self.change_page(-1))
        self.count = Label(font_size='13sp', size_hint_x=.72)
        self.next = UIButton(text='>', size_hint_x=.14)
        self.next.bind(on_release=lambda *_: self.change_page(1))
        for widget in (self.previous, self.count, self.next):
            pager.add_widget(widget)
        root.add_widget(pager)
        self.source = Label(size_hint_y=None, height=m.h(30), font_size='12sp')
        root.add_widget(self.source)
        self.add_widget(root)
        self.retranslate()
        self.refresh_theme()

    def on_pre_enter(self, *_):
        self.progress = load_learning_progress()
        if not self._loaded:
            self._load_groups()
            self._loaded = True
        else:
            self._render_page()

    def retranslate(self):
        self.heading.text = msg('title')
        self.practice.text = msg('practice')
        self.search.hint_text = msg('search')
        self.source.text = msg('source')
        self._updating = True
        self.puzzle_select.values = [puzzle_label(p) for p in PUZZLES]
        self.puzzle_select.text = puzzle_label(self.puzzle)
        self._updating = False
        if self._loaded:
            self._load_groups(self.group['id'] if self.group else None)

    def refresh_theme(self):
        theme = self._theme()
        for label in (self.heading, self.hint, self.count):
            label.color = theme.text
        self.source.color = theme.text_muted
        self.search.foreground_color = theme.text
        self.search.background_color = theme.surface
        self.search.cursor_color = theme.accent
        if self._loaded:
            self._render_page()

    def _theme(self):
        from kivy.app import App
        return App.get_running_app().theme

    def _puzzle_changed(self, _widget, text):
        if self._updating:
            return
        self.puzzle = next(p for p in PUZZLES if puzzle_label(p) == text)
        self._load_groups()

    def _load_groups(self, preferred=None):
        choices = groups(self.puzzle)
        selected = next((g for g in choices if g['id'] == preferred), None)
        if selected is None:
            default = {'3x3': 'F2L', '2x2': 'OrtegaOLL'}.get(self.puzzle)
            selected = next((g for g in choices if g['id'] == default), choices[0])
        self._choices = {title(g, current_language()) + f" ({len(g['cases'])})": g for g in choices}
        self._updating = True
        self.set_select.values = list(self._choices)
        self.set_select.text = next(label for label, group in self._choices.items() if group is selected)
        self._updating = False
        self.group = selected
        self.page = 0
        self.search.text = ''
        self._render_page()

    def _set_changed(self, _widget, text):
        if self._updating or text not in getattr(self, '_choices', {}):
            return
        self.group = self._choices[text]
        self.page = 0
        self._render_page()

    def _schedule_search(self, *_):
        if self._search_event:
            self._search_event.cancel()
        self.page = 0
        self._search_event = Clock.schedule_once(lambda _dt: self._render_page(), .2)

    def _render_page(self):
        if not self.group:
            return
        self._revision += 1
        revision = self._revision
        self.rows.clear_widgets()
        self.hint.text = prerequisite(self.group, current_language())
        matched = search_cases(self.group, self.search.text)
        pages = max(1, math.ceil(len(matched) / self.PAGE_SIZE))
        self.page = max(0, min(self.page, pages - 1))
        self.count.text = msg('count', count=len(matched), page=self.page + 1, pages=pages)
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page + 1 >= pages
        self.scroll.scroll_y = 1
        if not matched:
            self.rows.add_widget(Label(text=msg('empty'), size_hint_y=None, height=m.h(64)))
            return
        page_items = matched[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]
        progress = load_learning_progress()
        for item in page_items:
            row = ResponsiveBoxLayout(height_px=122, gap_px=6)
            image = Image(size_hint_x=.28)
            index = progress.preferred(self.puzzle, item)
            if index is None:
                index = item.get('selected', 0)
            label = item['name'] + (' · ' + item['group'] if item.get('group') else '')
            if 'error' in item:
                label += '\n' + msg('source_check')
            button = UIButton(text=label + '\n' + item['algorithms'][index], font_size='13sp', halign='left')
            button.bind(size=lambda w, size: setattr(w, 'text_size', (size[0] - m.h(12), size[1])))
            button.bind(on_release=lambda *_a, entry=item: self._open_case(entry))
            row.add_widget(image)
            row.add_widget(button)
            tools = BoxLayout(orientation='vertical', size_hint_x=.21, spacing=m.h(4))
            variants = UIButton(text=msg('alternatives', count=len(item['algorithms'])), font_size='12sp')
            variants.bind(on_release=lambda *_a, entry=item: self._alternatives(entry))
            status = UIButton(text=msg(progress.status(self.puzzle, item)), font_size='12sp')
            status.bind(on_release=lambda *_a, entry=item: self._cycle_progress(entry))
            tools.add_widget(variants)
            tools.add_widget(status)
            row.add_widget(tools)
            self.rows.add_widget(row)
            Clock.schedule_once(lambda _dt, entry=item, picture=image, current=revision:
                                self._thumbnail(entry, picture, current), 0)

    def _thumbnail(self, item, picture, revision):
        if 'error' in item or revision != self._revision or not self.manager or self.manager.current != self.name:
            return
        try:
            from ui.screens.demo_menu import render_thumb
            steps = lesson(self.group, item)
            path = render_thumb(steps[0]['cases'][0], MODES[self.puzzle], size=112)
            if path:
                picture.source = path
        except (ValueError, KeyError, IndexError):
            pass

    def change_page(self, direction):
        self.page += direction
        self._render_page()

    def _open_case(self, item, alternative=None):
        try:
            if alternative is None:
                alternative = load_learning_progress().preferred(self.puzzle, item)
            steps = lesson(self.group, item, alternative)
            self.manager.get_screen('DemoScreen').enter_case(
                MODES[self.puzzle], 0, 0, steps, return_screen=self.name)
            self.manager.current = 'DemoScreen'
        except (ValueError, KeyError, IndexError) as exc:
            message = msg('source_check') if 'error' in item else msg('unavailable', error=str(exc))
            popup = Popup(title=item['name'], content=wrap(Label(text=message)), size_hint=(.9, .42))
            theme_popup(popup, self._theme())
            popup.open()

    def _alternatives(self, item):
        content = BoxLayout(orientation='vertical', spacing=m.h(6))
        listing = BoxLayout(orientation='vertical', spacing=m.h(6))
        content.add_widget(wrap_scroll(listing, do_scroll_x=False))
        content.add_widget(Label(text=msg('prefer_play'), size_hint_y=None, height=m.h(36), font_size='13sp'))
        popup = Popup(title=item['name'], content=content, size_hint=(.94, .85))
        for index, algorithm in enumerate(item['algorithms']):
            button = UIButton(text=f'{index + 1}. {algorithm}', size_hint_y=None, height=m.h(82), font_size='14sp')
            button.bind(size=lambda w, size: setattr(w, 'text_size', (size[0] - m.h(12), size[1])))
            def choose(*_, selected=index):
                # Validate the chosen alternative before persisting it.
                try:
                    lesson(self.group, item, selected)
                except ValueError:
                    self._open_case(item, selected)
                    return
                progress = load_learning_progress()
                progress.prefer(self.puzzle, item, selected)
                save_learning_progress(progress)
                popup.dismiss()
                self._open_case(item, selected)
            button.bind(on_release=choose)
            listing.add_widget(button)
        close = UIButton(text=msg('cancel'), size_hint_y=None, height=m.h(44))
        close.bind(on_release=lambda *_: popup.dismiss())
        content.add_widget(close)
        theme_popup(popup, self._theme())
        popup.open()

    def _cycle_progress(self, item):
        progress = load_learning_progress()
        progress.cycle(self.puzzle, item)
        save_learning_progress(progress)
        self._render_page()

    def open_practice(self, *_):
        practice = self.manager.get_screen('PracticeScreen')
        if self.puzzle in ('2x2', '3x3', 'SQ1', 'Pyraminx') and (practice.puzzle != self.puzzle or not practice.session.question):
            practice.select_puzzle(self.puzzle, self.group['id'] if self.group else None)
        self.manager.current = 'PracticeScreen'
