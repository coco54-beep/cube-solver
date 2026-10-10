"""Shape-card input for mirror cubes; no fictitious colored facelets."""
from kivy.uix.label import Label

from app.i18n import tr
from cube.mirror import MirrorCube
from cube.mastermorphix import make_piece,placements,position_kind,position_name
from renderer.mirror_view import MirrorView
from renderer.cube_orientation import CubeOrientation
from ui.screens.mastermorphix_screen import MastermorphixScreen,_thumbnail_camera_for,_app
from ui.widgets.buttons import UIButton
from ui.widgets import metrics as m


class MirrorScreen(MastermorphixScreen):
    def go_back(self):
        self.manager.current='IrregularDirectoryScreen'

    def build_ui(self):
        super().build_ui()
        old=self.view
        self.view=MirrorView()
        self.view.camera.azimuth=0.0
        self.view.camera.elevation=0.0
        self.view.lock_rotation=True
        self.view.on_pick_piece=self.select_position
        index=self.main.children.index(old)
        self.main.remove_widget(old)
        self.main.add_widget(self.view,index=index)
        self.palette_row.height=0
        self.palette_row._height_px=0
        self.palette_row.opacity=0
        self.palette_row.disabled=True

    def on_pre_enter(self,*args):
        if self._cube is None or self._cube.n!=_app().n:
            self._blank(None)
        self.reset_interaction()
        self._refresh()

    def _blank(self,palette):
        self._cube=MirrorCube.solved(n=_app().n)
        self._ori=CubeOrientation(self._cube.n)
        self._recorded=set()
        self._history=[]
        self._preview=None
        self._pos=self._cube.positions[0]
        self._group=position_kind(self._pos)

    def _refresh(self):
        if self._cube is None:
            return
        self.demo_button.disabled=self._cube.n>5
        self.demo_button.opacity=1 if self._cube.n<=5 else 0
        self._cancel_view_turn()
        self.title.text=f'{tr("directory.mirror")} · {tr("directory.order",order=self._cube.n)}'
        self.reference_label.text=tr('mirror.input_hint')
        self.view.selected_pos=self._pos
        self.view.recorded=self._recorded
        self.view.set_cube(self._cube)
        self.view.set_whole_world(self._ori.world)
        self.slot.text=position_name(self._pos)
        self.hint.text=tr('mirror.card_hint')
        self.progress.text=tr('morphix.progress',done=len(self._recorded),total=len(self._all_positions()))
        self.rotate.disabled=self._pos not in self._recorded
        self._build_gallery()
        self._resize()

    def _build_gallery(self):
        self.gallery.clear_widgets()
        homes=[p for p in self._cube.positions if placements(p,self._pos)]
        page_size=8
        pages=max(1,(len(homes)+page_size-1)//page_size)
        self._gallery_page=max(0,min(self._gallery_page,pages-1))
        self.gallery_pages.height=m.h(30) if pages>1 else 0
        self.gallery_pages.opacity=1 if pages>1 else 0
        self.gallery_pages.disabled=pages<=1
        self.gallery_page_label.text=f'{self._gallery_page+1}/{pages}'
        self.gallery_page_prev.disabled=self._gallery_page==0
        self.gallery_page_next.disabled=self._gallery_page==pages-1
        for home in homes[self._gallery_page*page_size:(self._gallery_page+1)*page_size]:
            frame=placements(home,self._pos)[0]
            current=self._cube.cubies[self._pos]
            active=self._pos in self._recorded and current.home==home
            if active:
                frame=current.frame
            button=UIButton(active=active)
            view=MirrorView(size_hint=(None,None))
            view.lock_rotation=True
            view.fit_piece=True
            view.set_cube(MirrorCube({self._pos:make_piece(home,self._pos,frame,self._cube.n)},n=self._cube.n))
            _thumbnail_camera_for(view,self._pos)
            button.add_widget(view)
            button.bind(pos=lambda b,*_:setattr(b.children[0],'pos',(b.x+b.width*.05,b.y+b.height*.05)),
                        size=lambda b,*_:setattr(b.children[0],'size',(b.width*.9,b.height*.9)))
            button.bind(on_release=lambda *_,h=home,f=frame:self.choose_piece(h,f))
            self.gallery.add_widget(button)

    def choose_piece(self,home,frame=None):
        self._remember()
        self._cube.cubies[self._pos]=make_piece(home,self._pos,frame or placements(home,self._pos)[0],self._cube.n)
        self._recorded.add(self._pos)
        self._refresh()

    def random_load(self):
        from cube.scramble import random_scramble
        self._remember()
        self._cube=MirrorCube.solved(n=self._cube.n)
        self._cube.apply_moves(random_scramble(self._cube.n))
        self._recorded=set(self._all_positions())
        self._refresh()

    def check(self):
        if len(self._recorded)!=len(self._all_positions()):
            self.hint.text=tr('morphix.error.incomplete',total=len(self._all_positions()))
            return None
        corners=[p.home for p in self._cube.cubies.values() if len(p.stickers)==3]
        if len(set(corners))!=8:
            self.hint.text=tr('mirror.duplicate')
            return None
        self.hint.text=tr('poly.valid')
        return self._cube.clone()

    def start_solve(self):
        cube=self.check()
        if cube is not None:
            _app().cube=cube
            _app().puzzle_kind='mirror'
            _app().solve_result=None
            self.manager.current='SolvingScreen'
