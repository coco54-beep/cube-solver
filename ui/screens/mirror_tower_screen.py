"""Silver piece-card entry with centre orientation, shared polyhedral playback."""
from ui.entry_feedback import validation_action
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
from ui.widgets.entry_controls import EntryGalleryPager,GALLERY_COLUMNS,GALLERY_PAGE_SIZE


class MirrorTowerScreen(PolyhedralScreen):
    view_class=MirrorTowerView
    cube_class=MirrorTowerCube
    hint_key='mirror_tower.hint'
    customize_icon='reset'
    supports_palette_settings=False

    def _new_cube(self, pieces=None):
        if self.cube_class is MirrorTowerCube:
            return self.cube_class(pieces)
        return self.cube_class(pieces, n=_app().n)

    def _placements(self, home, position):
        return placements(home, position)

    def _gallery_homes(self):
        return range(len(self._cube.geometry.pieces))

    def _card_camera(self,preview):
        preview.yaw,preview.pitch=self.view.yaw,self.view.pitch
        preview.roll=self.view.roll

    def __init__(self,**kwargs):
        self._recorded=set()
        self._position=0
        self._gallery_page=0
        super().__init__(**kwargs)
        self.gallery=GridLayout(cols=GALLERY_COLUMNS,spacing=m.h(6),size_hint_y=None)
        self.gallery_pages=EntryGalleryPager(self._change_gallery_page)
        self.panel.add_widget(self.gallery,index=self.panel.children.index(self.navigation)+1)
        self.panel.add_widget(self.gallery_pages,index=self.panel.children.index(self.navigation)+1)
        self.rotate=self.customize_button
        if self.supports_palette_settings:
            self.palette_button=UIButton(icon_name='gear')
            self.palette_button.bind(on_release=lambda *_:self.open_palette_settings())
            self.navigation.add_widget(self.palette_button,index=2)

    def _change_gallery_page(self,direction):
        if not self.entry_can_edit():return
        self._gallery_page+=direction
        self._refresh()

    def on_pre_enter(self,*args):
        fresh=self._cube is not _app().cube
        if fresh:
            self._position=0
            self._gallery_page=0
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
        self.demo_button.disabled=False
        self.demo_button.opacity=1
        self.status.text=tr('poly.progress',done=len(self._recorded),total=len(self._cube.geometry.pieces))
        self.hint.text=tr(self.hint_key)
        token=self.entry_gallery_generation()
        self.gallery.clear_widgets()
        choices=[(home,possible) for home in self._gallery_homes()
                 if (possible:=self._placements(home,self._position))]
        pages=max(1,(len(choices)+GALLERY_PAGE_SIZE-1)//GALLERY_PAGE_SIZE)
        self._gallery_page=self.gallery_pages.set_page(self._gallery_page,pages)
        choices=choices[self._gallery_page*GALLERY_PAGE_SIZE:(self._gallery_page+1)*GALLERY_PAGE_SIZE]
        rows=max(1,(len(choices)+GALLERY_COLUMNS-1)//GALLERY_COLUMNS)
        self.gallery.height=m.h(rows*66+(rows-1)*6)
        self.rotate.disabled=(self._position not in self._recorded or
                              len(self._placements(self._cube.pieces[self._position].home,self._position))<2)
        for home,possible in choices:
            piece=self._cube.pieces[self._position]
            active=self._position in self._recorded and piece.home==home
            frame=piece.frame if active else possible[0]
            button=UIButton(active=active)
            preview=self.view_class(size_hint=(None,None))
            preview.fit_piece=True
            preview.set_cube(self._new_cube({self._position:Piece(home,frame)}))
            preview.palette=tuple(self.view.palette)
            self._card_camera(preview)
            # Gallery previews are static: never let them intercept the card tap.
            preview.on_touch_down = preview.on_touch_move = preview.on_touch_up = lambda *_: False
            button.add_widget(preview)
            button.bind(pos=lambda b,*_:setattr(b.children[0],'pos',(b.x+b.width*.05,b.y+b.height*.05)),
                        size=lambda b,*_:setattr(b.children[0],'size',(b.width*.9,b.height*.9)))
            button.bind(on_release=lambda *_,h=home,f=frame,t=token:
                        self.entry_gallery_action(t,self.choose,h,f))
            self.gallery.add_widget(button)
        self.view.refresh()

    def paint(self,index):
        if self.entry_can_edit():
            if self._position!=self._cube.geometry.stickers[index].piece:self._gallery_page=0
            self._position=self._cube.geometry.stickers[index].piece
            self._refresh()

    def _remember(self):
        self._history.append((dict(self._cube.pieces),set(self._recorded)))
        self._history=self._history[-40:]
        _app().polyhedral_solution=None

    def choose(self,home,frame):
        if not self.entry_can_edit():
            return
        self._remember()
        self._cube.pieces[self._position]=Piece(home,frame)
        self._recorded.add(self._position)
        self._refresh()

    def customize(self):
        if not self.entry_can_edit() or self._position not in self._recorded:
            return
        self._remember()
        piece=self._cube.pieces[self._position]
        options=self._placements(piece.home,self._position)
        from cube.mirror_tower import frame_key
        index=next(i for i,f in enumerate(options) if frame_key(f)==frame_key(piece.frame))
        self._cube.pieces[self._position]=Piece(piece.home,options[(index+1)%len(options)])
        self._refresh()

    def randomize(self):
        if not self.entry_can_edit():
            return
        from cube.polyhedral_scramble import scramble
        work=self._new_cube()
        scramble(work,24)
        self._remember()
        self._cube.pieces=work.pieces
        self._recorded=set(range(len(self._cube.geometry.pieces)))
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
        if not self.entry_can_edit():
            return
        self._remember()
        self._recorded=set()
        self._cube.pieces=self._new_cube().pieces
        self._refresh()

    def undo(self):
        if not self.entry_can_edit():
            return
        if self._history:
            self._cube.pieces,self._recorded=self._history.pop()
            _app().polyhedral_solution=None
            self._refresh()

    def entry_reset_solved(self):
        self._remember()
        self._cube.pieces=self._new_cube().pieces
        self._recorded=set(range(len(self._cube.geometry.pieces)))

    def entry_commit_state(self):
        _app().cube=self._cube
        self._refresh()

    def entry_center_preset(self):
        # 和粽子/镜子一致：预置 4 个单贴纸中心块，方便对位。
        pieces=self._cube.geometry.pieces
        return {i for i in range(len(pieces)) if len(pieces[i])==1}

    @validation_action
    def validate(self):
        if not self.entry_can_edit():
            return False
        if len(self._recorded)!=len(self._cube.geometry.pieces):
            self.error('Please enter every sticker')
            return False
        try:
            self._cube.labeled_state()
        except (ValueError,KeyError):
            self.error('Duplicate piece')
            return False
        self.status.text=tr('poly.valid')
        return True

    def retranslate(self):
        super().retranslate()
        self.hint.text=tr(self.hint_key)

    def _face_roll(self,index):
        return 180 if self._cube.geometry.spec.normals[index][1]>0 else 0
