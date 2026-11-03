"""Streaming video encoding and PCM alignment. No frame files or network services."""
import math,os,shutil,subprocess,sys,wave
from pathlib import Path
import numpy as np
from services.speech import hidden_process_options,SpeechEngine
from demo.media import narration,speech_language


def ffmpeg():
    path=shutil.which('ffmpeg')
    if path:return path
    raise RuntimeError('media.backend_missing')


class VideoWriter:
    def __init__(self,path,width,height,fps):
        from kivy.utils import platform
        self.native=None;self.process=None;self.log=None
        if platform=='android':
            from jnius import autoclass
            self.native=autoclass('org.cubesolver.media.VideoBridge')(str(path),width,height,fps)
        else:
            command=ffmpeg();self.log=open(str(path)+'.log','wb')
            try:self.process=subprocess.Popen([command,'-nostdin','-v','error','-y','-f','rawvideo','-pixel_format','rgba',
                '-video_size',f'{width}x{height}','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264',
                '-preset','ultrafast','-pix_fmt','yuv420p',str(path)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
                stderr=self.log,**hidden_process_options())
            except Exception:self.log.close();self.log=None;raise

    def write(self,rgba):
        if self.native:self.native.write(rgba)
        else:self.process.stdin.write(rgba)

    def finish(self):
        if self.native:self.native.finish();self.native=None
        elif self.process:
            self.process.stdin.close()
            if self.process.wait(timeout=60):raise RuntimeError('Video encoder failed')
            self.process=None
        if self.log:self.log.close();self.log=None

    def close(self):
        if self.native:self.native.close();self.native=None
        if self.process:
            if self.process.poll() is None:self.process.terminate()
            self.process.wait(timeout=10);self.process=None
        if self.log:self.log.close();self.log=None


def mux(video,audio,output,cancel=lambda:False):
    from kivy.utils import platform
    if cancel():raise InterruptedError()
    if platform=='android':
        from jnius import autoclass
        bridge=autoclass('org.cubesolver.media.VideoBridge');aac=str(output)+'.m4a'
        try:bridge.encodeAudio(str(audio),aac);bridge.mux(str(video),aac,str(output))
        finally:Path(aac).unlink(missing_ok=True)
    else:
        process=subprocess.Popen([ffmpeg(),'-nostdin','-v','error','-y','-i',str(video),'-i',str(audio),
            '-c:v','copy','-c:a','aac','-movflags','+faststart',str(output)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**hidden_process_options())
        while True:
            try:code=process.wait(timeout=.1);break
            except subprocess.TimeoutExpired:
                if cancel():process.terminate();process.wait(timeout=10);raise InterruptedError()
        if code:raise RuntimeError('Audio/video mux failed')
    if cancel():raise InterruptedError()


def prepare_narration(case,parts,folder,voice,fps,cancel,progress,engine):
    result=[]
    for i,part in enumerate(parts):
        if cancel():raise InterruptedError()
        text=narration(case,part,first=part['start']==0);path=None
        # Silent exports still leave enough time to read every caption page.
        rate=7 if speech_language(text) in ('zh-CN','ja-JP') else 16
        frames=max(fps*2,math.ceil(len(text)/rate*fps))
        if voice:
            progress(i+1,len(parts));path=Path(folder)/f'voice-{i}.wav'
            engine.render(text,path,cancel)
            with wave.open(str(path),'rb') as stream:
                frames=max(fps*2,math.ceil(stream.getnframes()/stream.getframerate()*fps))
        result.append(dict(part=part,text=text,path=path,frames=frames))
    return result


class AlignedAudio:
    """Append narration or silence to exact video frame boundaries in bounded chunks."""
    RATE=22050
    def __init__(self,path,fps):
        self.fps=fps;self.frames=0;self.samples=0
        self.stream=wave.open(str(path),'wb');self.stream.setparams((1,2,self.RATE,0,'NONE','not compressed'))

    def append(self,frames,path=None,offset=0):
        self.frames+=frames;target=round(self.frames*self.RATE/self.fps);remaining=target-self.samples
        if path:
            with wave.open(str(path),'rb') as voice:
                if voice.getsampwidth()!=2:raise RuntimeError('16-bit system speech required')
                # Utterances are bounded sections, rather than one whole-course WAV in memory.
                data=np.frombuffer(voice.readframes(voice.getnframes()),dtype='<i2').reshape(-1,voice.getnchannels()).mean(axis=1)
                count=round(len(data)*self.RATE/voice.getframerate())
                if count:
                    data=np.interp(np.arange(count)*voice.getframerate()/self.RATE,np.arange(len(data)),data)
                    start=round(offset*self.RATE)
                    pcm=np.clip(data,-32768,32767).astype('<i2')[start:start+remaining].tobytes()
                    self.stream.writeframesraw(pcm);remaining-=len(pcm)//2
        while remaining>0:
            count=min(remaining,self.RATE);self.stream.writeframesraw(b'\x00\x00'*count);remaining-=count
        self.samples=target

    def close(self):self.stream.close()


def subtitle_time(seconds):
    ms=round(seconds*1000);seconds,ms=divmod(ms,1000);minutes,seconds=divmod(seconds,60);hours,minutes=divmod(minutes,60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'
