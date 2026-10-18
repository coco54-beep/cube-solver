"""Direct piece/shape entry, legal turns and solution playback for Square-1."""
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from ui.screens.entry_mixin import EntryActionsMixin
from kivy.uix.slider import Slider

from app.i18n import tr
from cube.square1 import Square1Cube
from cube.square1_entry import Square1Entry
from renderer.square1_view import Square1View
from renderer.camera_follow import follow_turn, square1_target, cancel_follow, reset_camera_view
from ui.widgets.camera_follow import follow_panel
from ui.widgets.square1_entry import Square1Ring,Square1ColorButton
from ui.widgets import metrics as m
from ui.widgets.buttons import UIButton,PrimaryButton,DangerButton
from ui.widgets.dialogs import theme_popup
from ui.widgets.layouts import AdaptiveSceneLayout,ResponsiveBoxLayout


def _app():
    return App.get_running_app()


class Square1Screen(EntryActionsMixin, Screen):
    view_class = Square1View
    demo_mode = True
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._cube=None
        self._work=None
        self._history=[]
        self._slot=0
        self._field=0
        self._entry=None
        self._playback=False
        self._playing=False
        self._hold=None
        self._hold_time=.5
        self._job=None
        self._cancel=threading.Event()
        self._speed=1.
        self._index=0
        self._moves=()
        self._pending_move=None
        self._build()

    def _button(self,row,icon,callback,cls=UIButton):
        button=cls(icon_name=icon)
        button.bind(on_release=lambda *_:callback())
        row.add_widget(button)
        return button

    def _build(self):
        if hasattr(self,'view'):
            self.stop()
            self._cancel_step()
        self.clear_widgets()
        root=AdaptiveSceneLayout()
        top=ResponsiveBoxLayout(height_px=44,gap_px=8)
        self._button(top,'back',self.back)
        self.title=Label(text=tr('directory.square1'),size_hint_x=4,font_size='20sp')
        top.add_widget(self.title)
        if self.demo_mode:
            demo=UIButton(icon_name='demo')
            demo.bind(on_release=lambda *_:self.open_demo())
            top.add_widget(demo)
        if not self._playback:
            self._button(top,'reset',self.reset_view)
        root.add_widget(top)
        self.view=self.view_class()
        self._simple=bool(getattr(_app(),'simple_input',False))
        self.view.lock_rotation=not self._playback or self._simple
        self.view.on_pick=self.select_surface
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=7,size_hint_y=None)
        self.status=Label(size_hint_y=None,height=m.h(40),font_size='13sp',halign='center',valign='middle')
        self.status.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        panel.add_widget(self.status)
        if not self._playback:
            headers=ResponsiveBoxLayout(height_px=22,gap_px=8)
            for key in ('square1.top','square1.bottom'):
                headers.add_widget(Label(text=tr(key),font_size='13sp'))
            panel.add_widget(headers)
            row=ResponsiveBoxLayout(height_px=132,gap_px=8)
            self.rings=[Square1Ring(layer,self.select_slot) for layer in (0,1)]
            for ring in self.rings:
                row.add_widget(ring)
            panel.add_widget(row)
            row=ResponsiveBoxLayout(height_px=36,gap_px=7)
            self.shape_buttons=[]
            for width,key in ((1,'square1.edge_block'),(2,'square1.corner_block')):
                button=UIButton(text=tr(key))
                button.bind(on_release=lambda *_,w=width:self.choose_shape(w))
                self.shape_buttons.append(button)
                row.add_widget(button)
            for amount,key in ((-1,'square1.rotate_left'),(1,'square1.rotate_right')):
                button=UIButton(text=tr(key))
                button.bind(on_release=lambda *_,a=amount:self.rotate_layer(a))
                row.add_widget(button)
            panel.add_widget(row)
            row=ResponsiveBoxLayout(height_px=38,gap_px=7)
            self.color_fields=[]
            for field,key in enumerate(('square1.cap','square1.side1','square1.side2')):
                button=Square1ColorButton(text=tr(key))
                button.bind(on_release=lambda *_,f=field:self.select_field(f))
                self.color_fields.append(button)
                row.add_widget(button)
            panel.add_widget(row)
            row=ResponsiveBoxLayout(height_px=36,gap_px=5)
            self.swatches=[]
            for color,key in enumerate(('white','red','green','yellow','orange','blue')):
                button=Square1ColorButton(text=tr('square1.color.'+key))
                button.set_color(color)
                button.bind(on_release=lambda *_,c=color:self.paint(c))
                self.swatches.append(button)
                row.add_widget(button)
            panel.add_widget(row)
            row=ResponsiveBoxLayout(height_px=36,gap_px=7)
            self.middle_buttons=[]
            for value,key in enumerate(('square1.middle_flat','square1.middle_slanted')):
                button=UIButton(text=tr(key))
                button.bind(on_release=lambda *_,v=value:self.set_middle(v))
                self.middle_buttons.append(button)
                row.add_widget(button)
            panel.add_widget(row)
            row=ResponsiveBoxLayout(height_px=44,gap_px=6)
            for icon,callback,cls in (('random',self.randomize,UIButton),('clear',self.clear,DangerButton),
                                      ('undo',self.undo,UIButton),('target',self.assign_initial,UIButton),('solve',self.solve,PrimaryButton)):
                self._button(row,icon,callback,cls)
            panel.add_widget(row)
        else:
            self.track=Slider(min=0,max=max(1,len(self._moves)),value=self._index,step=1,size_hint_y=None,height=m.h(38))
            self.track.bind(on_touch_up=lambda w,t:self.seek(round(w.value)) if w.collide_point(*t.pos) else None)
            panel.add_widget(self.track)
            row=ResponsiveBoxLayout(height_px=48,gap_px=8)
            self._playback_buttons={}
            for icon,callback in (('first',lambda:self.seek(0)),('prev',self.prev),('solve',self.play),
                                  ('next',self.next),('last',lambda:self.seek(len(self._moves)) )):
                if icon=='first':
                    callback=self.confirm_start
                elif icon=='last':
                    callback=self.confirm_end
                b=self._button(row,icon,callback,PrimaryButton if icon=='solve' else UIButton)
                if self._simple and icon in ('first','last'):
                    row.remove_widget(b)
                self._playback_buttons[icon]=b
                if icon=='solve':
                    self.play_button=b
            panel.add_widget(row)
            row=ResponsiveBoxLayout(height_px=44,gap_px=8)
            row.add_widget(Label(text=tr('playback.speed'),size_hint_x=.25))
            slider=Slider(min=.25,max=2,value=self._speed,step=.25)
            slider.bind(value=lambda w,v:setattr(self,'_speed',v))
            row.add_widget(slider)
            panel.add_widget(row)
            row=ResponsiveBoxLayout(height_px=44,gap_px=8)
            row.add_widget(Label(text=tr('playback.hold'),size_hint_x=.25))
            slider=Slider(min=0,max=6,value=self._hold_time,step=.1)
            slider.bind(value=lambda w,v:setattr(self,'_hold_time',max(0.0,v)))
            row.add_widget(slider)
            panel.add_widget(row)
            if not self._simple:
                row=ResponsiveBoxLayout(height_px=44,gap_px=8)
                self._button(row,'reset',self.reset_view)
                panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=8)
        self._button(row,'prev',lambda:self.view.turn_view(-1))
        self._button(row,'next',lambda:self.view.turn_view(1))
        panel.add_widget(row)
        self.panel=panel
        panel,self.follow_control=follow_panel(panel,self.view)
        root.set_content(self.view,panel)
        self.add_widget(root)

    def on_pre_enter(self,*args):
        if self._cube is not _app().cube:
            self._cube=_app().cube
            self._history=[]
            self._entry=Square1Entry()
            self._slot=self._field=0
            self._playback=False
            self._build()
        elif self._simple!=bool(getattr(_app(),'simple_input',False)):
            self._build()
        self._refresh()

    def _refresh(self,message=None):
        if self._cube is None:
            return
        shown=self._work if self._playback else self._entry
        if self.view.cube is not shown:
            self.view.set_cube(shown)
        self.view.recorded=None
        if self._playback:
            move=str(self._moves[self._index-1]) if self._index else tr('playback.ready')
            self.status.text=tr('poly.step',done=self._index,total=len(self._moves))+' · '+move
            self.track.value=self._index
            self.play_button.icon_name='pause' if self._playing else 'solve'
            busy=self.view._move is not None or self._pending_move is not None
            self._playback_buttons['first'].disabled=busy or self._index<=0
            self._playback_buttons['prev'].disabled=busy or self._index<=0
            self._playback_buttons['next'].disabled=busy or self._index>=len(self._moves)
            self._playback_buttons['last'].disabled=busy or self._index>=len(self._moves)
            self.play_button.disabled=not self._moves
        else:
            self.status.text=message or tr('square1.color_hint',done=self._entry.complete_count())
            self.view.selected=(self._slot,self._field)
            identity=self._entry.slots[self._slot]
            block=self._entry.blocks.get(identity)
            for width,button in enumerate(self.shape_buttons,1):
                button.active=block is not None and block.width==width
            for field,button in enumerate(self.color_fields):
                button.disabled=block is None or field>block.width
                button.active=field==self._field and not button.disabled
                button.set_color(block.colors[field] if not button.disabled else -2)
            for color,button in enumerate(self.swatches):
                button.disabled=block is None or ((color in (0,3))!=(self._field==0))
                button.opacity=.3 if button.disabled else 1
            for value,button in enumerate(self.middle_buttons):
                button.active=value==self._entry.middle
            for ring in self.rings:
                ring.refresh(self._entry,(self._slot,self._field))
        self.status.color=_app().theme.text
        self.title.color=_app().theme.text
        self.view.refresh()

    def select_surface(self,selection):
        if isinstance(selection,tuple):
            self.select_slot(*selection)

    def select_slot(self,slot,field=0):
        if not self._playback and slot<24 and self._job is None and self.view._move is None:
            self._slot=self._entry.block_start(slot)
            self._field=field
            self._refresh()

    def select_field(self,field):
        block=self._entry.blocks.get(self._entry.slots[self._slot])
        if self._job is not None or block is None or field>block.width:
            return
        self._field=field
        self._refresh()

    def _remember(self):
        self._history.append((self._entry.clone(),self._slot,self._field))
        self._history=self._history[-40:]

    def choose_shape(self,width):
        if self._job is not None or self.view._move is not None:
            return
        self._remember()
        self._slot=self._entry.set_shape(self._slot,width)
        self._field=0
        self._refresh()

    def paint(self,color):
        block=self._entry.blocks.get(self._entry.slots[self._slot])
        if self._job is not None or block is None or ((color in (0,3))!=(self._field==0)):
            return
        self._remember()
        self._entry.paint(self._slot,self._field,color)
        self._field=(self._field+1)%(block.width+1)
        self._refresh()

    def rotate_layer(self,amount):
        if self._job is not None:
            return
        self._remember()
        layer=self._slot//12
        self._entry.rotate_layer(layer,amount)
        self._slot=self._entry.block_start(layer*12+(self._slot%12-amount)%12)
        self._refresh()

    def randomize(self):
        if self._job is not None or self.view._move is not None:
            return
        generated=Square1Cube().scramble()
        self._remember()
        self._entry=Square1Entry(generated,colored=True)
        self._slot=self._entry.block_start(0)
        self._field=0
        self._refresh()

    def clear(self):
        if self._job is not None or self.view._move is not None:
            return
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        label=Label(text=tr('poly.clear'),halign='center',valign='middle')
        label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        buttons=ResponsiveBoxLayout(height_px=48,gap_px=8)
        cancel=UIButton(icon_name='cancel')
        danger=DangerButton(icon_name='clear')
        buttons.add_widget(cancel)
        buttons.add_widget(danger)
        content.add_widget(label)
        content.add_widget(buttons)
        popup=Popup(title=tr('input.clear.title'),content=content,size_hint=(.86,.34))
        theme_popup(popup,_app().theme)
        cancel.bind(on_release=lambda *_:popup.dismiss())
        danger.bind(on_release=lambda *_:(self._clear_now(),popup.dismiss()))
        popup.open()

    def _clear_now(self):
        if not self.entry_can_edit():
            return
        self._remember()
        self._entry=Square1Entry()
        self._slot=self._field=0
        self._refresh()

    def undo(self):
        if self._job is not None or self.view._move is not None:
            return
        if self._history:
            self._entry,self._slot,self._field=self._history.pop()
            self._refresh()

    def set_middle(self,value):
        if self._job is not None or self.view._move is not None:
            return
        self._remember()
        self._entry.middle=value
        self._refresh()

    def validate(self):
        if not self.entry_can_edit():
            return
        try:
            entered=self._entry.to_cube()
            self._cube.slots,self._cube.middle=entered.slots,entered.middle
            self._refresh(tr('poly.valid'))
            return True
        except ValueError as exc:
            self._refresh(tr(str(exc)))
            return False

    # ---- EntryActionsMixin 钩子 ----
    def entry_can_assign(self):
        return self._job is None and self.view._move is None

    def entry_reset_solved(self):
        self._remember()
        solved=Square1Cube.solved()
        self._entry=Square1Entry(solved,colored=True)
        self._slot=self._entry.block_start(0)
        self._field=0
        entered=self._entry.to_cube()
        self._cube.slots,self._cube.middle=entered.slots,entered.middle

    def entry_commit_state(self):
        _app().cube=self._cube
        self._refresh()

    def entry_set_status(self, text, error=False):
        self.status.text=text

    def solve(self):
        if self._job is not None or self.view._move is not None or not self.validate():
            return
        initial=self._cube.clone()
        def solved(result):
            self._initial=initial
            self._moves=tuple(result.moves)
            self._work=initial.clone()
            self._index=0
            self._playback=True
            self._build()
            self._refresh()
            self.manager.current=self.name
        screen=self.manager.get_screen('SolvingScreen')
        screen.configure(initial,self.name,solved,self.view_class)
        self.manager.current='SolvingScreen'

    def next(self):
        self.stop()
        self._advance()

    def _advance(self):
        if self.view._move is not None or self._pending_move is not None:
            return
        if self._index>=len(self._moves):
            self.stop()
            return
        def done():
            self._index+=1
            self._refresh()
            if self._playing:
                self._hold=Clock.schedule_once(lambda dt:self._advance(),self._hold_time)
        self._animate_followed(self._moves[self._index],done)

    def prev(self):
        self.stop()
        if self.view._move is None and self._pending_move is None and self._index>0:
            def done():
                self._index-=1
                self._refresh()
            self._animate_followed(self._moves[self._index-1].inverse(),done)

    def _animate_followed(self,move,done):
        self._pending_move=move
        def begin():
            if self._pending_move is not move:
                return
            self._pending_move=None
            self.view.animate_move(move,done,.32/self._speed)
        follow_turn(self.view,square1_target(move),begin)

    def _cancel_step(self):
        self._pending_move=None
        cancel_follow(self.view)
        self.view.cancel_animation()

    def play(self):
        if self._playing:
            self.stop()
        else:
            self._playing=True
            self._refresh()
            self._advance()

    def stop(self):
        self._playing=False
        if self._hold:
            self._hold.cancel()
        self._hold=None
        if self._work is not None:
            self._refresh()

    def seek(self,index):
        self.stop()
        self._cancel_step()
        self._index=max(0,min(len(self._moves),index))
        self._work=self._initial.clone()
        self._work.apply_moves(self._moves[:self._index])
        self._refresh()

    def confirm_start(self):
        self._confirm_seek(tr('playback.confirm.start'),0)

    def open_demo(self):
        if self._job is not None or self.view._move is not None:
            return
        self.manager.get_screen('DemoMenuScreen').set_mode(('square1',3))
        self.manager.current='DemoMenuScreen'

    def confirm_end(self):
        self._confirm_seek(tr('playback.confirm.end'),len(self._moves))

    def confirm_back(self):
        self.stop()
        self._confirm_action(tr('playback.confirm.back'),self._return_to_input)

    def _confirm_seek(self,message,index):
        self.stop()
        self._confirm_action(message,lambda:self.seek(index))

    def _confirm_action(self,message,action):
        self.stop()
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        label=Label(text=message,halign='center',valign='middle')
        label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        buttons=ResponsiveBoxLayout(height_px=48,gap_px=8)
        cancel=UIButton(icon_name='cancel')
        confirm=PrimaryButton(icon_name='done')
        buttons.add_widget(cancel)
        buttons.add_widget(confirm)
        content.add_widget(label)
        content.add_widget(buttons)
        popup=Popup(title=tr('confirm.title'),content=content,size_hint=(.86,.34))
        theme_popup(popup,_app().theme)
        cancel.bind(on_release=lambda *_:popup.dismiss())
        confirm.bind(on_release=lambda *_:(action(),popup.dismiss()))
        popup.open()

    def reset_view(self):
        if self._pending_move is not None:
            return
        reset_camera_view(self.view)

    def back(self):
        if self._playback:
            self.confirm_back()
        else:
            self.reset_interaction()
            self.manager.current='HomeScreen'

    def _return_to_input(self):
        self.reset_interaction()
        if self._playback:
            self._playback=False
            self._build()
            self._refresh()

    def reset_interaction(self):
        self.stop()
        self._cancel_step()
        self.view.cancel_touch()
        self._cancel.set()
        self._job=None
        if getattr(self,'_popup',None):
            self._popup.dismiss()

    def on_leave(self,*args):
        self.reset_interaction()

    def refresh_theme(self):
        self._refresh()

    def retranslate(self):
        self._build()
        self._refresh()
