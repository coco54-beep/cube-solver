"""Direct placement dialog for cuboids and Camouflage."""
import math
from kivy.graphics import Color,Line
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from app.i18n import tr
from cube.cuboid_entry import CuboidEntry
from cube.cuboid import IDENTITY
from cube.polyhedral import CUBE,dot
from renderer.cuboid_view import CuboidView
from ui.widgets.buttons import UIButton,PrimaryButton
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.dialogs import theme_popup
from ui.widgets import metrics as m
from ui.widgets.puzzle_preview import PassivePreview


class _PieceCard(PassivePreview,CuboidView):
    pass


class PlacementView(CuboidView):
    def _draw(self,*args):
        super()._draw(*args)
        self.canvas.after.clear()
        if self.cube is None or not getattr(self,'_proj',None):return
        from itertools import product
        eye,right,up,factor,cx,cy=self._proj
        scale=2.4/(5 if self.cube.puzzle_kind=='camouflage_3' else max(self.cube.dimensions))
        bounds=((-2.,3.),)*3 if self.cube.puzzle_kind=='camouflage_3' else tuple((-d/2,d/2) for d in self.cube.dimensions)
        world=self.observation_world()
        corners={bits:world.transform(*(bounds[a][bits[a]]*scale for a in range(3))) for bits in product((0,1),repeat=3)}
        with self.canvas.after:
            Color(.35,.55,.65,.45)
            for bits,p in corners.items():
                for a in range(3):
                    if bits[a]:continue
                    other=list(bits);other[a]=1;q=corners[tuple(other)]
                    Line(points=[self.x+cx+dot(p,right)*factor,self.y+cy+dot(p,up)*factor,
                                 self.x+cx+dot(q,right)*factor,self.y+cy+dot(q,up)*factor],
                         width=.8,dash_length=4,dash_offset=2)


