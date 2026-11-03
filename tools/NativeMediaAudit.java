package org.cubesolver.media;
import java.io.RandomAccessFile;

/** Runs with app_process on the emulator; no APK build or installation. */
public final class NativeMediaAudit {
    private static void le16(RandomAccessFile f,int n)throws Exception{f.write(n&255);f.write((n>>8)&255);}
    private static void le32(RandomAccessFile f,int n)throws Exception{le16(f,n);le16(f,n>>16);}
    public static void main(String[] args)throws Exception{
        String base=args[0];int width=480,height=640,frames=24,fps=12;
        VideoBridge video=new VideoBridge(base+"-silent.mp4",width,height,fps);
        try {
            byte[] rgba=new byte[width*height*4];
            for(int frame=0;frame<frames;frame++){
                for(int y=0;y<height;y++)for(int x=0;x<width;x++){
                    int i=(y*width+x)*4;rgba[i]=(byte)(x<width/2?220:10);
                    rgba[i+1]=(byte)(y<height/2?180:20);rgba[i+2]=(byte)(frame*8);rgba[i+3]=(byte)255;
                }
                video.write(rgba);
            }
            video.finish();
        } finally{video.close();}
        int samples=44100;
        try(RandomAccessFile wav=new RandomAccessFile(base+".wav","rw")){
            wav.setLength(0);wav.writeBytes("RIFF");le32(wav,36+samples*2);wav.writeBytes("WAVEfmt ");
            le32(wav,16);le16(wav,1);le16(wav,1);le32(wav,22050);le32(wav,44100);le16(wav,2);le16(wav,16);
            wav.writeBytes("data");le32(wav,samples*2);
            for(int i=0;i<samples;i++)le16(wav,(int)(Math.sin(i*2*Math.PI*440/22050)*8000));
        }
        VideoBridge.encodeAudio(base+".wav",base+".m4a");
        VideoBridge.mux(base+"-silent.mp4",base+".m4a",base+".mp4");
        System.out.println("NATIVE_MEDIA_PASS");
    }
}
