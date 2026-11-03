"""Course navigation, cancellable narration and video export controls."""
from collections import OrderedDict
from pathlib import Path
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.buttons import UIButton
from ui.widgets.dialogs import theme_popup
from app.i18n import tr
from demo.media import course_sections,section_at,narration,speech_language


class DemoMediaMixin:
    def _init_media(self):
        self._narrator=None;self._narrating=False;self._voice_enabled=False
        self._media_epoch=0;self._spoken=set();self._checkpoints=OrderedDict();self._export_job=None
        self._playback_speed=1.;self._chapter_popup=None;self._chapter_token=None
        self._voice_mode='section'

    def _build_media_controls(self,panel):
        row=ResponsiveBoxLayout(height_px=42,gap_px=5)
        self.btn_section_prev=UIButton(text=tr('media.previous'))
        self.btn_section_next=UIButton(text=tr('media.next'))
        self.lbl_section=UIButton(font_size='12sp')
        self.lbl_section.bind(on_release=lambda *_:self.open_chapters())
        self.btn_section_prev.bind(on_release=lambda *_:self.change_section(-1))
        self.btn_section_next.bind(on_release=lambda *_:self.change_section(1))
        for w in (self.btn_section_prev,self.lbl_section,self.btn_section_next):row.add_widget(w)
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=42,gap_px=5)
        self.btn_voice=UIButton(text=tr('media.voice_off'))
        self.btn_export=UIButton(text=tr('media.export'))
        self.btn_speed=UIButton(font_size='12sp')
        self.btn_speed.bind(on_release=lambda *_:self.cycle_speed())
        self.btn_voice.bind(on_release=lambda *_:self.toggle_voice())
        self.btn_export.bind(on_release=lambda *_:self.open_export())
        for button in (self.btn_voice,self.btn_speed,self.btn_export):row.add_widget(button)
        panel.add_widget(row)
        self.lbl_media=Label(text='',font_size='12sp',size_hint_y=None,height=0,halign='center')
        self.lbl_media.bind(width=lambda w,v:setattr(w,'text_size',(v,None)))
        self.lbl_media.bind(texture_size=lambda w,v:setattr(w,'height',v[1]+6 if w.text else 0))
        panel.add_widget(self.lbl_media)

    def _media_reset(self):
        self._close_chapters()
        self._checkpoints.clear();self._spoken.clear()
        self._checkpoints[0]=self._initial.clone()
        self._parts=course_sections(self._case())
        self.lbl_media.text=''

    def _media_stop(self):
        self._media_epoch+=1;self._narrating=False
        if self._narrator:self._narrator.stop()

    def _remember_checkpoint(self):
        if self._work is None:return
        if self._move_index%64 and self._move_index!=len(self._moves):return
        self._checkpoints[self._move_index]=self._work.clone()
        self._checkpoints.move_to_end(self._move_index)
        while len(self._checkpoints)>16:
            key=next(k for k in self._checkpoints if k!=0)
            del self._checkpoints[key]

    def _restore_index(self,index):
        key=max((k for k in self._checkpoints if k<=index),default=0)
        self._work=self._checkpoints[key].clone() if key in self._checkpoints else self._initial.clone()
        for i in range(key,index):
            self._work.apply_move(self._moves[i])
            if (i+1)%64==0:
                self._checkpoints[i+1]=self._work.clone()
                while len(self._checkpoints)>16:
                    del self._checkpoints[next(k for k in self._checkpoints if k!=0)]

    def seek(self,index):
        if self._initial is None:return
        self._stop();index=max(0,min(int(index),len(self._moves)))
        self._restore_index(index);self._move_index=index;self._spoken.clear()
        from ui.screens.demo_screen import _set_demo_cube
        _set_demo_cube(self.view,self._work,getattr(self,'_highlight',None));self._update_controls()

    def change_section(self,direction):
        parts=getattr(self,'_parts',())
        if not parts:return
        current=section_at(parts,self._move_index)
        target=max(0,min(current+direction,len(parts)-1))
        self.seek(parts[target]['start'])

    def toggle_voice(self):
        self._stop()
        if not self._voice_enabled:self._voice_enabled=True;self._voice_mode='section'
        elif self._voice_mode=='section':self._voice_mode='step'
        else:self._voice_enabled=False
        self._spoken.clear();self._update_controls()

    def _maybe_narrate(self):
        if not self._voice_enabled or not self._playing:return False
        if self._narrating:return True
        part=next((p for p in self._parts if p['start']==self._move_index),None)
        step_mode=self._voice_mode=='step'
        if self._move_index in self._spoken or (part is None and not step_mode):return False
        from kivy.app import App
        from services.speech import Narrator
        text=(tr('media.step_voice',i=self._move_index+1)+self.lbl_action.text if step_mode else
              narration(self._case(),part,first=self._move_index==0))
        if not text:return False
        if self._narrator:self._narrator.stop()
        self._narrator=Narrator(Path(App.get_running_app().user_data_dir)/'voice-cache',speech_language(text))
        epoch=self._media_epoch;index=self._move_index;self._narrating=True
        self.lbl_media.text=tr('media.speaking');self._update_controls()
        def done():
            if self._media_epoch!=epoch or not self._playing:return
            self._narrating=False;self._spoken.add(index);self.lbl_media.text='';self._advance()
        def error(detail):
            if self._media_epoch!=epoch:return
            self._narrating=False;self._playing=False
            self.lbl_media.text=tr('media.voice_missing');self._update_controls()
        self._narrator.speak(text,done,error);return True

    def _media_controls(self):
        if not hasattr(self,'lbl_section'):return
        parts=getattr(self,'_parts',());index=section_at(parts,self._move_index)
        self.lbl_section.text=tr('media.chapters',i=index+1,total=len(parts)) if parts else '—'
        self.btn_speed.text=tr('media.speed',speed=f'{self._playback_speed:g}')
        self.btn_section_prev.disabled=not parts or index==0
        self.btn_section_next.disabled=not parts or index>=len(parts)-1
        self.btn_voice.text=tr('media.voice_step' if self._voice_enabled and self._voice_mode=='step' else
                              'media.voice_on' if self._voice_enabled else 'media.voice_off')
        self.btn_section_prev.text=tr('media.previous');self.btn_section_next.text=tr('media.next')
        self.btn_export.text=tr('media.export')
        self.btn_export.disabled=not self._moves or self._export_job is not None
        if self._narrating:
            self.btn_prev.disabled=True;self.btn_next.disabled=True

    def set_speed(self,speed):
        speed=float(speed)
        if not .25<=speed<=4:raise ValueError('Playback speed must be 0.25–4')
        playing=self._playing;self._stop();self._playback_speed=speed;self._update_controls()
        if playing:self.play()

    def cycle_speed(self):
        speeds=(.5,1.,1.5,2.,3.)
        self.set_speed(speeds[(speeds.index(self._playback_speed)+1)%len(speeds)] if self._playback_speed in speeds else 1.)

    def _close_chapters(self):
        self._chapter_token=None
        if self._chapter_popup:self._chapter_popup.dismiss();self._chapter_popup=None

    def open_chapters(self):
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.boxlayout import BoxLayout
        from kivy.app import App
        from demo.cases import localized
        if not getattr(self,'_parts',()):return
        self._stop();self._close_chapters();self._chapter_token=token=object()
        body=BoxLayout(orientation='vertical',size_hint_y=None,spacing=6)
        body.bind(minimum_height=body.setter('height'));scroll=ScrollView(do_scroll_x=False);scroll.add_widget(body)
        popup=self._chapter_popup=Popup(title=tr('media.chapter_list'),content=scroll,size_hint=(.94,.84))
        def choose(index):
            if self._chapter_token is not token:return
            if self.manager is not None and self.manager.current!=self.name:return
            popup.dismiss();self.seek(self._parts[index]['start'])
        for i,p in enumerate(self._parts):
            button=UIButton(text=f"{localized(p['title'])}  ·  {p['start']+1}–{p['end']}",
                            size_hint_y=None,height=52,font_size='13sp',active=i==section_at(self._parts,self._move_index))
            button.bind(on_release=lambda *_,index=i:choose(index));body.add_widget(button)
        popup.bind(on_dismiss=lambda *_:setattr(self,'_chapter_token',None) if self._chapter_token is token else None)
        theme_popup(popup,App.get_running_app().theme);popup.open();return popup

    def open_export(self):
        if self._export_job or not self._moves:return
        self._stop()
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        hint=Label(text=tr('media.export_hint'),halign='center',valign='middle')
        hint.bind(size=lambda w,v:setattr(w,'text_size',v));content.add_widget(hint)
        from demo.media import video_seconds,section_at
        estimate=Label(halign='center',size_hint_y=None,height=46,font_size='12sp')
        estimate.bind(size=lambda w,v:setattr(w,'text_size',v));content.add_widget(estimate)
        voice_row=ResponsiveBoxLayout(height_px=40);voice=CheckBox(active=True,size_hint_x=.2)
        voice_row.add_widget(voice);voice_row.add_widget(Label(text=tr('media.with_voice')));content.add_widget(voice_row)
        def duration(*_):
            seconds=round(video_seconds(self._case(),self._initial,self._playback_speed,voice.active))
            estimate.text=tr('media.estimated_length',minutes=seconds//60,seconds=seconds%60)
        voice.bind(active=duration);duration()
        popup=Popup(title=tr('media.export'),content=content,size_hint=(.92,.64),auto_dismiss=False)
        for key,scope in (('media.full','full'),('media.current','section')):
            button=UIButton(text=tr(key),height=44,size_hint_y=None)
            button.bind(on_release=lambda *_,s=scope:self._start_export(popup,s,voice.active))
            content.add_widget(button)
        close=UIButton(text=tr('demo.close'),height=44,size_hint_y=None);close.bind(on_release=lambda *_:popup.dismiss());content.add_widget(close)
        from kivy.app import App
        theme_popup(popup,App.get_running_app().theme);popup.open();return popup

    def _start_export(self,chooser,scope,voice):
        if self._export_job:return
        chooser.dismiss()
        from ui.demo_video import VideoExport
        parts=self._parts
        selected=parts[section_at(parts,self._move_index)] if scope=='section' else None
        job=self._export_job=VideoExport(self,selected,voice)
        self._media_controls();job.start()

    def _cancel_export(self):
        if self._export_job:self._export_job.cancel()

    def pause_media(self):
        self._stop();self._cancel_export();self._close_chapters()
        if hasattr(self,'move_guide'):self.move_guide.stop()

    def resume_media(self):
        # Returning from background keeps playback/voice paused, but lets the
        # teaching overlay track subsequent camera gestures again.
        if hasattr(self,'move_guide'):self.move_guide.start()