class CuboidEntryPopup(Popup):
    def __init__(self,cube,theme,on_apply,**kwargs):
        super().__init__(title=tr('cuboid.direct_entry'),size_hint=(.97,.97),**kwargs)
        self.draft=CuboidEntry(cube)
        self.on_apply=on_apply
        self.piece=self.draft.visible[0]
        self.position=self.direction=self.page=0
        self.history=[]
        root=ResponsiveBoxLayout(orientation='vertical',gap_px=5)
        self.hint=Label(text=tr('cuboid.entry_hint'),size_hint_y=None,height=m.h(40),font_size='13sp')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        root.add_widget(self.hint)
        self.view=PlacementView()
        self.view.lock_rotation=False
        self.view.yaw,self.view.pitch=32,22
        root.add_widget(self.view)
        row=ResponsiveBoxLayout(height_px=35,gap_px=5)
        self._button(row,'prev',lambda:self.change_position(-1))
        self.position_label=Label(font_size='13sp',size_hint_x=3);row.add_widget(self.position_label)
        self._button(row,'next',lambda:self.change_position(1))
        root.add_widget(row)
        row=ResponsiveBoxLayout(height_px=35,gap_px=5)
        self._button(row,'undo',lambda:self.change_direction(-1))
        self.direction_label=Label(font_size='13sp',size_hint_x=3);row.add_widget(self.direction_label)
        self._button(row,'redo',lambda:self.change_direction(1))
        self._button(row,'check',self.place,PrimaryButton)
        root.add_widget(row)
        self.gallery=GridLayout(cols=4,size_hint_y=None,height=m.h(128),spacing=m.h(4))
        root.add_widget(self.gallery)
        row=ResponsiveBoxLayout(height_px=32,gap_px=5)
        self._button(row,'prev',lambda:self.change_page(-1))
        self.page_label=Label(font_size='12sp');row.add_widget(self.page_label)
        self._button(row,'next',lambda:self.change_page(1))
        root.add_widget(row)
        row=ResponsiveBoxLayout(height_px=38,gap_px=5)
        self._text_button(row,tr('cuboid.entry_reset'),self.clear)
        self._text_button(row,tr('cuboid.entry_edit'),lambda:self.load(cube))
        self._button(row,'clear',self.remove)
        self._button(row,'undo',self.undo)
        self._button(row,'cancel',self.dismiss)
        root.add_widget(row)
        row=ResponsiveBoxLayout(height_px=42,gap_px=5)
        self.status=Label(font_size='13sp');row.add_widget(self.status)
        self._text_button(row,tr('cuboid.entry_apply'),self.apply,PrimaryButton)
        root.add_widget(row)
        self.content=root
        theme_popup(self,theme)
        self._text_color=theme.text
        for widget in root.walk():
            if type(widget) is Label:widget.color=theme.text
        self.refresh()

    def _button(self,row,icon,callback,cls=UIButton):
        b=cls(icon_name=icon);b.bind(on_release=lambda *_:callback());row.add_widget(b);return b

    def _text_button(self,row,text,callback,cls=UIButton):
        b=cls(text=text);b.bind(on_release=lambda *_:callback());row.add_widget(b);return b

    def _frame(self):return self.draft.options(self.piece)[self.position][self.direction]

    def select(self,piece):
        self.piece=piece;self.position=self.direction=0
        frame=self.draft.placed.get(piece)
        if frame is not None:
            for pos,frames in enumerate(self.draft.options(piece)):
                if frame in frames:self.position,self.direction=pos,frames.index(frame);break
        self.refresh()

    def change_position(self,delta):
        self.position=(self.position+delta)%len(self.draft.options(self.piece));self.direction=0;self.refresh()

    def change_direction(self,delta):
        self.direction=(self.direction+delta)%len(self.draft.options(self.piece)[self.position]);self.refresh()

    def change_page(self,delta):
        pages=(len(self.draft.visible)+7)//8;self.page=(self.page+delta)%pages;self.refresh()

    def refresh(self,message=None):
        self.view.set_cube(self.draft.preview(self.piece,self._frame()))
        self.view.selected=-3
        options=self.draft.options(self.piece)
        self.position_label.text=tr('cuboid.entry_position',index=self.position+1,total=len(options))
        self.direction_label.text=tr('cuboid.entry_direction',index=self.direction+1,total=len(options[self.position]))
        self.status.text=message or tr('cuboid.entry_progress',done=len(self.draft.placed),total=len(self.draft.visible))
        gallery_key=(self.page,self.piece,frozenset(self.draft.placed))
        if gallery_key==getattr(self,'_gallery_key',None):return
        self._gallery_key=gallery_key
        self.gallery.clear_widgets()
        self.page_label.text=f'{self.page+1}/{(len(self.draft.visible)+7)//8}'
        for piece in self.draft.visible[self.page*8:self.page*8+8]:
            button=UIButton(active=piece==self.piece)
            card=_PieceCard(size_hint=(None,None));card.fit_piece=True
            draft=self.draft.preview(piece,IDENTITY);draft.entry_pieces=frozenset((piece,))
            card.set_cube(draft);card.lock_rotation=True
            faces=[CUBE[f] for p,f in self.draft.panel_colors if p==piece]
            normal=tuple(sum(n[a] for n in faces) for a in range(3))
            x,y,z=normal
            # Show the painted exterior, rather than the black internal walls
            # of pieces whose home position is on the rear or bottom.
            if not x and not z:x,z=.35,.6
            card.yaw=math.degrees(math.atan2(x,z))
            card.pitch=math.degrees(math.atan2(y or .3,math.hypot(x,z)))
            button.add_widget(card)
            badge=Label(text=('✓ ' if piece in self.draft.placed else '')+str(piece+1),font_size='11sp',
                        color=self._text_color,size_hint=(None,None))
            button.add_widget(badge)
            def arrange(b,*_):
                label,view=b.children
                view.pos=(b.x+m.h(2),b.y+m.h(2));view.size=(max(2,b.width-m.h(4)),max(2,b.height-m.h(4)))
                label.pos=(b.x,b.y);label.size=(m.h(30),m.h(16))
            button.bind(pos=arrange,size=arrange)
            button.bind(on_release=lambda *_,p=piece:self.select(p))
            self.gallery.add_widget(button)

    def place(self):
        try:
            previous=self.snapshot()
            self.draft.place(self.piece,self._frame())
        except ValueError as exc:self.refresh(tr(str(exc)));return
        self.history.append(previous)
        remaining=[p for p in self.draft.visible if p not in self.draft.placed]
        if remaining:
            self.page=self.draft.visible.index(remaining[0])//8
            self.select(remaining[0])
        else:self.refresh()

    def undo(self):
        if self.history:
            self.draft.placed,self.piece,self.position,self.direction,self.page=self.history.pop()
            self.refresh()

    def snapshot(self):
        return dict(self.draft.placed),self.piece,self.position,self.direction,self.page

    def remove(self):
        if self.piece in self.draft.placed:
            self.history.append(self.snapshot());self.draft.placed.pop(self.piece);self.refresh()

    def clear(self):
        self.history.append(self.snapshot());self.draft.placed={};self.refresh()

    def load(self,cube):
        self.history.append(self.snapshot())
        self.draft.placed={p:cube.frames[p] for p in self.draft.visible};self.select(self.piece)

    def apply(self):
        try:entered=self.draft.to_cube()
        except ValueError as exc:self.refresh(tr(str(exc)));return
        self.on_apply(entered);self.dismiss()
