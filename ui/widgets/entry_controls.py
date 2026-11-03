"""Shared placement and sizing of controls on puzzle entry screens."""
from kivy.uix.label import Label
from ui.widgets.buttons import UIButton, PrimaryButton, DangerButton
from ui.widgets.layouts import ResponsiveBoxLayout


class EntryActionRow(ResponsiveBoxLayout):
    """Simple mode exposes only essentials; advanced mode exposes all tools."""
    simple_keys = ('twist', 'random', 'clear', 'undo', 'solve')
    play_keys = ('twist', 'random', 'undo', 'target', 'solve')
    def __init__(self,owner,state,**kwargs):
        super().__init__(height_px=48,gap_px=6,**kwargs)
        self.owner=owner;self.task_state=state;self.buttons={};self.labels={};self.original={};self.hidden_keys=set()
        self.bind(width=lambda *_:self.reflow())

    def add_action(self,key,button):
        # Screen-specific actions can supply an icon; the one common local
        # clear action uses X, distinct from the whole-draft trash button.
        if not button.icon_name and key=='clear_piece':button.icon_name='cancel'
        if button.icon_name:button.text=''
        self.buttons[key]=button;self.original[key]=(button.icon_name,button.text,button.size_hint_x,button.size_hint_y,button.height)

    def add_secondary(self,key,button):
        if button.parent:button.parent.remove_widget(button)
        self.add_action(key,button);self.reflow()

    def action_label(self,key):
        from app.i18n import tr
        if key in self.labels:return self.labels[key]
        if key=='pick' and getattr(self.owner,'_uses_standard_palette',lambda:False)():return tr('palette.settings')
        return tr('entry.action_'+key)

    def reflow(self):
        from kivy.app import App
        simple=bool(getattr(App.get_running_app(),'simple_input',False))
        self.clear_widgets()
        # First detach every registered tool: secondary buttons must not stay
        # attached to an old toolbar after mode or screen changes.
        for key in self.buttons:
            button=self.buttons[key]
            if button.parent:button.parent.remove_widget(button)
            icon,text,size_hint_x,size_hint_y,height=self.original[key]
            # Keep current icons such as the standard cube's palette gear.
            # Reflow must never restore an outdated pipette.
            button.icon_name=button.icon_name or icon
            button.text='' if button.icon_name else self.action_label(key)
            button.size_hint_x=size_hint_x;button.size_hint_y=size_hint_y;button.height=height
        keys=(self.play_keys if getattr(self.owner,'play_only',False) else self.simple_keys) if simple else self.buttons
        for key in keys:
            if key in self.buttons and key not in self.hidden_keys:self.add_widget(self.buttons[key])

GALLERY_COLUMNS = 4
GALLERY_PAGE_SIZE = 8


def entry_header(title, back, help_callback=None):
    row = ResponsiveBoxLayout(height_px=44, gap_px=8)
    previous = UIButton(icon_name='back', size_hint_x=.22)
    previous.bind(on_release=lambda *_: back())
    title.size_hint_x = .56
    title.font_size = '20sp'
    _fit_header_title(title)
    help_button = UIButton(icon_name='demo', size_hint_x=.22)
    if help_callback is None:
        help_button.disabled = True
        help_button.opacity = 0
    else:
        help_button.bind(on_release=lambda *_: help_callback())
    for widget in (previous, title, help_button):
        row.add_widget(widget)
    return row, previous, help_button


def _fit_header_title(title):
    title.halign='center';title.valign='middle';title.shorten=True;title.shorten_from='right'
    title.bind(size=lambda widget,_:setattr(widget,'text_size',widget.size))


def twist_header(title,back):
    row=ResponsiveBoxLayout(height_px=48,gap_px=8)
    previous=UIButton(icon_name='back',size_hint_x=.22)
    done=PrimaryButton(icon_name='done',size_hint_x=.22)
    for button in (previous,done):button.bind(on_release=lambda *_:back())
    title.size_hint_x=.56;title.font_size='20sp';_fit_header_title(title)
    for widget in (previous,title,done):row.add_widget(widget)
    return row,previous,done


def bind_random_action(button, callback):
    """Bind a scramble action and lock its button until generation completes."""
    owner = getattr(callback, '__self__', None)
    state=getattr(owner,'entry_state',None)
    if state is not None:
        from ui.entry_state import lock_controls
        lock_controls(state,button)

    def release(*_):
        if button.disabled:
            return
        button.disabled = True
        try:
            if state is None:callback()
            else:
                with state.requesting('scrambling'):callback()
        except Exception as exc:
            cancel=getattr(owner,'_cancel',None)
            if cancel is not None and hasattr(cancel,'set'):cancel.set()
            if state is not None:state.cancel()
            button.disabled = False
            if hasattr(owner,'entry_show_error'):
                from kivy.logger import Logger
                from services.failures import classify
                Logger.exception('Entry scramble failed')
                owner.entry_show_error(str(exc),kind='operation',category=classify(exception=exc),retry=callback)
                return
            raise
        button.disabled=state.locked if state is not None else False

    button.bind(on_release=release)
    return button


def entry_actions(*, randomize, clear, undo, assign, solve, twist=None):
    """Use one icon and position for each action across entry families."""
    state=getattr(getattr(randomize,'__self__',None),'entry_state',None)
    row=EntryActionRow(getattr(randomize,'__self__',None),state)
    if state is not None:
        from ui.entry_state import lock_controls
        lock_controls(state,row)
    buttons = {}
    for icon, callback, cls in (
            ('twist', twist, UIButton), ('random', randomize, UIButton),
            ('clear', clear, DangerButton), ('undo', undo, UIButton),
            ('target', assign, UIButton), ('solve', solve, PrimaryButton)):
        if callback is None:
            continue
        button = cls(icon_name=icon)
        if icon == 'random':
            bind_random_action(button, callback)
        else:
            button.bind(on_release=lambda *_, fn=callback: fn())
        row.add_action(icon,button)
        buttons[icon] = button
    row.reflow()
    return row, buttons


class EntryGalleryPager(ResponsiveBoxLayout):
    def __init__(self, change_page, **kwargs):
        super().__init__(height_px=30, gap_px=6, **kwargs)
        self.previous = UIButton(icon_name='prev')
        self.label = Label(font_size='12sp')
        self.next = UIButton(icon_name='next')
        self.previous.bind(on_release=lambda *_: change_page(-1))
        self.next.bind(on_release=lambda *_: change_page(1))
        for widget in (self.previous, self.label, self.next):
            self.add_widget(widget)
        self.set_page(0, 1)

    def set_page(self, page, count):
        count = max(1, count)
        page = max(0, min(page, count-1))
        self._height_px = 30 if count > 1 else 0
        self.opacity = 1 if count > 1 else 0
        self.disabled = count <= 1
        self.previous.disabled = page == 0
        self.next.disabled = page == count-1
        self.label.text = f'{page+1}/{count}'
        self._sync_metrics()
        return page
