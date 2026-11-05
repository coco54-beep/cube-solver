"""Shared material puzzle page, with simulation-only public models."""
import math,threading
from collections import Counter
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from app.i18n import tr
from candidate_puzzles import PLAY_ONLY_KINDS
from cube.copter_input import CopterCube,scrambled
from cube.curvy_copter import JUMBLE,multiply
from cube.appearance import IDENTITY_FRAME
from cube.polyhedral import CUBE,EDGE_AXES,Move,rotate
from ui.screens.polyhedral_screen import PolyhedralScreen,PolyhedralTwistScreen,_app
from ui.screens.entry_mixin import EntryActionsMixin
from ui.entry_feedback import validation_action
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.buttons import UIButton,PrimaryButton,DangerButton
from ui.widgets import metrics as m
from renderer.copter_view import CopterView

class CopterInputScreen(PolyhedralScreen):
    view_class=CopterView
    entry_twist_screen='CopterTwistScreen'
    make_scrambled=staticmethod(scrambled)
    pose_presets=(('90°',90.),('180°',180.),('J',JUMBLE),('180° − J',180.-JUMBLE))

    @property
    def play_only(self):
        return getattr(self._cube or getattr(_app(),'cube',None),'puzzle_kind',None) in PLAY_ONLY_KINDS

    def on_pre_enter(self,*args):
        cube=_app().cube
        if cube.puzzle_kind in PLAY_ONLY_KINDS and any(c<0 for c in cube.paints):
            # Retired blank-entry checkpoints must also open a complete model.
            _app().cube=type(cube)();_app().polyhedral_solution=None;_app().solve_result=None
        fresh=self._cube is not _app().cube
        super().on_pre_enter(*args)
        if self.play_only and fresh:
            from renderer.mat4 import Mat4
            self.view.set_whole_world(Mat4())
            self.view.yaw,self.view.pitch,self.view.roll=32,22,0
            self.view.lock_rotation=False;self.view.refresh()
        if self.play_only:Clock.schedule_once(self._settle_play_layout,0)

    def _settle_play_layout(self,*args):
        if self.manager is not None and self.manager.current!=self.name:return
        self._root_layout._adapt();self._root_layout.do_layout()
        self._root_layout.body.do_layout();self.view.refresh()

    def _build_palette(self):
        if self.play_only:return
        super()._build_palette()

    def _hide_input_controls(self):
        for widget in (self.palette,self.palette2,*self._extra_palette_rows,
                       self.navigation,self.hint,self.shape_button):
            widget.disabled=True
            if widget.parent:widget.parent.remove_widget(widget)
        self.view.on_pick=None;self.view.selected=None
        self.shape_button.opacity=0;self.shape_button.height=0
        # Keep one standard reset action; erasing colours is no longer offered.
        row=getattr(self,'_play_actions',None)
        if row is None:
            row=self._play_actions=self.entry_action_buttons['solve'].parent
        if row is not None:
            row.labels['target']=tr('entry.model_reset')
            row.hidden_keys.add('clear');row.reflow()

    def open_palette_settings(self):
        if not self.play_only:return super().open_palette_settings()

    @staticmethod
    def validate_aligned(cube):
        from cube.copter_aligned import observed_colors
        from solver.copter_colours import validate
        validate(observed_colors(cube))

    def _refresh(self):
        if self._cube is None:return
        if self.play_only:
            self._hide_input_controls()
            self.status.text='';self.status.color=_app().theme.text_muted
            self.view.cube=self._cube;self.view.refresh()
            return
        self.status.text=tr('poly.progress',done=sum(c>=0 for c in self._cube.paints),total=len(self._cube.panels))
        self.status.color=_app().theme.text_muted
        self.shape_button.height=m.h(44);self.shape_button.opacity=1;self.shape_button.disabled=False
        self.shape_button.text=tr('copter.shape')
        self.view.cube=self._cube;self.view.refresh()

    def _remember(self):
        self._history.append(self._cube.clone());self._history=self._history[-40:]
        _app().polyhedral_solution=None

    def paint(self,index):
        if self.play_only:return
        if not self.entry_can_edit() or self._cube.paints[index]==self._color:return
        self._remember();self._cube.paint(index,self._color);self.view.selected=index;self._refresh()

    def undo(self):
        if not self.entry_can_edit() or not self._history:return
        self._restore_or_replace(self._history.pop());_app().polyhedral_solution=None;self._refresh()

    def _restore_or_replace(self,work):
        if work.puzzle_kind!=self._cube.puzzle_kind:raise ValueError('rigid.invalid')
        if type(self._cube) is type(work):self._cube.restore(work)
        else:
            # Updating an obsolete geometry is a reversible model replacement,
            # never a copy of incompatible frames into the old material cells.
            self._cube=_app().cube=work.clone()
            self.view.set_cube(self._cube)
        _app().solve_result=None

    def clear(self):
        if self.play_only:return
        if not self.entry_can_edit():return
        box=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        row=ResponsiveBoxLayout(height_px=44,gap_px=8)
        cancel=UIButton(text=tr('poly.cancel'));confirm=DangerButton(text=tr('poly.confirm'))
        row.add_widget(cancel);row.add_widget(confirm);box.add_widget(row)
        popup=self._popup(tr('poly.clear'),box,(.8,.26))
        def commit(*_):
            if self.entry_can_edit():self._remember();self._cube.paints=(-1,)*len(self._cube.panels);self._refresh()
            popup.dismiss()
        confirm.bind(on_release=commit);cancel.bind(on_release=lambda *_:popup.dismiss())

    def entry_reset_solved(self):
        self._remember();self._cube.restore(type(self._cube)());self._refresh()

    def open_twist(self):EntryActionsMixin.open_twist(self)

    def error(self,message,locations=None):
        from services.failures import classify
        locations=locations or ([dict(sticker=i) for i,color in enumerate(self._cube.paints) if color<0]
                               if classify(message)=='incomplete' else [])
        return self.entry_show_error(message,locations=locations)

    @validation_action
    def validate(self):
        if not self.entry_can_edit():return False
        try:
            if any(c<0 for c in self._cube.paints):raise ValueError('Please enter every sticker')
            if hasattr(self._cube,'validate_pose'):self._cube.validate_pose()
            if Counter(self._cube.paints)!=Counter(type(self._cube)().paints):
                raise ValueError('The color counts do not match this puzzle')
            # On a cubical shell, complete local/global colour checks are cheap.
            # A jumbled shape is repaired in the cancellable solving service.
            try:self._cube.aligned_permutation()
            except ValueError as error:
                if str(error)!='copter.align_first':raise
            else:
                self.validate_aligned(self._cube)
        except ValueError as error:self.error(str(error),getattr(error,'locations',None));return False
        return True

    def randomize(self):
        if not self.entry_can_edit():return
        target=self._cube;before=target.clone();job=self.entry_state.begin('scrambling')
        cancel=self._cancel=threading.Event();self.status.text=tr('rigid.shuffling')
        def run():
            work=None;error=None
            try:work=self.make_scrambled(cancel=cancel.is_set)
            except InterruptedError:return
            except Exception as exc:error=exc
            def done(_):
                if self._job is not job:return
                self._job=None
                if cancel.is_set() or self._cube is not target:return
                if error is not None:
                    from services.failures import classify
                    self.entry_show_error(str(error),kind='scramble',category=classify(exception=error),retry=self.randomize);return
                self._history.append(before);self._history=self._history[-40:]
                self._restore_or_replace(work);_app().polyhedral_solution=None;self._refresh()
            Clock.schedule_once(done,0)
        threading.Thread(target=run,daemon=True).start()

    def open_shape_entry(self):
        if self.play_only:return
        if not self.entry_can_edit():return
        self._pose_target=self._cube;self._pose_work=self._cube.clone()
        self._pose_home=(self._cube.panels[self.view.selected][0] if self.view.selected is not None else 0)
        box=ResponsiveBoxLayout(orientation='vertical',gap_px=7)
        self.pose_preview=self.view_class();self.pose_preview.set_cube(self._pose_work)
        self.pose_preview.lock_rotation=False
        self.pose_preview.palette=self.view.palette;self.pose_preview.on_pick=self._pose_pick;box.add_widget(self.pose_preview)
        self.pose_piece=Label(size_hint_y=None,height=30);box.add_widget(self.pose_piece)
        row=ResponsiveBoxLayout(height_px=44,gap_px=5)
        self.pose_mode=Spinner(values=(tr('copter.single'),tr('copter.layer')),text=tr('copter.single'))
        self._pose_axes=getattr(self._cube,'turn_axes',EDGE_AXES)
        self.pose_axis=Spinner(values=('X','Y','Z')+tuple(str(i+1) for i in range(len(self._pose_axes))),text='X')
        row.add_widget(self.pose_mode);row.add_widget(self.pose_axis);box.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=5)
        self.pose_step=Spinner(values=tuple(label for label,angle in self.pose_presets)+(tr('copter.custom'),),text=self.pose_presets[0][0])
        self.pose_angle=TextInput(text='0',multiline=False,input_filter=None,size_hint_x=.55)
        row.add_widget(self.pose_step);row.add_widget(self.pose_angle)
        for icon,direction in (('prev',-1),('next',1)):
            b=UIButton(icon_name=icon);b.bind(on_release=lambda *_,d=direction:self.rotate_pose(d));row.add_widget(b)
        box.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=5)
        cancel=UIButton(icon_name='cancel');ok=PrimaryButton(icon_name='check')
        cancel.bind(on_release=lambda *_:self._pose_popup.dismiss());ok.bind(on_release=lambda *_:self.confirm_pose())
        row.add_widget(cancel);row.add_widget(ok);box.add_widget(row)
        self._pose_popup=self._popup(tr('copter.shape'),box,(.94,.88))
        self._pose_popup.bind(on_dismiss=lambda *_:self._close_pose())
        self._pose_refresh()

    def _pose_pick(self,index):
        self._pose_home=self._pose_work.panels[index][0];self.pose_preview.selected=index;self._pose_refresh()

    def _pose_refresh(self):
        count=sum(home==self._pose_home for home,face,poly in self._cube.panels)
        role=tr('copter.corner' if count==3 else 'copter.carrier' if count==2 else 'copter.leaf')
        self.pose_piece.text=f'{role} · {self._pose_home+1}'
        self.pose_preview.selected_piece=self._pose_home
        self.pose_preview.cube=self._pose_work;self.pose_preview.refresh()

    def rotate_pose(self,direction):
        if self._cube is not self._pose_target:return
        try:
            choice=self.pose_step.values.index(self.pose_step.text)
            amount=self.pose_presets[choice][1] if choice<len(self.pose_presets) else float(self.pose_angle.text)
            if not math.isfinite(amount):raise ValueError('rigid.invalid')
            amount*=direction;axis=self.pose_axis.values.index(self.pose_axis.text)
            if self.pose_mode.text==tr('copter.layer'):
                if axis<3:raise ValueError('copter.edge_axis')
                self._pose_work.apply_move(Move(axis-3,0,amount))
            else:
                normal=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))[axis] if axis<3 else self._pose_axes[axis-3]
                turn=tuple(rotate(column,normal,math.radians(amount)) for column in IDENTITY_FRAME)
                self._pose_work.set_piece_frame(self._pose_home,multiply(turn,self._pose_work.frames[self._pose_home]))
            self._pose_refresh()
        except (ValueError,OverflowError) as exc:
            self.pose_piece.text=tr(str(exc))

    def confirm_pose(self):
        if self._cube is not self._pose_target:return
        if self._cube.signature()!=self._pose_work.signature():
            self._remember();self._cube.restore(self._pose_work);self._refresh()
        self._pose_popup.dismiss()

    def _close_pose(self):
        self.pose_preview.cancel_touch();self.pose_preview.cancel_animation();self._pose_work=None

    def on_leave(self,*args):
        popup=getattr(self,'_pose_popup',None)
        if popup is not None:popup.dismiss()
        super().on_leave(*args)


