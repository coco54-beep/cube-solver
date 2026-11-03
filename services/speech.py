"""Offline system speech with cancellable ownership; no network TTS service."""
import base64,hashlib,json,os,shutil,subprocess,sys,threading,time,uuid,wave
from pathlib import Path


class SpeechError(RuntimeError):pass

_sound_lock=threading.Lock()
_sound_owner=None


def hidden_process_options():
    return dict(creationflags=subprocess.CREATE_NO_WINDOW) if sys.platform=='win32' else {}


class SpeechEngine:
    def __init__(self,language='zh-CN'):
        self.language=language;self.process=None;self.android=None;self.cancelled=threading.Event()

    def _android(self):
        if self.android is None:
            from jnius import autoclass
            activity=autoclass('org.kivy.android.PythonActivity').mActivity
            self.android=autoclass('org.cubesolver.media.SpeechBridge').create(activity,self.language)
        if self.cancelled.is_set():self.android.close();raise InterruptedError()
        return self.android

    def render(self,text,path,cancel=None):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        if self.cancelled.is_set() or (cancel and cancel()):raise InterruptedError()
        from kivy.utils import platform
        if platform=='android':
            try:self._android().render(text,str(path))
            except Exception as exc:
                if self.cancelled.is_set():raise InterruptedError() from exc
                raise SpeechError('media.voice_missing') from exc
        elif sys.platform=='win32':
            payload=base64.b64encode(json.dumps(dict(text=text,path=str(path.resolve()),language=self.language),ensure_ascii=False).encode()).decode()
            script="""$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$taskVoiceSpec=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('PAYLOAD'))|ConvertFrom-Json
$taskVoice=New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
 $taskMatch=$taskVoice.GetInstalledVoices()|Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq $taskVoiceSpec.language }|Select-Object -First 1
 if ($null -eq $taskMatch) { throw 'No system voice for this language' }
 $taskVoice.SelectVoice($taskMatch.VoiceInfo.Name)
 $taskFormat=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono)
 $taskVoice.SetOutputToWaveFile($taskVoiceSpec.path,$taskFormat)
 $taskVoice.Speak($taskVoiceSpec.text)
} finally { $taskVoice.Dispose() }
""".replace('PAYLOAD',payload)
            command=base64.b64encode(script.encode('utf-16le')).decode()
            self.process=subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',command],
                stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**hidden_process_options())
            while True:
                try:_,error=self.process.communicate(timeout=.1);break
                except subprocess.TimeoutExpired:
                    if cancel and cancel():self.stop();raise InterruptedError()
            if self.process.returncode:raise SpeechError('media.voice_missing')
            self.process=None
        else:
            executable=shutil.which('espeak-ng') or shutil.which('espeak')
            if executable is None:raise SpeechError('media.voice_missing')
            self.process=subprocess.Popen([executable,'-v',self.language,'-w',str(path),text],**hidden_process_options())
            while self.process.poll() is None:
                if cancel and cancel():self.stop();raise InterruptedError()
                threading.Event().wait(.05)
            if self.process.returncode:raise SpeechError('media.voice_missing')
            self.process=None
        if cancel and cancel():raise InterruptedError()
        try:
            with wave.open(str(path),'rb') as stream:
                if stream.getsampwidth()!=2 or stream.getnframes()==0:raise SpeechError('media.voice_missing')
        except (OSError,wave.Error) as exc:raise SpeechError('media.voice_missing') from exc
        return path

    def speak(self,text,cache,cancel=None):
        from kivy.utils import platform
        if platform=='android':
            try:self._android().speak(text)
            except Exception as exc:
                if self.cancelled.is_set():raise InterruptedError() from exc
                raise SpeechError('media.voice_missing') from exc
            return
        path=Path(cache)/(hashlib.sha256((self.language+text).encode()).hexdigest()+'.wav')
        valid=False
        if path.exists():
            try:
                with wave.open(str(path),'rb') as stream:valid=stream.getnframes()>0 and stream.getsampwidth()==2
            except (OSError,wave.Error,EOFError):pass
        if not valid:
            pending=path.with_name(path.stem+'-'+uuid.uuid4().hex+'.part.wav')
            try:
                self.render(text,pending,cancel)
                if self.cancelled.is_set() or (cancel and cancel()):raise InterruptedError()
                pending.replace(path)
            finally:pending.unlink(missing_ok=True)
        if cancel and cancel():raise InterruptedError()
        if sys.platform=='win32':
            import winsound
            global _sound_owner
            with wave.open(str(path),'rb') as stream:duration=stream.getnframes()/stream.getframerate()
            with _sound_lock:
                if self.cancelled.is_set():raise InterruptedError()
                _sound_owner=self
                winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC)
            end=time.monotonic()+duration
            while time.monotonic()<end:
                if self.cancelled.is_set() or (cancel and cancel()) or _sound_owner is not self:raise InterruptedError()
                self.cancelled.wait(.05)
        else:
            command=shutil.which('aplay')
            if command is None:raise SpeechError('media.voice_missing')
            self.process=subprocess.Popen([command,str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.process.wait();self.process=None

    def stop(self):
        self.cancelled.set()
        if self.process is not None and self.process.poll() is None:self.process.terminate()
        if self.android is not None:self.android.stop()
        if sys.platform=='win32':
            import winsound
            global _sound_owner
            with _sound_lock:
                if _sound_owner is self:
                    _sound_owner=None;winsound.PlaySound(None,0)

    def close(self):
        self.stop()
        if self.android is not None:self.android.close()


class Narrator:
    def __init__(self,cache,language='zh-CN'):
        self.engine=None;self.language=language;self.cache=cache;self.token=None

    def speak(self,text,on_done,on_error):
        from kivy.clock import Clock
        self.stop();token=self.token=object();engine=self.engine=SpeechEngine(self.language)
        def run():
            error=None
            try:engine.speak(text,self.cache,lambda:self.token is not token)
            except Exception as exc:error=str(exc)
            finally:
                try:engine.close()
                except Exception as exc:
                    if not error:error=str(exc)
            def finish(_):
                if self.token is not token:return
                self.token=None
                if error:on_error(error)
                else:on_done()
            Clock.schedule_once(finish,0)
        threading.Thread(target=run,daemon=True).start()

    def stop(self):
        self.token=None
        if self.engine is not None:self.engine.stop()
        self.engine=None
