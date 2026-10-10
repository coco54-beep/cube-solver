"""Responsive polyhedral sticker entry and solution playback."""
import math
import threading

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner

from app.i18n import tr
from cube.polyhedral import Move
from renderer.polyhedral_view import PolyhedralView, PolyhedralTwistView
from ui.screens.mastermorphix_screen import _Swatch
from ui.widgets.buttons import UIButton,PrimaryButton,DangerButton
from ui.widgets.dialogs import theme_popup
from ui.widgets.layouts import AdaptiveSceneLayout,ResponsiveBoxLayout
from ui.widgets import metrics as m


def _app():
    return App.get_running_app()


class PolyhedralScreen(Screen):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._cube=None
        self._history=[]
        self._face=0
        self._axis=0
        self._layer=0
        self._color=0
        self._job=None
        self._solve_popup=None
        self._cancel=threading.Event()
        self._build()

    def _build(self):
        root=AdaptiveSceneLayout(padding_px=[12,8,12,8],gap_px=8)
        self._root_layout=root
        top=ResponsiveBoxLayout(height_px=44,gap_px=8)
        back=UIButton(icon_name='back',size_hint_x=.16)
        back.bind(on_release=lambda *_:self.back())
        self.title=Label(font_size='20sp')
        help_button=UIButton(icon_name='demo',size_hint_x=.16)
        help_button.bind(on_release=lambda *_:self.help())
        for item in (back,self.title,help_button):
            top.add_widget(item)
        root.add_widget(top)
        self.view=PolyhedralView()
        self.view.on_pick=self.paint
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=7,size_hint_y=None)
        self.palette=ResponsiveBoxLayout(height_px=44,gap_px=5)
        panel.add_widget(self.palette)
        self.palette2=ResponsiveBoxLayout(height_px=44,gap_px=5)
        panel.add_widget(self.palette2)
        self.hint=Label(text=tr('poly.input_hint'),size_hint_y=None,height=m.h(54),
                        font_size='13sp',halign='center',valign='middle')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        panel.add_widget(self.hint)
        observation=ResponsiveBoxLayout(height_px=44,gap_px=6)
        prev=UIButton(icon_name='prev')
        prev.bind(on_release=lambda *_:self.change_view(-1))
        customize=UIButton(icon_name='gear')
        customize.bind(on_release=lambda *_:self.customize())
        nxt=UIButton(icon_name='next')
        nxt.bind(on_release=lambda *_:self.change_view(1))
        for widget in (prev,customize,nxt):
            observation.add_widget(widget)
        panel.add_widget(observation)
        actions=ResponsiveBoxLayout(height_px=48,gap_px=6)
        for cls,icon,callback in ((UIButton,'twist',self.open_twist),
                                  (UIButton,'random',self.randomize),(DangerButton,'clear',self.clear),
                                  (UIButton,'undo',self.undo),(UIButton,'check',self.validate),
                                  (PrimaryButton,'solve',self.solve)):
            button=cls(icon_name=icon)
            button.bind(on_release=lambda *_,fn=callback:fn())
            actions.add_widget(button)
        panel.add_widget(actions)
        self.status=Label(size_hint_y=None,height=m.h(34),font_size='14sp',
                          halign='center',valign='middle')
        self.status.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        panel.add_widget(self.status)
        self.panel=panel
        root.set_content(self.view,panel)
        self.add_widget(root)

    def on_pre_enter(self,*args):
        if self._cube is not _app().cube:
            self._cube=_app().cube
            self._history=[]
            self._axis=self._layer=self._color=self._face=0
            self.view.set_cube(self._cube)
            from app.prefs import get as pref_get
            saved=pref_get('poly_palette_'+self._cube.puzzle_kind,None)
            if isinstance(saved,list) and len(saved)==len(self._cube.geometry.spec.normals) and all(
                isinstance(c,list) and len(c)==4 and all(isinstance(v,(int,float)) and 0<=v<=1 for v in c)
                for c in saved):
                self.view.palette=tuple(tuple(c) for c in saved)
            self.view.selected=None
            self._build_palette()
        self.retranslate()
        self.refresh_theme()
        self._refresh()

    def _build_palette(self):
        self.palette.clear_widgets()
        self.palette2.clear_widgets()
        count=len(self._cube.geometry.spec.normals)
        self.palette2.height=m.h(44) if count>6 else 0
        self.palette2._height_px=44 if count>6 else 0
        self.palette2.opacity=1 if count>6 else 0
        self.palette2.disabled=count<=6
        self._swatches=[]
        for i in range(count):
            button=_Swatch(self.view.palette[i],text=str(i+1),active=i==self._color)
            button.bind(on_release=lambda *_,color=i:self.choose_color(color))
            (self.palette if i<6 else self.palette2).add_widget(button)
            self._swatches.append(button)

    def choose_color(self,color):
        self._color=color
        for i,button in enumerate(self._swatches):
            button.active=i==color

    def _remember(self):
        self._history.append(tuple(self._cube.colors))
        self._history=self._history[-40:]
        _app().polyhedral_solution=None

    def paint(self,index):
        if self._job is not None:
            return
        self._remember()
        self._cube.colors[index]=self._color
        self.view.selected=index
        self._refresh()

    def _refresh(self):
        if self._cube is None:
            return
        self.status.text=tr('poly.progress',done=sum(c>=0 for c in self._cube.colors),
                            total=len(self._cube.colors))
        self.view.refresh()

    def change_view(self,direction):
        self._face=(self._face+direction)%len(self._cube.geometry.spec.normals)
        x,y,z=self._cube.geometry.spec.normals[self._face]
        yaw=math.degrees(math.atan2(x,z))
        while yaw-self.view.yaw>180:
            yaw-=360
        while yaw-self.view.yaw<-180:
            yaw+=360
        pitch=math.degrees(math.asin(y))
        Animation.cancel_all(self.view,'yaw','pitch')
        Animation(yaw=yaw,pitch=pitch,duration=.45,t='in_out_sine').start(self.view)

    def _axis_selected(self,widget,text):
        pass

    def open_twist(self):
        """进入专门的拧动界面（输入界面本身不保留内嵌拧动）。"""
        if self._job is not None:
            return
        self.manager.current='PolyhedralTwistScreen'

    def randomize(self):
        from solver.polyhedral import scramble
        self._remember()
        self._cube.colors=[s.face for s in self._cube.geometry.stickers]
        scramble(self._cube,30)
        self._refresh()

    def undo(self):
        if self._history:
            self._cube.colors=list(self._history.pop())
            self._refresh()

    def clear(self):
        box=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        button=DangerButton(text=tr('poly.confirm'))
        box.add_widget(button)
        popup=self._popup(tr('poly.clear'),box,(.8,.26))
        def confirm(*args):
            self._remember()
            self._cube.colors=[-1]*len(self._cube.colors)
            popup.dismiss()
            self._refresh()
        button.bind(on_release=confirm)

    def validate(self):
        from solver.polyhedral import identify
        try:
            identify(self._cube)
            self.status.text=tr('poly.valid')
        except ValueError as exc:
            self.error(str(exc))

    def solve(self):
        if self._job is not None:
            return
        self._cancel=threading.Event()
        cancellation=self._cancel
        job=object()
        self._job=job
        entered=self._cube.entered()
        self.panel.disabled=True
        cancel=UIButton(text=tr('poly.cancel'),height=m.h(44),size_hint_y=None)
        message=Label(text=tr('poly.solving'))
        box=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        box.add_widget(message)
        box.add_widget(cancel)
        popup=self._popup(tr('poly.solving'),box,(.8,.28),auto_dismiss=False)
        self._solve_popup=popup
        cancel.bind(on_release=lambda *_:cancellation.set())
        def progress(done,total):
            Clock.schedule_once(lambda dt:setattr(message,'text',tr('poly.stage',done=done,total=total)),0)
        def finish(solution=None,error=None):
            if self._job is not job:
                return
            self._job=None
            self.panel.disabled=False
            popup.dismiss()
            self._solve_popup=None
            if cancellation.is_set():
                return
            if error is not None:
                self.error(error)
            else:
                _app().polyhedral_solution=(entered,solution,tuple(self.view.palette))
                self.manager.current='PolyhedralPlaybackScreen'
        def worker():
            try:
                from solver.polyhedral import solve_polyhedral
                solution=solve_polyhedral(entered,cancellation.is_set,progress)
                Clock.schedule_once(lambda dt:finish(solution),0)
            except InterruptedError:
                Clock.schedule_once(lambda dt:finish(),0)
            except Exception as exc:
                error=str(exc)
                Clock.schedule_once(lambda dt:finish(error=error),0)
        threading.Thread(target=worker,daemon=True).start()

    def customize(self):
        picker=ColorPicker(color=self.view.palette[self._color])
        box=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        box.add_widget(picker)
        apply=PrimaryButton(text=tr('poly.apply'),size_hint_y=None,height=m.h(44))
        box.add_widget(apply)
        popup=self._popup(tr('poly.palette'),box,(.9,.85))
        def save(*args):
            palette=list(self.view.palette)
            palette[self._color]=tuple(picker.color[:3])+(1,)
            self.view.palette=tuple(palette)
            from app.prefs import set as pref_set
            pref_set('poly_palette_'+self._cube.puzzle_kind,[list(c) for c in palette])
            self._build_palette()
            self.view.refresh()
            popup.dismiss()
        apply.bind(on_release=save)

    def _popup(self,title,content,size=(.85,.4),**kwargs):
        popup=Popup(title=title,content=content,size_hint=size,**kwargs)
        theme_popup(popup,_app().theme)
        popup.open()
        return popup

    def error(self,message):
        errors={
            'Please enter every sticker':'incomplete',
            'The color counts do not match this puzzle':'counts',
            'A piece has an impossible color combination or position':'piece',
            'A piece has a mirrored or impossible orientation':'orientation',
            'Repeated color on a piece':'piece', 'Duplicate piece':'piece',
            'The entered core has an impossible orientation':'orientation',
            'The entered puzzle is not a legal state':'illegal',
            'Odd orbit permutation':'illegal',
            'The entered pieces violate an orientation or permutation constraint':'illegal',
        }
        message=tr('poly.error.'+errors[message]) if message in errors else tr('poly.error.solver',detail=message)
        content=Label(text=message,halign='center',valign='middle',color=_app().theme.text)
        content.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        self._popup(tr('poly.error'),content)

    def help(self):
        label=Label(text=tr('poly.help'),halign='left',valign='middle',color=_app().theme.text)
        label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        self._popup(tr('poly.help_title'),label,(.94,.78))

    def back(self):
        self._cancel_solve()
        self.view.cancel_animation()
        self.panel.disabled=False
        self.manager.current='IrregularDirectoryScreen'

    def on_leave(self,*args):
        self._cancel_solve()
        self.view.cancel_animation()
        self.panel.disabled=False

    def _cancel_solve(self):
        self._cancel.set()
        self._job=None
        if self._solve_popup:
            self._solve_popup.dismiss()
            self._solve_popup=None

    def reset_interaction(self):
        self.view.cancel_animation()
        self.panel.disabled=self._job is not None

    def retranslate(self):
        if self._cube:
            self.title.text=f'{tr("directory."+self._cube.puzzle_kind)} · {tr("directory.order",order=self._cube.n)}'
        self.hint.text=tr('poly.input_hint')

    def refresh_theme(self):
        for label in (self.title,self.hint,self.status):
            label.color=_app().theme.text


