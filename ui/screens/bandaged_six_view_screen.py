"""Bandage entry shares Camouflage's six views, colour brush and drag panels."""
from copy import deepcopy
from kivy.clock import Clock
from cube.bandaged_cube import BandagedCube,KINDS
from cube.bandaged_observation import BandagedSixViewDraft,COLOR_CODES,state_key
from cube.bandaged_entry import plates
from cube.conversion import cubies_to_facelets
from cube.cuboid import FACES
from app.constants import COLOR_INFO
from app.i18n import tr
from app.prefs import get as pref_get
from ui.screens.cuboid_six_view_screen import CuboidSixViewScreen,_app


class BandagedSixViewScreen(CuboidSixViewScreen):
    draft_class=BandagedSixViewDraft
    entry_twist_screen='TwistScreen'

    def _build(self):
        super()._build()
        # Fixed-shell cubes have no absent cells, unpainted outer walls or
        # depth choices. Keep the common six-view layout and useful controls.
        for row in (self.tools[-2].parent,self.depth_label.parent,self.outside_button.parent):
            if row.parent is not None:row.parent.remove_widget(row)

    def on_pre_enter(self,*args):
        app=_app();cube=app.cube
        if not isinstance(cube,BandagedCube):
            Clock.schedule_once(lambda *_:setattr(self.manager,'current','HomeScreen'),0)
            return
        current=state_key(cube);kind=cube.puzzle_kind
        fresh=getattr(self,'_fresh_request',False);self._fresh_request=False
        keep=self._six_state is not None and self._six_state.get('kind')==kind and self._six_state.get('version')==3
        if not keep:
            cached=getattr(app,'bandage_six_cache',{}).get(kind)
            self._six_state=deepcopy(cached) if cached is not None else None
            keep=self._six_state is not None
            self._six_face=2;self._six_undo=[];self._six_applied=None;self._six_cube_key=None
        if fresh:self._six_applied=None
        if keep and not fresh and self._six_cube_key is not None and self._six_cube_key!=current:
            draft=self.draft_class.from_cube(cube);self._six_state=draft.state();self._six_applied=deepcopy(self._six_state)
        elif not keep:
            # Fresh entry starts blank. Legacy drafts retain their recorded
            # colours and seams; no hidden state is guessed from a scramble.
            legacy=getattr(app,'bandage_entry_cache',{}).get(self.input_cache_key(cube))
            draft=(self.draft_class.from_facelets(kind,*legacy) if legacy is not None else self.draft_class(kind))
            self._six_state=draft.state();self._six_applied=None
        self._cube=cube;self._six_cube_key=current
        self._draft=self.draft_class(kind,self._six_state)
        self._depth=None;self._selected=();self._color=min(max(self._color,0),5)
        self.palette=tuple(tuple(c) for c in pref_get('poly_palette_'+kind,self.default_palette_colors()))
        self._build_colors();self.retranslate();self._refresh()
        Clock.schedule_once(self._settle_layout,0)

    def _refresh(self):
        if self._draft is None:return
        super()._refresh()
        self.hint.text=tr('bandage.six_hint')

    def default_palette_colors(self):
        return [tuple(COLOR_INFO[c][1]) if len(COLOR_INFO[c][1])==4 else tuple(COLOR_INFO[c][1])+(1,) for c in COLOR_CODES]

    def replace_cube(self,cube):
        self._cube=cube.clone();_app().cube=self._cube
        _app().solve_result=None

    def randomize(self):
        if self._job is None:self._load_cube(BandagedCube.random_scramble(self._cube.puzzle_kind))

    def entry_reset_solved(self):
        self._load_cube(BandagedCube.solved(self._cube.puzzle_kind))

    def input_cache_key(self,cube=None):
        cube=cube or self._cube or _app().cube
        from app.facelet_cache import cache_key
        return cache_key(cube.puzzle_kind,cube.n)

    def collect_facelets(self):
        return self._draft.facelets()

    def set_facelets(self,data,remember=False):
        from app.facelet_cache import fits
        if not fits(data,self._cube.n):return False
        cube=_app().cube
        if isinstance(cube,BandagedCube) and cube.puzzle_kind==self._cube.puzzle_kind and cubies_to_facelets(cube.cubies,cube.n)==data:
            if self._ready() and state_key(cube)==state_key(self._cube) and data==self.collect_facelets():return True
            self._load_cube(cube)
        else:
            if remember:self._remember()
            self._draft=self.draft_class.from_facelets(self._cube.puzzle_kind,data,self._draft.connections())
            self._six_applied=None;self._selected=();self._sync()
        return True

    def _continue(self,after):
        app=_app();app.cube=self._cube;app.n=self._cube.n;app.solve_result=None
        from app.facelet_cache import remember_recent
        remember_recent(app,self.collect_facelets())
        if after=='twist':self.manager.current='TwistScreen'
        elif after=='solve':
            if self.manager.get_screen('SolvingScreen').configure(self._cube,self.name) is not False:
                self.manager.current='SolvingScreen'

    def on_pre_leave(self,*args):
        self.reset_interaction()
        if self._draft is None:return
        app=_app();kind=self._draft.kind
        if not hasattr(app,'bandage_six_cache'):app.bandage_six_cache={}
        app.bandage_six_cache[kind]=deepcopy(self._six_state)
        if not hasattr(app,'bandage_entry_cache'):app.bandage_entry_cache={}
        app.bandage_entry_cache[self.input_cache_key()]=(self.collect_facelets(),self._draft.connections())
        if app.puzzle_kind==kind:
            from app.facelet_cache import remember_recent
            remember_recent(app,self.collect_facelets())

    def help(self):
        from demo.coverage import supports
        if supports(self._cube.puzzle_kind,self._cube.n):return super().help()
        from kivy.uix.label import Label
        from kivy.uix.popup import Popup
        from ui.widgets.dialogs import theme_popup
        label=Label(text=tr('bandage.six_help'),halign='left',valign='middle')
        label.bind(size=lambda w,*_:setattr(w,'text_size',(w.width-24,w.height)))
        popup=Popup(title=tr('six.title'),content=label,size_hint=(.9,.7))
        theme_popup(popup,_app().theme);popup.open()
