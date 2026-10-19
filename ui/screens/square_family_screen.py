"""SQ family piece-card entry and legal turns, sharing the SQ-1 player."""
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner

from app.i18n import tr
from cube.square_family import SquareFamilyCube
from cube.square_family_entry import SquareFamilyEntry,SquareFamilyBlock
from renderer.square_family_view import SquareFamilyView
from renderer.camera_follow import follow_turn
from ui.screens.square1_screen import Square1Screen,_app
from ui.widgets.square1_entry import Square1Ring
from ui.widgets.camera_follow import follow_panel
from ui.widgets.buttons import UIButton,PrimaryButton,DangerButton
from ui.widgets.layouts import AdaptiveSceneLayout,ResponsiveBoxLayout
from ui.widgets import metrics as m


class SquareFamilyScreen(Square1Screen):
    view_class = SquareFamilyView
    demo_mode = False

    def __init__(self,**kwargs):
        self._gallery_page = 0
        super().__init__(**kwargs)

    def _layer_names(self):
        keys = ('top','inner_top','inner_bottom','bottom') if self._cube.layer_count == 4 else ('top','bottom')
        return tuple(tr('sq.layer_'+key) for key in keys)

    def _build(self):
        if self._playback:
            super()._build()
            self.title.text = tr('directory.'+self._cube.puzzle_kind)
            return
        if hasattr(self,'view'):
            self._cancel_step()
        self.clear_widgets()
        root = AdaptiveSceneLayout()
        top = ResponsiveBoxLayout(height_px=44,gap_px=8)
        self._button(top,'back',self.back)
        self.title = Label(text=tr('directory.sq_family'),size_hint_x=4,font_size='20sp')
        top.add_widget(self.title)
        self._button(top,'reset',self.reset_view)
        root.add_widget(top)
        self.view = self.view_class()
        self.view.lock_rotation = True
        self.view.on_pick = self.select_surface
        self.view.on_twist = self._turn_input
        self._simple = bool(getattr(_app(),'simple_input',False))
        panel = ResponsiveBoxLayout(orientation='vertical',gap_px=6,size_hint_y=None)
        self.status = Label(size_hint_y=None,height=m.h(42),font_size='13sp',halign='center',valign='middle')
        self.status.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        panel.add_widget(self.status)
        row = ResponsiveBoxLayout(height_px=40,gap_px=6)
        self.layer_selector = Spinner(text='U',values=('U','D'))
        self.layer_selector.bind(text=self._change_layer)
        row.add_widget(self.layer_selector)
        self._button(row,'undo',lambda:self.turn_ring(-1))
        self._button(row,'redo',lambda:self.turn_ring(1))
        self.slash_button = UIButton(text='/ 180°')
        self.slash_button.bind(on_release=lambda *_:self.slash())
        row.add_widget(self.slash_button)
        panel.add_widget(row)
        self.ring = Square1Ring(0,self.select_slot,size_hint_y=None,height=m.h(135))
        panel.add_widget(self.ring)
        self.gallery = GridLayout(cols=4,size_hint_y=None,height=m.h(140),spacing=m.h(5))
        panel.add_widget(self.gallery)
        pages = ResponsiveBoxLayout(height_px=32,gap_px=7)
        self._button(pages,'prev',lambda:self.change_gallery(-1))
        self.page_label = Label(font_size='13sp')
        pages.add_widget(self.page_label)
        self._button(pages,'next',lambda:self.change_gallery(1))
        panel.add_widget(pages)
        row = ResponsiveBoxLayout(height_px=36,gap_px=7)
        self.middle_buttons = []
        for value in (0,1):
            button = UIButton(text=tr('sq.centre_'+str(value)))
            button.bind(on_release=lambda *_,v=value:self.set_middle(v))
            self.middle_buttons.append(button)
            row.add_widget(button)
        panel.add_widget(row)
        row = ResponsiveBoxLayout(height_px=48,gap_px=6)
        for icon,callback,cls in (('random',self.randomize,UIButton),('clear',self.clear,DangerButton),
                                  ('undo',self.undo,UIButton),('target',self.assign_initial,UIButton),
                                  ('solve',self.solve,PrimaryButton)):
            self._button(row,icon,callback,cls)
        panel.add_widget(row)
        row = ResponsiveBoxLayout(height_px=40,gap_px=6)
        self._button(row,'prev',lambda:self.view.turn_view(-1))
        self._button(row,'next',lambda:self.view.turn_view(1))
        panel.add_widget(row)
        self.panel = panel
        panel,self.follow_control = follow_panel(panel,self.view)
        root.set_content(self.view,panel)
        self.add_widget(root)

    def on_pre_enter(self,*args):
        if self._cube is not _app().cube:
            self._cube = _app().cube
            self._entry = SquareFamilyEntry(self._cube)
            self._history = []
            self._slot = self._field = self._gallery_page = 0
            self._playback = False
            self._build()
        elif self._simple != bool(getattr(_app(),'simple_input',False)):
            self._build()
        self._refresh()

    def _refresh(self,message=None):
        if self._cube is None:
            return
        if self._playback and not hasattr(self, "track"):
            return
        if self._playback:
            return super()._refresh(message)
        self.title.text = tr('directory.'+self._cube.puzzle_kind)
        if self.view.cube is not self._entry:
            self.view.set_cube(self._entry)
        self.view.selected = (self._slot,0)
        self.status.text = message if message is not None else tr('sq.input',done=self._entry.complete_count(),total=len(self._cube.specs))
        self.status.color = _app().theme.text
        self.title.color = _app().theme.text
        names = self._layer_names()
        self.layer_selector.values = names
        self.layer_selector.text = names[self._slot//12]
        self.slash_button.disabled = not self._entry.can_slice()
        self.ring.layer = self._slot//12
        self.ring.refresh(self._entry,(self._slot,0))
        for value,button in enumerate(self.middle_buttons):
            button.active = value == self._entry.middle
        self._build_gallery()
        self.view.refresh()

    def _change_layer(self,widget,value):
        if self._cube is None or not self.entry_can_edit():
            return
        names = self._layer_names()
        if value in names and names.index(value) != self._slot//12:
            self.select_slot(names.index(value)*12)

    def select_slot(self,slot,field=0):
        if self._playback or not self.entry_can_edit() or not 0 <= slot < len(self._entry.slots):
            return
        if self._cube.puzzle_kind == 'square0':
            slot = slot//12*12+slot%12//3*3
        self._slot = self._entry.block_start(slot)
        self._field = self._gallery_page = 0
        self._refresh()

    def _homes(self):
        current = self._entry.blocks.get(self._entry.slots[self._slot])
        used = {block.home for identity,block in self._entry.blocks.items()
                if block.confirmed and identity != self._entry.slots[self._slot]}
        pair = int(self._slot//12 in (1,2))
        candidates = [home for home,spec in enumerate(self._cube.specs)
                      if self._cube.layer_count != 4 or spec.pair == pair]
        # Identical inner edges share one card, with an unused internal label.
        grouped = {}
        for home in candidates:
            spec = self._cube.specs[home]
            if (spec not in grouped or (grouped[spec] in used and home not in used) or
                    (current is not None and current.confirmed and current.home == home)):
                grouped[spec] = home
        return list(grouped.values())

    def _build_gallery(self):
        self.gallery.clear_widgets()
        homes = self._homes()
        pages = max(1,(len(homes)+7)//8)
        self._gallery_page = max(0,min(self._gallery_page,pages-1))
        self.page_label.text = f'{self._gallery_page+1}/{pages}'
        current = self._entry.blocks.get(self._entry.slots[self._slot])
        for home in homes[self._gallery_page*8:self._gallery_page*8+8]:
            button = UIButton(active=current is not None and current.confirmed and
                              self._cube.specs[current.home] == self._cube.specs[home])
            preview = self._entry.clone()
            preview.slots = [-1]*len(preview.slots)
            preview.blocks = {0:SquareFamilyBlock(home,True)}
            for i in range(self._cube.specs[home].width):
                preview.slots[self._slot//12*12+(self._slot%12+i)%12] = 0
            view = self.view_class(size_hint=(None,None))
            view.fit_piece = True
            view.show_middle = False
            view.lock_rotation = True
            view.yaw = 32.
            view.pitch = 35.*self._entry.layer_direction(self._slot//12)
            view.set_cube(preview)
            button.add_widget(view)
            button.bind(pos=lambda b,*_:setattr(b.children[0],'pos',(b.x+m.h(2),b.y+m.h(2))),
                        size=lambda b,*_:setattr(b.children[0],'size',(max(2,b.width-m.h(4)),max(2,b.height-m.h(4)))))
            button.bind(on_release=lambda *_,h=home:self.choose_piece(h))
            self.gallery.add_widget(button)

    def change_gallery(self,direction):
        if self.entry_can_edit():
            self._gallery_page += direction
            self._build_gallery()

    def choose_piece(self,home):
        if not self.entry_can_edit():
            return
        self._remember()
        self._slot = self._entry.choose_piece(self._slot,home)
        self._refresh()

    def randomize(self):
        if not self.entry_can_edit():
            return
        self._remember()
        cube = SquareFamilyCube(self._cube.puzzle_kind)
        cube.scramble()
        self._entry = SquareFamilyEntry(cube,colored=True)
        self._slot = self._entry.block_start(0)
        self._gallery_page = 0
        self._refresh()

    def _clear_now(self):
        if not self.entry_can_edit():
            return
        self._remember()
        self._entry = SquareFamilyEntry(SquareFamilyCube(self._cube.puzzle_kind))
        self._slot = self._field = self._gallery_page = 0
        self._refresh()

    def entry_reset_solved(self):
        self._remember()
        self._entry = SquareFamilyEntry(SquareFamilyCube(self._cube.puzzle_kind),colored=True)
        self._slot = self._field = self._gallery_page = 0
        self._cube.slots,self._cube.middle = self._entry.to_cube().slots,0

    def entry_can_assign(self):
        return self.entry_can_edit()

    def validate(self):
        if not self.entry_can_edit():
            return False
        try:
            entered = self._entry.to_cube()
            self._cube.slots,self._cube.middle = entered.slots,entered.middle
            self._refresh(tr('poly.valid'))
            return True
        except ValueError as exc:
            self._refresh(tr(str(exc)))
            return False

    def turn_ring(self,direction):
        if self.entry_can_edit():
            step = 3 if self._cube.puzzle_kind == 'square0' else 1
            self._turn_input(self._cube.move(self._slot//12,direction*step))

    def slash(self):
        if self.entry_can_edit() and self._entry.can_slice():
            self._turn_input(self._cube.move(self._cube.layer_count))

    def _turn_input(self,move):
        if not self.entry_can_edit():
            return
        self._remember()
        def done():
            self._slot = self._entry.block_start(self._slot)
            self._refresh()
        self._animate_followed(move,done)

    def _animate_followed(self,move,done):
        self._pending_move = move
        layers = self._cube.layer_count
        target = ((0.,1. if move.axis < layers/2 else -1.,0.) if move.axis < layers else (-.966,0.,-.259))
        def begin():
            if self._pending_move is not move:
                return
            self._pending_move = None
            if not self.view.animate_move(move,done,.32/self._speed):
                self._refresh(tr('square1.error.blocked'))
        follow_turn(self.view,target,begin)

    def set_middle(self,value):
        if self.entry_can_edit():
            super().set_middle(value)

    def undo(self):
        if self.entry_can_edit():
            super().undo()

    def clear(self):
        if self.entry_can_edit():
            super().clear()

    def back(self):
        if self._playback:
            self.confirm_back()
        else:
            self.reset_interaction()
            self.manager.current = 'HomeScreen'