class PolyhedralPlaybackScreen(Screen):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._playing=False
        self._hold=None
        self._hold_time=0.5
        self._work=None
        self._index=0
        self._seek_job=None
        root=AdaptiveSceneLayout(padding_px=[12,8,12,8])
        self.view=PolyhedralView()
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=8,size_hint_y=None)
        self.title=Label(size_hint_y=None,height=m.h(42),font_size='18sp')
        panel.add_widget(self.title)
        self.status=Label(size_hint_y=None,height=m.h(40),font_size='16sp')
        panel.add_widget(self.status)
        self.track=Slider(min=0,max=1,value=0,size_hint_y=None,height=m.h(30))
        self.track.bind(on_touch_up=self._seek_touch)
        panel.add_widget(self.track)
        row=ResponsiveBoxLayout(height_px=48,gap_px=6)
        for icon,fn in (('first',lambda:self.seek(0)),('prev',self.prev),('solve',self.play),
                        ('next',self.next),('last',lambda:self.seek(len(self._moves)))):
            button=PrimaryButton(icon_name=icon) if icon=='solve' else UIButton(icon_name=icon)
            button.bind(on_release=lambda *_,f=fn:f())
            row.add_widget(button)
            if icon=='solve':
                self.play_button=button
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        for icon,fn in (('reset',lambda:self.seek(0)),('back',self.back)):
            b=UIButton(icon_name=icon)
            b.bind(on_release=lambda *_,f=fn:f())
            row.add_widget(b)
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=34,gap_px=6)
        self.speed_label=Label(text=tr('poly.speed'),size_hint_x=.2)
        self.speed=Slider(min=.3,max=3,value=1)
        row.add_widget(self.speed_label)
        row.add_widget(self.speed)
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=34,gap_px=6)
        self.hold_label=Label(text=tr('playback.hold'),size_hint_x=.2)
        self.hold=Slider(min=0.0,max=6.0,value=self._hold_time,step=0.1)
        self.hold.bind(value=lambda inst,val:setattr(self,'_hold_time',max(0.0,val)))
        row.add_widget(self.hold_label)
        row.add_widget(self.hold)
        panel.add_widget(row)
        root.set_content(self.view,panel)
        self.add_widget(root)

    def on_pre_enter(self,*args):
        self.stop()
        self._initial,self._moves,palette=_app().polyhedral_solution
        self._work=self._initial.clone()
        self._index=0
        self._checkpoints={0:tuple(self._work.colors)}
        self.view.set_cube(self._work)
        if len(palette)==len(self._work.geometry.spec.normals):
            self.view.palette=palette
        self.track.max=max(1,len(self._moves))
        self.title.text=tr('poly.solution',total=len(self._moves))
        self._refresh()

    def _refresh(self):
        self.status.text=tr('poly.step',done=self._index,total=len(self._moves))
        self.track.value=self._index
        self.play_button.icon_name='pause' if self._playing else 'solve'
        self.view.refresh()
        for label in (self.title,self.status,self.speed_label,self.hold_label):
            label.color=_app().theme.text

    def next(self,*args):
        if self.view._move is not None or self._seek_job is not None:
            return
        if self._index>=len(self._moves):
            self.stop()
            return
        def done():
            self._index+=1
            if self._index%128==0:
                self._checkpoints[self._index]=tuple(self._work.colors)
            self._refresh()
            if self._playing:
                self._hold=Clock.schedule_once(self.next,self._hold_time)
        self.view.animate_move(self._moves[self._index],done,duration=.32/self.speed.value)

    def prev(self):
        self.stop()
        self.view.cancel_animation()
        if self._seek_job is not None:
            self.seek(self._index-1)
            return
        if self._index<=0:
            self._refresh()
            return
        move=self._moves[self._index-1].inverse(self._work.geometry.spec.turn_order)
        def done():
            self._index-=1
            self._refresh()
        self.view.animate_move(move,done,duration=.32/self.speed.value)

    def play(self):
        if self._seek_job is not None:
            return
        if self._playing:
            self.stop()
        else:
            self._playing=True
            self._refresh()
            self.next()

    def stop(self):
        self._playing=False
        if self._hold:
            self._hold.cancel()
        self._hold=None
        if self._work is not None:
            self._refresh()

    def seek(self,index):
        self.stop()
        self.view.cancel_animation()
        index=max(0,min(len(self._moves),int(index)))
        nearest=max(k for k in self._checkpoints if k<=index)
        job=object()
        self._seek_job=job
        work=self._initial.clone()
        work.colors=list(self._checkpoints[nearest])
        checkpoints={}
        def finish():
            if self._seek_job is not job:
                return
            self._seek_job=None
            self._work.colors=work.colors
            self._checkpoints.update(checkpoints)
            self._index=index
            self._refresh()
        def worker():
            for k in range(nearest,index):
                if self._seek_job is not job:
                    return
                work.apply_move(self._moves[k])
                if (k+1)%128==0:
                    checkpoints[k+1]=tuple(work.colors)
            Clock.schedule_once(lambda dt:finish(),0)
        if index-nearest>128:
            self.status.text=tr('poly.seeking')
            threading.Thread(target=worker,daemon=True).start()
        else:
            worker()

    def _seek_touch(self,widget,touch):
        if widget.collide_point(*touch.pos):
            self.seek(round(widget.value))

    def back(self):
        self.stop()
        self.view.cancel_animation()
        self.manager.current='PolyhedralScreen'

    def on_leave(self,*args):
        self._seek_job=None
        self.stop()
        self.view.cancel_animation()


