"""Export a separate 3D player through a bounded frame queue, without touching input."""
import math,queue,shutil,threading,time,uuid
from pathlib import Path
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color,Rectangle,Fbo,ClearColor,ClearBuffers,Scale,Translate
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.core.text import Label as CoreLabel
from kivy.utils import platform
from ui.widgets.buttons import UIButton
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.dialogs import theme_popup
from app.i18n import tr
from demo.cases import localized
from demo.media import course_sections,speech_language
from services.demo_video import VideoWriter,AlignedAudio,prepare_narration,mux,subtitle_time
from services.speech import SpeechEngine


class VideoCaption(Widget):
    """Synchronous text drawing: an offline FBO must not capture stale KV bindings."""
    def __init__(self,text='',color=(0,0,0,1),font_size=15,**kwargs):
        super().__init__(**kwargs)
        self.text=text;self.color=color;self.font_size=font_size;self.font_name=Label().font_name
        self._last_draw=None

    def texture_update(self):
        key=(self.text,tuple(self.pos),tuple(self.size),tuple(self.color),self.font_size,self.font_name)
        if key==self._last_draw:return
        self._last_draw=key
        label=CoreLabel(text=self.text,font_name=self.font_name,font_size=self.font_size,
                        text_size=(self.width,None),halign='left')
        label.refresh();texture=label.texture;self.canvas.clear()
        if texture:
            with self.canvas:
                Color(*self.color)
                Rectangle(texture=texture,size=texture.size,pos=(self.x,self.center_y-texture.height/2))


