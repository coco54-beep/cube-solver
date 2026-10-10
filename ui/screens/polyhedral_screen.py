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
from renderer.polyhedral_view import PolyhedralView, PolyhedralTwistView, default_palette
from renderer.cube_orientation import CubeOrientation
from renderer.mat4 import Mat4
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
        self._view_busy=False
        self._view_direction=None
        self._view_orientation=None
        self._build()

    def _build(self):
        root=AdaptiveSceneLayout(padding_px=[12,8,12,8],gap_px=8)
        self._root_layout=root
        top=ResponsiveBoxLayout(height_px=44,gap_px=8)
        back=UIButton(icon_name='back',size_hint_x=.16)
        back.bind(on_release=lambda *_:self.back())
        self.title=Label(font_size='20sp')
        help_button=UIButton(icon_name='demo',size_hint_x=.16)
        help_button.bind(on_release=lambda *_:self.open_demo())
        self.demo_button=help_button
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
            self._view_orientation=None
            if self._cube.puzzle_kind=='skewb':
                self._view_orientation=CubeOrientation(self._cube.n)
                self.view.set_whole_world(self._view_orientation.world)
                self.view.yaw=self.view.pitch=0
                self._face=2  # F, matching ordinary input's initial face.
            elif self._cube.puzzle_kind in ('pyraminx','moyu'):
                self.view.set_whole_world(Mat4())
                self._set_face_camera(0)
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
        if self._job is not None or self._view_busy:
            return
        self._remember()
        self._cube.colors[index]=self._color
        self.view.selected=index
        self._refresh()

    def _refresh(self):
        if self._cube is None:
            return
        self.demo_button.disabled=self._cube.n>5
        self.demo_button.opacity=1 if self._cube.n<=5 else 0
        self.status.text=tr('poly.progress',done=sum(c>=0 for c in self._cube.colors),
                            total=len(self._cube.colors))
        self.view.refresh()

    def open_demo(self):
        if self._job is not None or self._cube is None or self._cube.n>5:
            return
        self.manager.get_screen('DemoMenuScreen').set_mode((self._cube.puzzle_kind,self._cube.n))
        self.manager.current='DemoMenuScreen'

    def change_view(self,direction):
        if self._view_busy or self._job is not None:
            return
        self._view_busy=True
        self.panel.disabled=True
        if self._view_orientation is not None:
            self._view_direction=direction
            ori=self._view_orientation
            angle,axis=ori.prev_axis_deg() if direction<0 else ori.next_axis_deg()
            self.view.animate_whole_turn(axis,angle,.55,on_done=self._finish_cube_view)
            return
        self._face=(self._face+direction)%len(self._cube.geometry.spec.normals)
        yaw,pitch=self._face_camera(self._face)
        roll=self._face_roll(self._face)
        while yaw-self.view.yaw>180:
            yaw-=360
        while yaw-self.view.yaw<-180:
            yaw+=360
        while roll-self.view.roll>180:
            roll-=360
        while roll-self.view.roll<-180:
            roll+=360
        Animation.cancel_all(self.view,'yaw','pitch','roll')
        animation=Animation(yaw=yaw,pitch=pitch,roll=roll,duration=.55,t='in_out_sine')
        animation.bind(on_complete=lambda *_:self._finish_face_view())
        animation.start(self.view)

    def _face_camera(self,index):
        x,y,z=self._cube.geometry.spec.normals[index]
        yaw=math.degrees(math.atan2(x,z))
        pitch=math.degrees(math.asin(y))
        return yaw,pitch

    def _set_face_camera(self,index):
        self.view.yaw,self.view.pitch=self._face_camera(index)
        self.view.roll=self._face_roll(index)

    def _face_roll(self,index):
        # Keep each tetrahedral face upright, with the same convention for
        # both Pyraminx and the curved Tower model.
        if self._cube.puzzle_kind in ('pyraminx','moyu'):
            return 180 if self._cube.geometry.spec.normals[index][1]>0 else 0
        return 0

    def _finish_cube_view(self):
        direction=self._view_direction
        if direction is None:
            return
        ori=self._view_orientation
        ori.turn_prev() if direction<0 else ori.turn_next()
        self.view.set_whole_world(ori.world)
        self._face={'U':0,'R':1,'F':2,'D':3,'L':4,'B':5}[ori.current_face()]
        self._view_direction=None
        self._finish_face_view()

    def _finish_face_view(self):
        self._view_busy=False
        self.panel.disabled=self._job is not None

    def reset_interaction(self):
        self.view.cancel_touch()
        self.view.cancel_animation()
        self._view_direction=None
        if self._view_orientation is not None:
            self.view.set_whole_world(self._view_orientation.world)
        elif self._cube is not None and self._view_busy:
            self._set_face_camera(self._face)
        self._finish_face_view()

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
        actions=ResponsiveBoxLayout(height_px=44,gap_px=8)
        restore=UIButton(text=tr('poly.restore_colors'))
        apply=PrimaryButton(text=tr('poly.apply'))
        actions.add_widget(restore)
        actions.add_widget(apply)
        box.add_widget(actions)
        popup=self._popup(tr('poly.palette'),box,(.9,.85))
        def save(*args):
            palette=list(self.view.palette)
            palette[self._color]=tuple(picker.color[:3])+(1,)
            self._save_palette(palette)
            popup.dismiss()
        def reset(*args):
            self._save_palette(default_palette(self._cube))
            picker.color=self.view.palette[self._color]
        restore.bind(on_release=reset)
        apply.bind(on_release=save)

    def _save_palette(self,palette):
        self.view.palette=tuple(palette)
        from app.prefs import set as pref_set
        pref_set('poly_palette_'+self._cube.puzzle_kind,[list(c) for c in palette])
        self._build_palette()
        self.view.refresh()

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
        self.reset_interaction()
        self.panel.disabled=False
        self.manager.current='IrregularDirectoryScreen'

    def on_leave(self,*args):
        self._cancel_solve()
        self.reset_interaction()
        self.panel.disabled=False

    def _cancel_solve(self):
        self._cancel.set()
        self._job=None
        if self._solve_popup:
            self._solve_popup.dismiss()
            self._solve_popup=None

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
        self.build_ui()

    def build_ui(self):
        from ui.screens.playback_screen import _ProgressTrack
        self._simple=bool(getattr(_app(),'simple_input',False))
        root=AdaptiveSceneLayout(padding_px=[28,8,28,8],gap_px=6)
        self.view=PolyhedralView()
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=8,size_hint_y=None)
        self.view.lock_rotation=self._simple
        info=ResponsiveBoxLayout(orientation='vertical',height_px=72,gap_px=4)
        self.title=Label(font_size='15sp',halign='center')
        self.status=Label(font_size='18sp',halign='center')
        for label in (self.title,self.status):
            label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
            info.add_widget(label)
        panel.add_widget(info)
        self.track=_ProgressTrack(maximum=1,value=0,size_hint_y=None,height=m.h(6))
        panel.bind(height=lambda *_:setattr(self.track,'height',m.h(6)))
        panel.add_widget(self.track)
        controls=ResponsiveBoxLayout(orientation='vertical',height_px=110,gap_px=6)
        row=ResponsiveBoxLayout(gap_px=8)
        self._playback_buttons={}
        for icon,fn in (('first',lambda:self.seek(0)),('prev',self.prev),('solve',self.play),
                        ('next',self.next),('last',lambda:self.seek(len(self._moves)))):
            button=PrimaryButton(icon_name=icon) if icon=='solve' else UIButton(icon_name=icon)
            button.bind(on_release=lambda *_,f=fn:f())
            self._playback_buttons[icon]=button
            if not self._simple or icon not in ('first','last'):
                row.add_widget(button)
            if icon=='solve':
                self.play_button=button
        controls.add_widget(row)
        row=ResponsiveBoxLayout(gap_px=8)
        for icon,fn in (('reset',self.view.reset_camera),('back',self.back)):
            b=UIButton(icon_name=icon)
            b.bind(on_release=lambda *_,f=fn:f())
            if not self._simple or icon=='back':
                row.add_widget(b)
        controls.add_widget(row)
        panel.add_widget(controls)
        row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self.speed_label=Label(text=tr('playback.speed'),font_size='15sp',size_hint_x=.24)
        self.speed=Slider(min=.25,max=2,value=getattr(self,'_speed_value',1),step=.25,size_hint_x=.76)
        self.speed.bind(value=lambda w,v:setattr(self,'_speed_value',v))
        row.add_widget(self.speed_label)
        row.add_widget(self.speed)
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self.hold_label=Label(text=tr('playback.hold'),font_size='15sp',size_hint_x=.24)
        self.hold=Slider(min=0.0,max=6.0,value=self._hold_time,step=0.1,size_hint_x=.76)
        self.hold.bind(value=lambda inst,val:setattr(self,'_hold_time',max(0.0,val)))
        row.add_widget(self.hold_label)
        row.add_widget(self.hold)
        panel.add_widget(row)
        root.set_content(self.view,panel)
        self.add_widget(root)

    def retranslate(self):
        self.speed_label.text=tr('playback.speed')
        self.hold_label.text=tr('playback.hold')
        if self._work is not None:
            self._refresh()

    def refresh_theme(self):
        if self._work is not None:
            self._refresh()

    def on_pre_enter(self,*args):
        self.stop()
        if self._simple!=bool(getattr(_app(),'simple_input',False)):
            self.view.cancel_animation()
            self.clear_widgets()
            self.build_ui()
        self._initial,self._moves,palette=_app().polyhedral_solution
        self._work=self._initial.clone()
        self._index=0
        self._checkpoints={0:tuple(self._work.colors)}
        self.view.set_cube(self._work)
        if len(palette)==len(self._work.geometry.spec.normals):
            self.view.palette=palette
        self.track.maximum=max(1,len(self._moves))
        self.title.text=tr('poly.solution',total=len(self._moves))
        self._refresh()

    def _refresh(self):
        from demo.irregular_cases import token
        current=(token(self.view._move) if self.view._move is not None else
                 token(self._moves[self._index-1]) if self._index else tr('playback.ready'))
        self.title.text=tr('playback.current',move=current)
        self.status.text=tr('poly.step',done=self._index,total=len(self._moves))
        self.track.value=self._index
        self.play_button.icon_name='pause' if self._playing else 'solve'
        busy=self.view._move is not None or self._seek_job is not None
        self._playback_buttons['prev'].disabled=busy or self._index<=0
        self._playback_buttons['next'].disabled=busy or self._index>=len(self._moves)
        self._playback_buttons['first'].disabled=busy or self._index<=0
        self._playback_buttons['last'].disabled=busy or self._index>=len(self._moves)
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
        self._refresh()

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
        self._refresh()

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