class PolyhedralTwistScreen(Screen):
    """专门的异形魔方拧动界面：选择转轴/层，顺逆拧动，左右切换观察面。

    与普通魔方的 TwistScreen 一样，录入页本身不再内嵌拧动控件；本页直接
    操作录入中的 PolyhedralPuzzle（同一对象），返回后录入页即时反映改动。
    """

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._cube=None
        self._face=0
        self._axis=0
        self._layer=0
        self._history=[]
        self._future=[]
        self._build()

    def _build(self):
        root=AdaptiveSceneLayout(padding_px=[12,8,12,8],gap_px=8)
        top=ResponsiveBoxLayout(height_px=44,gap_px=8)
        back=UIButton(icon_name='back',size_hint_x=.16)
        back.bind(on_release=lambda *_:self.back())
        self.title=Label(font_size='20sp')
        done=PrimaryButton(icon_name='done',size_hint_x=.16)
        done.bind(on_release=lambda *_:self.back())
        for item in (back,self.title,done):
            top.add_widget(item)
        root.add_widget(top)
        self.view=PolyhedralTwistView()
        self.view.on_twist=self.twist
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=7,size_hint_y=None)
        history=ResponsiveBoxLayout(height_px=48,gap_px=8)
        self.btn_undo=UIButton(icon_name='undo')
        self.btn_undo.bind(on_release=lambda *_:self.undo())
        self.btn_redo=UIButton(icon_name='redo')
        self.btn_redo.bind(on_release=lambda *_:self.redo())
        history.add_widget(self.btn_undo)
        history.add_widget(self.btn_redo)
        panel.add_widget(history)
        observation=ResponsiveBoxLayout(height_px=48,gap_px=8)
        prev=UIButton(icon_name='prev')
        prev.bind(on_release=lambda *_:self.change_view(-1))
        self.btn_lock=UIButton(icon_name='lock')
        self.btn_lock.bind(on_release=lambda *_:self.toggle_lock())
        reset=UIButton(icon_name='reset')
        reset.bind(on_release=lambda *_:self.view.reset_camera())
        nxt=UIButton(icon_name='next')
        nxt.bind(on_release=lambda *_:self.change_view(1))
        for widget in (prev,self.btn_lock,reset,nxt):
            observation.add_widget(widget)
        panel.add_widget(observation)
        layer_row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self.axis=Spinner(text='',values=())
        self.axis.bind(text=self._axis_selected)
        self.layer=Spinner(text='',values=())
        self.layer.bind(text=self._layer_selected)
        backward=UIButton(icon_name='undo',size_hint_x=.28)
        backward.bind(on_release=lambda *_:self.turn(-1))
        forward=UIButton(icon_name='redo',size_hint_x=.28)
        forward.bind(on_release=lambda *_:self.turn(1))
        for item in (self.axis,self.layer,backward,forward):
            layer_row.add_widget(item)
        panel.add_widget(layer_row)
        self.hint=Label(text=tr('twist.hint_lock_on'),size_hint_y=None,height=m.h(54),
                        font_size='13sp',halign='center',valign='middle')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        panel.add_widget(self.hint)
        self.panel=panel
        root.set_content(self.view,panel)
        self.add_widget(root)

    def on_pre_enter(self,*args):
        self._cube=_app().cube
        if self._cube is None or not hasattr(self._cube,'geometry'):
            return
        self.view.cancel_touch()
        self.view.set_cube(self._cube)
        self.view.lock_view=True
        self._history=[]
        self._future=[]
        self._face=0
        self._update_controls()
        from app.prefs import get as pref_get
        saved=pref_get('poly_palette_'+self._cube.puzzle_kind,None)
        count=len(self._cube.geometry.spec.normals)
        if isinstance(saved,list) and len(saved)==count and all(
            isinstance(c,list) and len(c)==4 for c in saved):
            self.view.palette=tuple(tuple(c) for c in saved)
        self.view.selected=None
        self.axis.values=tuple(tr('poly.axis',i=i+1) for i in range(len(self._cube.geometry.spec.axes)))
        self.axis.text=self.axis.values[0]
        self._axis=0
        self._set_layers()
        self.view.reset_camera() if hasattr(self.view,'reset_camera') else None
        self.retranslate()
        self.refresh_theme()
        self.view.refresh()

    def retranslate(self):
        if self._cube is not None:
            self.title.text=f'{tr("directory."+self._cube.puzzle_kind)} · {tr("input.twist")}'
        self.hint.text=tr('poly.twist_hint_on') if self.view.lock_view else tr('poly.twist_hint_off')

    def refresh_theme(self):
        self.title.color=_app().theme.text
        self.hint.color=_app().theme.text

    def change_view(self,direction):
        if self._cube is None or self.view._move is not None:
            return
        self.view.cancel_touch()
        self._face=(self._face+direction)%len(self._cube.geometry.spec.normals)
        x,y,z=self._cube.geometry.spec.normals[self._face]
        yaw=math.degrees(math.atan2(x,z))
        while yaw-self.view.yaw>180:
            yaw-=360
        while yaw-self.view.yaw<-180:
            yaw+=360
        pitch=math.degrees(math.asin(y))
        Animation.cancel_all(self.view,'yaw','pitch')
        self.view.camera_busy=True
        animation=Animation(yaw=yaw,pitch=pitch,duration=.45,t='in_out_sine')
        animation.bind(on_complete=lambda *_:setattr(self.view,'camera_busy',False))
        animation.start(self.view)

    def _axis_selected(self,widget,text):
        if text in widget.values:
            self._axis=widget.values.index(text)
            self._layer=0
            self._set_layers()

    def _set_layers(self):
        if self._cube is None:
            return
        self.layer.values=tuple(tr('poly.layer',i=i+1)
                                for i in range(len(self._cube.geometry.layers[self._axis])))
        self.layer.text=self.layer.values[0]
        self._layer=0

    def _layer_selected(self,widget,text):
        if text in widget.values:
            self._layer=widget.values.index(text)

    def _update_controls(self):
        self.btn_undo.disabled=not self._history
        self.btn_redo.disabled=not self._future
        self.btn_lock.icon_name='lock' if self.view.lock_view else 'unlock'
        self.btn_lock.active=self.view.lock_view

    def toggle_lock(self):
        self.view.cancel_touch()
        self.view.lock_view=not self.view.lock_view
        self._update_controls()
        self.retranslate()

    def twist(self,move):
        if self._cube is None or self.view._move is not None or self.view.camera_busy:
            return
        self._history.append(move)
        self._future.clear()
        self._animate(move)

    def undo(self):
        if self.view._move is not None or self.view.camera_busy or not self._history:
            return
        move=self._history.pop()
        self._future.append(move)
        self._animate(move.inverse(self._cube.geometry.spec.turn_order))

    def redo(self):
        if self.view._move is not None or self.view.camera_busy or not self._future:
            return
        move=self._future.pop()
        self._history.append(move)
        self._animate(move)

    def _animate(self,move):
        self.view.cancel_touch()
        self.panel.disabled=True
        self._update_controls()
        def done():
            _app().polyhedral_solution=None
            self.panel.disabled=False
            self._update_controls()
            self.view.refresh()
        if not self.view.animate_move(move,done):
            self.panel.disabled=False

    def turn(self,direction):
        if self._cube is not None:
            self.twist(Move(self._axis,self._layer,direction%self._cube.geometry.spec.turn_order))

    def back(self):
        if self.view._move is not None:
            return
        self.view.cancel_touch()
        self.view.cancel_animation()
        self.panel.disabled=False
        self.manager.current='PolyhedralScreen'

    def reset_interaction(self):
        self.view.cancel_touch()

    def on_leave(self,*args):
        self.view.cancel_touch()
        self.view.camera_busy=False
        self.view.cancel_animation()
        self.panel.disabled=False