class VideoExport:
    WIDTH=480;HEIGHT=640;FPS=12

    def __init__(self,owner,part=None,voice=True):
        self.owner=owner;self.mode=owner.mode;self.case=dict(owner._case());self.voice=voice
        self.parts=[dict(part)] if part else list(course_sections(self.case))
        self.start_index=self.parts[0]['start'];self.end_index=self.parts[-1]['end']
        self.speed=getattr(owner,'_playback_speed',1.)
        self.render_started=None;self.completed_moves=0;self._last_eta=0
        self.cancelled=threading.Event();self.frames=queue.Queue(maxsize=3);self.player=None;self.event=None
        self.finished=threading.Event()
        self.speech=SpeechEngine(speech_language(self.case.get('narration_intro',localized(self.case['tip']))))
        base=(Path(App.get_running_app().user_data_dir)/'exports').resolve();base.mkdir(parents=True,exist_ok=True)
        self.export_root=base
        self.output=base/('course-'+uuid.uuid4().hex+'.mp4')
        self.folder=base/('.work-'+uuid.uuid4().hex);self.folder.mkdir()
        self.subtitles=[];self.frame_count=0;self.part_index=0;self.hold=False;self.ending=False
        self.actions_started=0;self.final_signature=None

    def start(self):
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        self.message=Label(text=tr('media.preparing',i=0,total=len(self.parts)),halign='center',valign='middle')
        self.message.bind(size=lambda w,v:setattr(w,'text_size',v));content.add_widget(self.message)
        self.cancel_button=UIButton(text=tr('poly.cancel'),height=44,size_hint_y=None)
        self.cancel_button.bind(on_release=lambda *_:self.cancel());content.add_widget(self.cancel_button)
        self.popup=Popup(title=tr('media.export'),content=content,size_hint=(.92,.5),auto_dismiss=False)
        theme_popup(self.popup,App.get_running_app().theme);self.popup.open()
        threading.Thread(target=self._run,daemon=True).start()

    def _status(self,key,**values):
        def update(_):
            if self.owner._export_job is self and not self.cancelled.is_set():self.message.text=tr(key,**values)
        Clock.schedule_once(update,0)

    def _run(self):
        writer=None;audio=None;error=None
        try:
            prepared=prepare_narration(self.case,self.parts,self.folder,self.voice,self.FPS,self.cancelled.is_set,
                lambda i,total:self._status('media.preparing',i=i,total=total),self.speech)
            if self.cancelled.is_set():raise InterruptedError()
            video=self.folder/'silent.mp4';wav=self.folder/'narration.wav'
            writer=VideoWriter(video,self.WIDTH,self.HEIGHT,self.FPS)
            if self.voice:audio=AlignedAudio(wav,self.FPS)
            Clock.schedule_once(lambda _:self._begin_frames(prepared),0)
            while True:
                if self.cancelled.is_set():raise InterruptedError()
                try:item=self.frames.get(timeout=.1)
                except queue.Empty:continue
                if item is None:break
                rgba,count,speech,offset=item
                for _ in range(count):
                    if self.cancelled.is_set():raise InterruptedError()
                    writer.write(rgba)
                if audio:audio.append(count,speech,offset)
            self._status('media.encoding');writer.finish();writer=None
            if audio:audio.close();audio=None
            finished=self.folder/'finished.mp4'
            if self.voice:mux(video,wav,finished,self.cancelled.is_set)
            else:video.rename(finished)
            if self.cancelled.is_set():raise InterruptedError()
            # Publish only a finished file. Each job owns a unique output name.
            srt='\n\n'.join(f'{i+1}\n{subtitle_time(a)} --> {subtitle_time(b)}\n{text}'
                for i,(a,b,text) in enumerate(self.subtitles))+'\n'
            (self.folder/'captions.srt').write_text(srt,encoding='utf-8-sig')
            finished.rename(self.output)
            (self.folder/'captions.srt').rename(self.output.with_suffix('.srt'))
            if self.cancelled.is_set():
                self.output.unlink(missing_ok=True);self.output.with_suffix('.srt').unlink(missing_ok=True)
                raise InterruptedError()
        except InterruptedError:pass
        except Exception as exc:
            error=str(exc)
            from kivy.logger import Logger
            Logger.exception('Demo: video export failed')
        finally:
            for resource in (writer,audio,self.speech):
                if resource:
                    try:resource.close()
                    except Exception as exc:
                        if not error:error=str(exc)
            # Only remove this job's checked private directory, never a user-selected path.
            resolved=self.folder.resolve()
            if resolved.parent==self.export_root and resolved.name.startswith('.work-') and not self.folder.is_symlink():
                shutil.rmtree(resolved,ignore_errors=True)
            self.finished.set()
            Clock.schedule_once(lambda _:self._finish(error),0)

    def _begin_frames(self,prepared):
        if self.cancelled.is_set():return
        try:
            from ui.screens.demo_screen import DemoScreen,_set_demo_cube
            self.player=DemoScreen(name='VideoExportPlayer')
            self.player._follow=lambda target,begin:begin()
            self.player.enter_case(self.mode,0,0,[dict(title=self.case['name'],desc='',cases=[self.case])])
            self.player.set_speed(self.speed)
            self.player.seek(self.start_index)
            view=self.player.view
            if view.parent:view.parent.remove_widget(view)
            self.canvas=BoxLayout(orientation='vertical',size_hint=(None,None),size=(self.WIDTH,self.HEIGHT),padding=16,spacing=8)
            with self.canvas.canvas.before:
                Color(*App.get_running_app().theme.bg);self.background=Rectangle(pos=(0,0),size=self.canvas.size)
            color=App.get_running_app().theme.text
            self.heading=VideoCaption(text=self.player.lbl_mode.text,size_hint_y=None,height=44,color=color,font_size=20)
            self.caption=VideoCaption(size_hint_y=None,height=154,color=color,font_size=15)
            self.progress=VideoCaption(size_hint_y=None,height=34,color=color,font_size=15)
            self.canvas.add_widget(self.heading);self.canvas.add_widget(view);self.canvas.add_widget(self.caption);self.canvas.add_widget(self.progress)
            self.canvas.do_layout();view.size_hint=(1,1);self.canvas.do_layout()
            self.capture_fbo=Fbo(size=(self.WIDTH,self.HEIGHT),with_stencilbuffer=True)
            with self.capture_fbo:
                ClearColor(0,0,0,0);ClearBuffers();Scale(1,-1,1)
                Translate(-self.canvas.x,-self.canvas.y-self.HEIGHT,0)
            self.capture_fbo.add(self.canvas.canvas)
            _set_demo_cube(view,self.player._work)
            self.prepared=prepared;self.event=Clock.schedule_interval(self._pump,0)
            self.render_started=time.monotonic();self._refresh_eta()
        except Exception as exc:self._render_failed(exc)

    def _tick_animation(self):
        view=self.player.view
        if getattr(view,'_anim',None) is not None:
            view._anim_event.cancel();view._anim_tick(1/self.FPS)
        elif getattr(view,'_event',None) is not None:
            event=view._event;event.cancel();event.callback(1/self.FPS)
        else:raise RuntimeError('Animation did not start')
        # A completed atom may schedule the following atom during its callback.
        for attr in ('_anim_event','_event'):
            event=getattr(view,attr,None)
            if event:event.cancel()

    def _capture(self,redraw=True):
        self.canvas.do_layout()
        for label in (self.heading,self.caption,self.progress):label.texture_update()
        view=self.player.view
        if redraw:
            if hasattr(view,'_draw'):view._draw()
            elif hasattr(view,'_draw_mesh'):view._draw_mesh()
        if hasattr(self.player,'move_guide'):self.player.move_guide.draw()
        for attr in ('_fbo','_surface_fbo'):
            fbo=getattr(view,attr,None)
            if fbo:fbo.draw()
        self.capture_fbo.ask_update();self.capture_fbo.draw()
        return bytes(self.capture_fbo.texture.pixels)

    def _pump(self,_dt):
        self._refresh_eta()
        # Export faster than real time while yielding frequently to touch/cancel events.
        deadline=time.perf_counter()+.008
        for _ in range(3):
            if self._pump_frame(_dt) is False:return False
            if self.frames.full() or time.perf_counter()>=deadline:return

    def _pump_frame(self,_dt):
        if self.cancelled.is_set():return False
        if self.frames.full():return
        try:
            p=self.player
            if self.ending:self.frames.put_nowait(None);self.event=None;return False
            part=self.prepared[self.part_index]
            if not self.hold:
                pages=[part['text'][i:i+80] for i in range(0,len(part['text']),80)] or ['']
                page=getattr(self,'hold_page',0)
                a=round(page*part['frames']/len(pages));b=round((page+1)*part['frames']/len(pages))
                self.caption.text=part['part']['title']+'\n'+pages[page]
                self.progress.text=f'{p._move_index} / {len(p._moves)}'
                rgba=self._capture();count=b-a
                self.subtitles.append((self.frame_count/self.FPS,(self.frame_count+count)/self.FPS,pages[page]))
                self.frames.put_nowait((rgba,count,part['path'],a/self.FPS));self.frame_count+=count
                self.hold_page=page+1
                if self.hold_page==len(pages):self.hold=True;self.hold_page=0
                return
            if p._move_index>=part['part']['end'] and not p._busy:
                if self.part_index<len(self.prepared)-1:
                    self.part_index+=1;self.hold=False;return
                self.caption.text=part['part'].get('check','') or localized(self.case['tip'])
                self.progress.text=f'{p._move_index} / {len(p._moves)}'
                from demo.solutions import state_signature
                self.final_signature=state_signature(p._work)
                self.frames.put_nowait((self._capture(),self.FPS*2,None,0));self.frame_count+=self.FPS*2;self.ending=True;return
            if not p._busy:
                self.actions_started+=1
                p._start_move(p._moves[p._move_index],p._move_index+1)
            action_text=p.lbl_action.text;progress_text=p.lbl_progress.text
            guide_spec=p.move_guide.spec if hasattr(p,'move_guide') else None
            self._tick_animation()
            if hasattr(p,'move_guide'):p.move_guide.spec=guide_spec
            self.completed_moves=max(0,p._move_index-self.start_index)
            self.caption.text=part['part']['title']+'\n'+(action_text or part['part']['text'])
            self.progress.text=progress_text
            # The animation tick already drew this frame. Rebuilding the same geometry
            # twice is costly on deep-cut models with hundreds of small panels.
            self.frames.put_nowait((self._capture(redraw=not p._busy),1,None,0));self.frame_count+=1
        except Exception as exc:self._render_failed(exc);return False

    def _refresh_eta(self):
        if self.render_started is None or self.cancelled.is_set() or time.monotonic()-self._last_eta<1:return
        self._last_eta=time.monotonic()
        from services.export_timing import remaining_seconds
        total=self.end_index-self.start_index
        remaining=remaining_seconds(self._last_eta-self.render_started,self.completed_moves,total)
        estimate=(tr('media.eta_pending') if remaining is None else
                  tr('media.eta',minutes=round(remaining)//60,seconds=round(remaining)%60))
        self.message.text=tr('media.rendering',i=self.completed_moves,total=total)+'\n'+estimate

    def _render_failed(self,exc):
        self.render_error=str(exc);self.cancelled.set();self.speech.stop()

    def _cleanup_player(self):
        if self.event:self.event.cancel();self.event=None
        if self.player and hasattr(self.player,'move_guide'):self.player.move_guide.dispose()
        if self.player:self.player._stop();self.player=None
        if getattr(self,'capture_fbo',None) is not None:
            if self.canvas is not None:self.capture_fbo.remove(self.canvas.canvas)
            self.capture_fbo=None
        self.canvas=None

    def cancel(self):
        self.cancelled.set();self.speech.stop();self._cleanup_player();self.popup.dismiss()
        if self.owner._export_job is self:
            self.owner._export_job=None;self.owner.lbl_media.text=tr('media.cancelled');self.owner._media_controls()

    def _finish(self,error):
        self._cleanup_player();self.popup.dismiss()
        if self.owner._export_job is not self:return
        self.owner._export_job=None;self.owner._media_controls()
        error=getattr(self,'render_error',None) or error
        if error:
            detail=tr(error) if error.startswith('media.') else error
            self.owner.lbl_media.text=tr('media.failed',detail=detail);return
        if self.cancelled.is_set():self.owner.lbl_media.text=tr('media.cancelled');return
        self.owner.lbl_media.text=tr('media.finished',path=str(self.output))
        if platform=='android':self._offer_save()

    def _offer_save(self):
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        message=Label(text=tr('media.finished',path=self.output.name),halign='center')
        message.bind(size=lambda w,v:setattr(w,'text_size',v));content.add_widget(message)
        save=UIButton(text=tr('media.save'),height=44,size_hint_y=None);content.add_widget(save)
        close=UIButton(text=tr('demo.close'),height=44,size_hint_y=None);content.add_widget(close)
        popup=Popup(title=tr('media.export'),content=content,size_hint=(.92,.45))
        close.bind(on_release=lambda *_:popup.dismiss())
        def choose(*_):
            from android import activity
            from android.runnable import run_on_ui_thread
            from jnius import autoclass
            Intent=autoclass('android.content.Intent');host=autoclass('org.kivy.android.PythonActivity').mActivity
            code=4817
            def result(request,response,data):
                if request!=code:return
                activity.unbind(on_activity_result=result)
                Clock.schedule_once(lambda _:setattr(save,'disabled',False),0)
                if response!=-1 or data is None:return
                uri=str(data.getData().toString())
                def copy():
                    try:
                        autoclass('org.cubesolver.media.VideoBridge').copyToUri(host,str(self.output),uri)
                        text=tr('media.saved')
                    except Exception as exc:text=tr('media.failed',detail=str(exc))
                    Clock.schedule_once(lambda _:setattr(message,'text',text),0)
                threading.Thread(target=copy,daemon=True).start()
            activity.bind(on_activity_result=result)
            save.disabled=True
            intent=Intent(Intent.ACTION_CREATE_DOCUMENT);intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType('video/mp4');intent.putExtra(Intent.EXTRA_TITLE,self.output.name)
            @run_on_ui_thread
            def launch():
                try:host.startActivityForResult(intent,code)
                except Exception as exc:
                    activity.unbind(on_activity_result=result)
                    text=tr('media.failed',detail=str(exc))
                    def failed(_):save.disabled=False;message.text=text
                    Clock.schedule_once(failed,0)
            launch()
        save.bind(on_release=choose);theme_popup(popup,App.get_running_app().theme);popup.open()