class CopterTwistScreen(PolyhedralTwistScreen):
    entry_screen_name='CopterInputScreen'
    def on_pre_enter(self,*args):
        super().on_pre_enter(*args)
        self._material_entry_snapshot=self._cube.clone()

    def _set_layers(self):
        self.layer.values=('180°','J = 70.529°','180° − J = 109.471°')
        self.layer.disabled=False;self._layer=0
        if self.layer.text not in self.layer.values:self.layer.text=self.layer.values[0]
        self._layer_selected(self.layer,self.layer.text)

    def _layer_selected(self,widget,text):
        if text in widget.values:
            self._angle=(180.,JUMBLE,180.-JUMBLE)[widget.values.index(text)]
            self.view.turn_amount=self._angle

    def turn(self,direction):self.twist(Move(self._axis,0,self._angle*direction))

    def twist(self,move):
        if self.view._move is not None or self.view.camera_busy:return
        if not self._cube.can_apply(move):
            from ui.entry_feedback import show_feedback
            show_feedback(self.hint,tr('rigid.blocked'));return
        self._axis=move.axis;self.axis.text=self.axis.values[move.axis]
        self._history.append(move);self._future.clear();self._animate(move)

    def back(self):
        if self.view._move is not None or self.view.camera_busy:return
        initial=getattr(self,'_material_entry_snapshot',None)
        if initial is not None and self._cube.signature()!=initial.signature():
            entry=self.manager.get_screen(self.entry_screen_name)
            entry._history.append(initial.clone());entry._history=entry._history[-40:]
        self.view.cancel_touch();self.view.cancel_animation();self.panel.disabled=False
        self.manager.current=self.entry_screen_name
