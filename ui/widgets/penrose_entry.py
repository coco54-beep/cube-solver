"""Whole Penrose piece cards inside the animated 3D face entry page."""
from functools import lru_cache

from kivy.app import App
from kivy.graphics import Color, Line, Mesh
from kivy.graphics.texture import Texture
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from app.i18n import tr, current_language
from cube.coordinates import FACE_NORMALS, rc_from_pos
from cube.penrose_entry import piece_choices, piece_groups, rotated_choice, place_piece, solved, VISIBLE
from cube.polyhedral import cross, dot, unit
from renderer.entry_style import SEAM, stroke
from renderer.variant_scene import build_variant_scene
from ui.widgets import metrics as m
from ui.widgets.buttons import UIButton
from ui.widgets.entry_controls import EntryGalleryPager, GALLERY_COLUMNS, GALLERY_PAGE_SIZE
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.puzzle_preview import PassivePreview


@lru_cache(maxsize=512)
def _edge_mesh(n, pos, choice):
    cube = solved(n)
    cube.cubies = {pos: choice.piece(pos)}
    vertices, _, infos = build_variant_scene(cube)
    return tuple((tuple(tuple(vertices[offset+i*7:offset+i*7+3]) for i in range(4)),
                  tuple(vertices[offset+3:offset+7]), info[2])
                 for offset, info in zip(range(0, len(vertices), 28), infos))


class PenroseEdgePreview(PassivePreview, Widget):
    _texture = None

    def __init__(self, n, pos, choice, face, world, **kwargs):
        super().__init__(**kwargs)
        self.geometry = _edge_mesh(n, pos, choice)
        normals = [world.transform(*normal) for normal, _ in choice.stickers]
        primary = world.transform(*FACE_NORMALS[face])
        others=[normal for normal in normals if dot(normal,primary)<.5]
        if not others:
            others=[world.transform(*next(n for n in FACE_NORMALS.values()
                                          if abs(dot(n,FACE_NORMALS[face]))<.5))]
        other=tuple(sum(n[i] for n in others) for i in range(3))
        tangent=cross(primary,other) if len(normals)<3 else (0.,0.,0.)
        self._eye=unit(tuple(a+.8*b+.35*c for a,b,c in zip(primary,other,tangent)))
        right=cross((0.,1.,0.),self._eye)
        if dot(right,right)<1e-10:right=cross((1.,0.,0.),self._eye)
        self._right=unit(right)
        self._up = cross(self._eye,self._right)
        self.world = world
        self.bind(size=self.redraw, pos=self.redraw)

    @classmethod
    def white_texture(cls):
        if cls._texture is None:
            cls._texture = Texture.create(size=(1,1), colorfmt='rgba')
            def restore(texture):
                texture.blit_buffer(bytes((255,255,255,255)), colorfmt='rgba', bufferfmt='ubyte')
            restore(cls._texture)
            cls._texture.add_reload_observer(restore)
        return cls._texture

    def redraw(self,*_):
        faces = []
        for points, rgba, edges in self.geometry:
            points = tuple(self.world.transform(*p) for p in points)
            a,b,c = points[:3]
            normal = cross(tuple(y-x for x,y in zip(a,b)),tuple(y-x for x,y in zip(a,c)))
            if dot(normal,self._eye) <= 1e-10:continue
            projected = tuple((dot(p,self._right),dot(p,self._up)) for p in points)
            faces.append((sum(dot(p,self._eye) for p in points)/4,projected,rgba,edges))
        self.canvas.clear()
        if not faces:return
        xs = [x for _,points,_,_ in faces for x,y in points]
        ys = [y for _,points,_,_ in faces for x,y in points]
        cx,cy = (min(xs)+max(xs))/2,(min(ys)+max(ys))/2
        factor = max(0.,min((self.width-10)/max(max(xs)-min(xs),.01),
                            (self.height-10)/max(max(ys)-min(ys),.01)))
        with self.canvas:
            for _,points,rgba,edges in sorted(faces,key=lambda item:item[0]):
                pixels = tuple((self.center_x+(x-cx)*factor,self.center_y+(y-cy)*factor) for x,y in points)
                Color(*rgba)
                Mesh(vertices=[v for x,y in pixels for v in (x,y,0.,0.)],
                     indices=[0,1,2,0,2,3],mode='triangles',texture=self.white_texture())
                Color(*SEAM)
                for edge in edges:
                    Line(points=(*pixels[edge],*pixels[(edge+1)%4]),width=stroke())


