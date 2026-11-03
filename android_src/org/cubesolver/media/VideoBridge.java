package org.cubesolver.media;

import android.media.Image;
import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.media.MediaMuxer;
import java.io.FileInputStream;
import java.io.OutputStream;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;

/** Streaming native H.264/AAC encoding; never stores the movie in RAM. */
public final class VideoBridge {
    private MediaCodec codec;
    private MediaMuxer muxer;
    private final MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();
    private final int width,height,fps;
    private int track=-1,frame;
    private boolean started;

    public VideoBridge(String path,int width,int height,int fps) throws Exception {
        this.width=width;this.height=height;this.fps=fps;
        try {
            codec=MediaCodec.createEncoderByType("video/avc");
            MediaFormat format=MediaFormat.createVideoFormat("video/avc",width,height);
            format.setInteger(MediaFormat.KEY_COLOR_FORMAT,MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible);
            format.setInteger(MediaFormat.KEY_BIT_RATE,1500000);
            format.setInteger(MediaFormat.KEY_FRAME_RATE,fps);
            format.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL,2);
            codec.configure(format,null,null,MediaCodec.CONFIGURE_FLAG_ENCODE);
            muxer=new MediaMuxer(path,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);codec.start();
        } catch(Exception failure) {close();throw failure;}
    }
    private boolean drain(boolean end) throws Exception {
        int waits=0;
        while (true) {
            int index=codec.dequeueOutputBuffer(info,end?10000:0);
            if (index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                track=muxer.addTrack(codec.getOutputFormat());muxer.start();started=true;
            } else if (index>=0) {
                if ((info.flags&MediaCodec.BUFFER_FLAG_CODEC_CONFIG)!=0) info.size=0;
                if (info.size>0) {
                    if (!started) throw new Exception("Encoder format is unavailable");
                    ByteBuffer buffer=codec.getOutputBuffer(index);
                    buffer.position(info.offset);buffer.limit(info.offset+info.size);
                    muxer.writeSampleData(track,buffer,info);
                }
                boolean done=(info.flags&MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;
                codec.releaseOutputBuffer(index,false);
                if (done) return true;
            } else if (!end) return false;
            else if (++waits>1000) throw new Exception("Video encoder timed out");
        }
    }
    private static void put(Image.Plane plane,int x,int y,int value) {
        plane.getBuffer().put(y*plane.getRowStride()+x*plane.getPixelStride(),(byte)Math.max(0,Math.min(255,value)));
    }
    public void write(byte[] rgba) throws Exception {
        if (rgba.length!=width*height*4) throw new Exception("Frame size mismatch");
        int index;int waits=0;
        while ((index=codec.dequeueInputBuffer(10000))<0) {
            drain(false);if (++waits>1000) throw new Exception("Video encoder stalled");
        }
        Image image=codec.getInputImage(index);
        if (image==null) throw new Exception("Flexible video input is unavailable");
        Image.Plane[] planes=image.getPlanes();
        for (int y=0;y<height;y+=2) for (int x=0;x<width;x+=2) {
            int rs=0,gs=0,bs=0;
            for (int dy=0;dy<2;dy++) for (int dx=0;dx<2;dx++) {
                int offset=((y+dy)*width+x+dx)*4;
                int r=rgba[offset]&255,g=rgba[offset+1]&255,b=rgba[offset+2]&255;
                put(planes[0],x+dx,y+dy,16+((66*r+129*g+25*b+128)>>8));
                rs+=r;gs+=g;bs+=b;
            }
            int r=rs/4,g=gs/4,b=bs/4;
            put(planes[1],x/2,y/2,128+((-38*r-74*g+112*b+128)>>8));
            put(planes[2],x/2,y/2,128+((112*r-94*g-18*b+128)>>8));
        }
        codec.queueInputBuffer(index,0,width*height*3/2,(long)frame++*1000000/fps,0);drain(false);
    }
    public void finish() throws Exception {
        int index;int waits=0;
        while ((index=codec.dequeueInputBuffer(10000))<0) {
            drain(false);if (++waits>1000) throw new Exception("Video encoder stalled");
        }
        codec.queueInputBuffer(index,0,0,(long)frame*1000000/fps,MediaCodec.BUFFER_FLAG_END_OF_STREAM);
        drain(true);close();
    }
    public void close() {
        if (codec!=null) {try {codec.stop();}catch(Exception ignored){} codec.release();codec=null;}
        if (muxer!=null) {try {if(started)muxer.stop();}catch(Exception ignored){} muxer.release();muxer=null;}
    }
    private static int le16(RandomAccessFile f) throws Exception {return f.readUnsignedByte()|(f.readUnsignedByte()<<8);}
    private static long le32(RandomAccessFile f) throws Exception {return (long)le16(f)|((long)le16(f)<<16);}
    private static String tag(RandomAccessFile f) throws Exception {byte[] b=new byte[4];f.readFully(b);return new String(b,"US-ASCII");}
    public static void encodeAudio(String wav,String output) throws Exception {
        RandomAccessFile file=new RandomAccessFile(wav,"r");MediaCodec audio=null;MediaMuxer mux=null;
        boolean begun=false;
        try {
            if (!tag(file).equals("RIFF")) throw new Exception("Not a WAV file");
            le32(file);if(!tag(file).equals("WAVE"))throw new Exception("Not PCM WAV");
            int channels=0,rate=0,bits=0;long remaining=0;
            while(file.getFilePointer()+8<=file.length()) {
                String name=tag(file);long size=le32(file),next=file.getFilePointer()+size+(size&1);
                if(name.equals("fmt ")) {
                    if(le16(file)!=1)throw new Exception("PCM audio required");
                    channels=le16(file);rate=(int)le32(file);le32(file);le16(file);bits=le16(file);
                } else if(name.equals("data")) {remaining=size;break;}
                file.seek(next);
            }
            if(channels<1||rate<1||bits!=16)throw new Exception("16-bit PCM required");
            audio=MediaCodec.createEncoderByType("audio/mp4a-latm");
            MediaFormat format=MediaFormat.createAudioFormat("audio/mp4a-latm",rate,channels);
            format.setInteger(MediaFormat.KEY_AAC_PROFILE,MediaCodecInfo.CodecProfileLevel.AACObjectLC);
            format.setInteger(MediaFormat.KEY_BIT_RATE,channels*64000);
            audio.configure(format,null,null,MediaCodec.CONFIGURE_FLAG_ENCODE);audio.start();
            mux=new MediaMuxer(output,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
            MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();int track=-1;long consumed=0;
            boolean inputEnd=false,outputEnd=false;int waits=0;
            while(!outputEnd) {
                if(!inputEnd) {
                    int index=audio.dequeueInputBuffer(10000);
                    if(index>=0) {
                        ByteBuffer buffer=audio.getInputBuffer(index);buffer.clear();
                        int count=(int)Math.min(remaining,buffer.remaining());count-=count%(channels*2);
                        byte[] data=new byte[count];file.readFully(data);buffer.put(data);
                        long pts=consumed*1000000/(rate*channels*2L);consumed+=count;remaining-=count;
                        inputEnd=count==0;
                        audio.queueInputBuffer(index,0,count,pts,inputEnd?MediaCodec.BUFFER_FLAG_END_OF_STREAM:0);
                    }
                }
                int index=audio.dequeueOutputBuffer(info,10000);
                if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {track=mux.addTrack(audio.getOutputFormat());mux.start();begun=true;}
                else if(index>=0) {
                    if(info.size>0&&(info.flags&MediaCodec.BUFFER_FLAG_CODEC_CONFIG)==0) {
                        ByteBuffer buffer=audio.getOutputBuffer(index);buffer.position(info.offset);buffer.limit(info.offset+info.size);
                        mux.writeSampleData(track,buffer,info);
                    }
                    outputEnd=(info.flags&MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;audio.releaseOutputBuffer(index,false);waits=0;
                } else if(++waits>3000)throw new Exception("Audio encoder timed out");
            }
        } finally {
            file.close();if(audio!=null){try{audio.stop();}catch(Exception ignored){}audio.release();}
            if(mux!=null){try{if(begun)mux.stop();}catch(Exception ignored){}mux.release();}
        }
    }
    public static void mux(String video,String audio,String output) throws Exception {
        MediaMuxer mux=new MediaMuxer(output,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
        MediaExtractor[] inputs={new MediaExtractor(),new MediaExtractor()};boolean started=false;
        try {
            inputs[0].setDataSource(video);inputs[1].setDataSource(audio);
            int[] tracks=new int[2];
            for(int i=0;i<2;i++){inputs[i].selectTrack(0);tracks[i]=mux.addTrack(inputs[i].getTrackFormat(0));}
            mux.start();started=true;ByteBuffer buffer=ByteBuffer.allocateDirect(4*1024*1024);
            MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();
            for(int i=0;i<2;i++) while(true) {
                buffer.clear();int size=inputs[i].readSampleData(buffer,0);if(size<0)break;
                info.set(0,size,inputs[i].getSampleTime(),inputs[i].getSampleFlags());
                mux.writeSampleData(tracks[i],buffer,info);inputs[i].advance();
            }
        } finally {for(MediaExtractor input:inputs)input.release();if(started)mux.stop();mux.release();}
    }
    public static void copyToUri(android.app.Activity activity,String input,String uri) throws Exception {
        try(FileInputStream stream=new FileInputStream(input);
            OutputStream output=activity.getContentResolver().openOutputStream(android.net.Uri.parse(uri))) {
            byte[] buffer=new byte[65536];int count;
            while((count=stream.read(buffer))>=0)output.write(buffer,0,count);
        }
    }
}
