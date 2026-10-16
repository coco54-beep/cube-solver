"""Silver piece-card entry with centre orientation, shared polyhedral playback."""
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from app.i18n import tr
from cube.mirror_tower import MirrorTowerCube,Piece,placements
from renderer.mirror_tower_view import MirrorTowerView
from ui.screens.polyhedral_screen import PolyhedralScreen,_app
from ui.widgets.buttons import UIButton,DangerButton
from ui.widgets.dialogs import theme_popup
from ui.widgets import metrics as m
from ui.widgets.layouts import ResponsiveBoxLayout


class MirrorTowerScreen(PolyhedralScreen):
    view_class=MirrorTowerView
    customize_icon='reset'

    def __init__(self,**kwargs):
        self._recorded=set()
        self._position=0
        super().__init__(**kwargs)
        self.gallery=GridLayout(cols=3,spacing=m.h(6),size_hint_y=None,height=m.h(145))
        self.panel.add_widget(self.gallery,index=2)

    def on_pre_enter(self,*args):
        fresh=self._cube is not _app().cube
        if fresh:
            self._position=0
        super().on_pre_enter(*args)
        if fresh:
            self._recorded=self.center_preset(set())
            self._set_face_camera(0)
        self._refresh()

    def _build_palette(self):
        for row in (self.palette,self.palette2):
            row.clear_widgets()
            row.height=row._height_px=0
            row.disabled=True
            row.opacity=0
        self._swatches=[]

    def _refresh(self):
        if self._cube is None:
            return
        self.view.recorded=self._recorded
        self.view.selected=self._cube.geometry.pieces[self._position][0]
        if self.view.cube is not self._cube:
            self.view.set_cube(self._cube)
        self.demo_button.disabled=self._cube.n>5
        self.demo_button.opacity=0 if self._cube.n>5 else 1
        self.status.text=tr('poly.progress',done=len(self._recorded),total=14)
        self.hint.text=tr('mirror_tower.hint')
        self.gallery.clear_widgets()
        for home in range(14):
            possible=placements(home,self._position)
            if not possible:
                continue
            piece=self._cube.pieces[self._position]
            active=self._position in self._recorded and piece.home==home
            frame=piece.frame if active else possible[0]
            button=UIButton(active=active)
            preview=MirrorTowerView(size_hint=(None,None))
            preview.fit_piece=True
            preview.set_cube(MirrorTowerCube({self._position:Piece(home,frame)}))
            preview.yaw,preview.pitch=self.view.yaw,self.view.pitch
            preview.roll=self.view.roll
            button.add_widget(preview)
            button.bind(pos=lambda b,*_:setattr(b.children[0],'pos',b.pos),size=lambda b,*_:setattr(b.children[0],'size',b.size))
            button.bind(on_release=lambda *_,h=home,f=frame:self.choose(h,f))
            self.gallery.add_widget(button)
        self.view.refresh()

    def paint(self,index):
        if self._job is None and not self._view_busy:
            self._position=self._cube.geometry.stickers[index].piece
            self._refresh()

    def _remember(self):
        self._history.append((dict(self._cube.pieces),set(self._recorded)))
        self._history=self._history[-40:]
        _app().polyhedral_solution=None

    def choose(self,home,frame):
        if self._job is not None or self._view_busy:
            return
        self._remember()
        self._cube.pieces[self._position]=Piece(home,frame)
        self._recorded.add(self._position)
        self._refresh()

    def customize(self):
        if self._job is not None or self._view_busy or self._position not in self._recorded:
            return
        self._remember()
        piece=self._cube.pieces[self._position]
        options=placements(piece.home,self._position)
        from cube.mirror_tower import frame_key
        index=next(i for i,f in enumerate(options) if frame_key(f)==frame_key(piece.frame))
        self._cube.pieces[self._position]=Piece(piece.home,options[(index+1)%len(options)])
        self._refresh()

    def randomize(self):
        from solver.polyhedral import scramble
        self._remember()
        self._cube.pieces=MirrorTowerCube().pieces
        scramble(self._cube,24)
        self._recorded=set(range(14))
        self._refresh()

    def clear(self):
        if self._job is not None or self._view_busy:
            return
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        label=Label(text=tr('poly.clear'),halign='center',valign='middle')
        label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        actions=ResponsiveBoxLayout(height_px=44,gap_px=8)
        cancel=UIButton(text=tr('poly.cancel'))
        button=DangerButton(text=tr('poly.confirm'))
        actions.add_widget(cancel)
        actions.add_widget(button)
        content.add_widget(label)
        content.add_widget(actions)
        popup=Popup(title=tr('poly.clear'),content=content,size_hint=(.8,.32))
        theme_popup(popup,_app().theme)
        button.bind(on_release=lambda *_:(self._clear_now(),popup.dismiss()))
        cancel.bind(on_release=lambda *_:popup.dismiss())
        popup.open()

    def _clear_now(self):
        self._remember()
        self._recorded=set()
        self._cube.pieces=MirrorTowerCube().pieces
        self._refresh()

    def undo(self):
        if self._history:
            self._cube.pieces,self._recorded=self._history.pop()
            self._refresh()

    def entry_reset_solved(self):
        self._remember()
        self._cube.pieces=MirrorTowerCube().pieces
        self._recorded=set(range(14))

    def entry_commit_state(self):
        _app().cube=self._cube
        self._refresh()

    def entry_center_preset(self):
        # 和粽子/镜子一致：预置 4 个单贴纸中心块，方便对位。
        pieces=self._cube.geometry.pieces
        return {i for i in range(len(pieces)) if len(pieces[i])==1}

    def validate(self):
        if len(self._recorded)!=14:
            self.error('Please enter every sticker')
            return False
        try:
            self._cube.labeled_state()
        except (ValueError,KeyError):
            self.error('Duplicate piece')
            return False
        self.status.text=tr('poly.valid')
        return True

    def solve(self):
        if self.validate():
            super().solve()

    def retranslate(self):
        super().retranslate()
        self.hint.text=tr('mirror_tower.hint')

    def _face_roll(self,index):
        return 180 if self._cube.geometry.spec.normals[index][1]>0 else 0
