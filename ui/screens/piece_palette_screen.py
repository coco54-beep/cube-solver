"""Independent palette editor: all changes stay local until Save."""
from kivy.core.window import Window
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app.i18n import tr
from ui.widgets.buttons import UIButton,PrimaryButton
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets import metrics as m
from ui.widgets.mastermorphix_net import MastermorphixNet
from ui.widgets.palette_net import CubePaletteNet


class PiecePaletteScreen(Screen):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._source=None;self._draft=[];self._defaults=[];self._index=0;self._updating=False
        root=ResponsiveBoxLayout(orientation='vertical',gap_px=8,padding_px=[16,8,16,10])
        top=ResponsiveBoxLayout(height_px=44,gap_px=8)
        back=UIButton(icon_name='back',size_hint_x=None,width=m.h(54))
        back.bind(on_release=lambda *_:self.back())
        self.title=Label(font_size='20sp');top.add_widget(back);top.add_widget(self.title)
        root.add_widget(top)
        self.body=ResponsiveBoxLayout(gap_px=12)
        self.reference_box=ResponsiveBoxLayout(orientation='vertical',gap_px=5)
        self.puzzle_label=Label(size_hint_y=None,height=m.h(28),font_size='15sp',halign='center')
        self.reference_box.add_widget(self.puzzle_label)
        self.reference_holder=ResponsiveBoxLayout()
        self.reference_box.add_widget(self.reference_holder)
        self.hint=Label(size_hint_y=None,height=m.h(44),font_size='12sp',halign='center',valign='middle')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        self.reference_box.add_widget(self.hint)
        self.body.add_widget(self.reference_box)
        controls=ResponsiveBoxLayout(orientation='vertical',gap_px=7)
        self.swatch_row=ResponsiveBoxLayout(height_px=44,gap_px=6);controls.add_widget(self.swatch_row)
        self.selected_label=Label(size_hint_y=None,height=m.h(26),font_size='14sp',halign='center')
        controls.add_widget(self.selected_label)
        self.picker=ColorPicker(color=(1,1,1,1))
        self.picker.bind(color=self._change_color);controls.add_widget(self.picker)
        actions=ResponsiveBoxLayout(height_px=46,gap_px=8)
        self.cancel_button=UIButton();self.restore_button=UIButton();self.save_button=PrimaryButton()
        self.cancel_button.bind(on_release=lambda *_:self.back())
        self.restore_button.bind(on_release=lambda *_:self.restore_defaults())
        self.save_button.bind(on_release=lambda *_:self.save())
        for button in (self.cancel_button,self.restore_button,self.save_button):
            button.font_size='14sp';button.halign='center';button.valign='middle'
            button.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
            actions.add_widget(button)
        controls.add_widget(actions);self.body.add_widget(controls);self.controls=controls
        root.add_widget(self.body);self.add_widget(root)
        self.bind(size=self._resize)
        self.retranslate()

    def configure(self,source,index=0):
        self._source=source.name
        self._draft=[tuple(c[:3])+(1.,) for c in source.palette_colors()]
        self._defaults=[tuple(c[:3])+(1.,) for c in source.default_palette_colors()]
        self._slot_labels=(list(source.palette_slot_labels()) if hasattr(source,'palette_slot_labels') else
                           [str(i+1) for i in range(len(self._draft))])
        self._index=max(0,min(index,len(self._draft)-1))
        self.puzzle_label.text=(source.palette_title() if hasattr(source,'palette_title') else
                               tr('directory.'+source._cube.puzzle_kind))
        self.reference_holder.clear_widgets()
        cls=MastermorphixNet if len(self._draft)==4 else CubePaletteNet
        self.reference=cls(colors=list(self._draft),selected_face=self._index)
        if isinstance(self.reference,CubePaletteNet):self.reference.labels=self._slot_labels
        self.reference_holder.add_widget(self.reference)
        self._build_swatches();self._sync_picker();self._resize()

    def _build_swatches(self):
        # Import lazily to keep the shared entry screen free of import cycles.
        from ui.screens.mastermorphix_screen import _Swatch
        self.swatch_row.clear_widgets();self._swatches=[]
        for i,rgba in enumerate(self._draft):
            button=_Swatch(rgba,text=self._slot_labels[i],active=i==self._index)
            button.bind(on_release=lambda *_,index=i:self.select(index))
            self.swatch_row.add_widget(button);self._swatches.append(button)

    def _sync_picker(self):
        self._updating=True
        try:self.picker.color=self._draft[self._index]
        finally:self._updating=False
        self._refresh_draft()

    def select(self,index):
        self._index=index;self._sync_picker()

    def _change_color(self,picker,rgba):
        if self._updating or not self._draft:return
        value=tuple(rgba[:3])+(1.,);previous=self._draft[self._index]
        for i,color in enumerate(self._draft):
            if i!=self._index and color[:3]==value[:3]:
                self._draft[i]=previous;break
        self._draft[self._index]=value
        if rgba[3]!=1:
            self._updating=True
            try:picker.color=value
            finally:self._updating=False
        self._refresh_draft()

    def _refresh_draft(self):
        if not self._draft:return
        self.reference.colors=list(self._draft);self.reference.selected_face=self._index
        for i,button in enumerate(self._swatches):
            button.rgba=self._draft[i];button.active=i==self._index
            rgb=self._draft[i][:3]
            button.color=(.04,.07,.1,1) if .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]>.5 else (1,1,1,1)
            button._rebuild()
        self.selected_label.text=tr('palette.selected',i=self._slot_labels[self._index])

    def restore_defaults(self):
        if self._defaults:self._draft=list(self._defaults);self._sync_picker()

    def save(self):
        if self._source is None or not self.manager.has_screen(self._source):return
        if len({c[:3] for c in self._draft})!=len(self._draft):
            self.selected_label.text=tr('palette.duplicate');return
        source=self.manager.get_screen(self._source)
        source.apply_palette_colors(list(self._draft))
        self.back()

    def back(self):
        if self.manager is not None and self._source and self.manager.has_screen(self._source):
            self.manager.current=self._source

    def _keyboard(self,window,key,*args):
        if key in (27,1001):self.back();return True
        return False

    def on_pre_enter(self,*args):
        Window.bind(on_keyboard=self._keyboard);self.retranslate();self._resize()

    def on_pre_leave(self,*args):Window.unbind(on_keyboard=self._keyboard)

    def _resize(self,*args):
        wide=self.width>self.height*1.15
        self.body.orientation='horizontal' if wide else 'vertical'
        self.reference_box.size_hint=(.34,1) if wide else (1,None)
        if not wide:self.reference_box.height=m.h(175)
        self.controls.size_hint=(.66,1) if wide else (1,1)

    def retranslate(self):
        self.title.text=tr('palette.settings');self.hint.text=tr('palette.hint')
        self.cancel_button.text=tr('poly.cancel');self.restore_button.text=tr('poly.restore_colors')
        self.save_button.text=tr('palette.save');self._refresh_draft()

    def refresh_theme(self):
        from kivy.app import App
        for label in (self.title,self.puzzle_label,self.hint,self.selected_label):
            label.color=App.get_running_app().theme.text