class PenrosePieceInput(ResponsiveBoxLayout):
    def __init__(self,screen,host,**kwargs):
        super().__init__(orientation='vertical',height_px=0,gap_px=6,**kwargs)
        self.screen=screen;self.host=host;self.position=None;self.page=0;self.stamp=None;self.choices=()
        self.caption=Label(size_hint_y=None,height=m.h(26),font_size='12sp',halign='center',valign='middle')
        self.caption.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        self.gallery=GridLayout(cols=GALLERY_COLUMNS,size_hint_y=None,height=0,spacing=m.h(6))
        self.pager=EntryGalleryPager(self.change_page)
        self.rotate=UIButton(icon_name='reset',size_hint_y=None,height=m.h(40))
        self.rotate.bind(on_release=lambda *_:self.flip())
        for widget in (self.caption,self.gallery,self.pager,self.rotate):self.add_widget(widget)
        self.opacity=0;self.disabled=True

    def select(self,pos):
        if not self.screen._penrose() or not self.screen.entry_can_edit():return False
        choices=piece_choices(self.screen._n(),pos)
        if not choices:
            self.clear()
            return False
        if pos!=self.position:self.page=0
        self.position=pos;self.refresh();self.screen._refresh_view()
        return True

    def clear(self):
        self.position=None;self.page=0;self.stamp=None;self._generation=object()
        self.refresh()

    def pattern(self):
        if self.position is None:return ()
        return tuple((normal,self.screen._data[face][row][column])
                     for normal,_ in self.choices[0].stickers
                     for face in (next(f for f,n in FACE_NORMALS.items() if n==normal),)
                     for row,column in (rc_from_pos(self.screen._n(),face,self.position),))

    def refresh(self):
        screen=self.screen
        visible=screen._penrose() and self.position is not None
        face=screen._ori.current_face() if screen._ori is not None else 'F'
        if visible:
            self.choices=piece_choices(screen._n(),self.position)
            visible=bool(self.choices) and FACE_NORMALS[face] in dict(self.choices[0].stickers)
        if not visible:
            self.position=None;self._height_px=0;self.opacity=0;self.disabled=True
            if self.parent is not None:self.parent.remove_widget(self)
            self.gallery.clear_widgets();self.stamp=None;self._sync_metrics();return
        if self.parent is None:self.host.add_widget(self,index=self.host.children.index(screen.msg)+1)
        self.opacity=1;self.disabled=False
        pattern=self.pattern()
        self.caption.height=m.h(26)
        role={1:'centre',2:'edge',3:'corner'}[len(self.choices[0].stickers)]
        self.caption.text=tr('penrose.piece_choose',piece=tr('penrose.'+role))
        self.caption.color=App.get_running_app().theme.text
        groups=piece_groups(screen._n(),self.position)
        cards=tuple(next((c for c in group if tuple((n,VISIBLE[col]) for n,col in c.stickers)==pattern),group[0])
                    for group in groups)
        count=max(1,(len(cards)+GALLERY_PAGE_SIZE-1)//GALLERY_PAGE_SIZE)
        self.page=max(0,min(self.page,count-1));self.pager.set_page(self.page,count)
        choices=cards[self.page*GALLERY_PAGE_SIZE:(self.page+1)*GALLERY_PAGE_SIZE]
        rows=(len(choices)+GALLERY_COLUMNS-1)//GALLERY_COLUMNS
        self.gallery.height=m.h(rows*66+max(0,rows-1)*6)
        self._height_px=26+rows*66+max(0,rows-1)*6+(30 if count>1 else 0)+40+18
        self._sync_metrics()
        self.rotate.disabled=not self.flipped_choice() or len(self.choices[0].stickers)<2
        self.rotate.height=m.h(40)
        stamp=(screen._n(),self.position,face,screen._ori.index,pattern,self.page,current_language())
        if stamp==self.stamp:return
        self.stamp=stamp
        self._generation=generation=object()
        self.gallery.clear_widgets()
        for choice in choices:
            active=tuple((n,VISIBLE[c]) for n,c in choice.stickers)==pattern
            button=UIButton(active=active)
            button.penrose_choice=choice
            preview=PenroseEdgePreview(screen._n(),self.position,choice,face,screen._ori.world)
            button.add_widget(preview)
            button.bind(pos=lambda b,*_:setattr(b.children[0],'pos',b.pos),
                        size=lambda b,*_:setattr(b.children[0],'size',b.size))
            button.bind(on_release=lambda *_,p=self.position,c=choice,g=generation:self.choose(p,c,g))
            self.gallery.add_widget(button)

    def change_page(self,delta):
        if self.screen.entry_can_edit():self.page+=delta;self.refresh()

    def choose(self,pos,choice,generation=None):
        screen=self.screen
        if not screen.entry_can_edit() or pos!=self.position:return
        if generation is not None and generation is not self._generation:return
        before=screen.collect_facelets();data=place_piece(before,screen._n(),pos,choice)
        if data==before:return
        screen.set_facelets(data,remember=True)

    def flipped_choice(self):
        pattern=self.pattern()
        current=next((c for c in self.choices if tuple((n,VISIBLE[col]) for n,col in c.stickers)==pattern),None)
        if current is None:return None
        result=rotated_choice(self.screen._n(),self.position,current)
        return result if result!=current else None

    def flip(self):
        choice=self.flipped_choice()
        if choice:self.choose(self.position,choice)


# Retain the old attribute/class name for saved screens and older callers.
PenroseEdgeInput=PenrosePieceInput
