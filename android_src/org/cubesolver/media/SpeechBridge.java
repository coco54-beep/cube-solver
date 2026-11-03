package org.cubesolver.media;

import android.app.Activity;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import java.io.File;
import java.util.Locale;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** System TTS only. Blocking operations are invoked from a Python worker. */
public final class SpeechBridge {
    private TextToSpeech engine;
    private final CountDownLatch ready = new CountDownLatch(1);
    private volatile CountDownLatch completion;
    private volatile boolean cancelled, failed;
    private int status = TextToSpeech.ERROR;
    private String language;
    private volatile String utterance;

    public static SpeechBridge create(Activity activity, String language) {
        SpeechBridge bridge = new SpeechBridge(); bridge.language = language;
        activity.runOnUiThread(() -> {
            bridge.engine = new TextToSpeech(activity, value -> {
                bridge.status = value; bridge.ready.countDown();
            });
            if (bridge.cancelled) bridge.engine.shutdown();
        });
        return bridge;
    }
    private void initialize() throws Exception {
        if (!ready.await(15, TimeUnit.SECONDS) || status != TextToSpeech.SUCCESS)
            throw new Exception("media.voice_missing");
        if (cancelled) throw new InterruptedException();
        if (engine.setLanguage(Locale.forLanguageTag(language)) < 0)
            throw new Exception("media.voice_missing");
        engine.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            public void onStart(String id) {}
            public void onDone(String id) { if (id.equals(utterance) && completion != null) completion.countDown(); }
            public void onError(String id) { if(id.equals(utterance)){ failed = true; if (completion != null) completion.countDown(); } }
            public void onStop(String id, boolean interrupted) { if(id.equals(utterance)){ failed = true; if (completion != null) completion.countDown(); } }
        });
    }
    private void await() throws Exception {
        for (int i=0; i<180; i++) {
            if (cancelled) throw new InterruptedException();
            if (completion.await(1, TimeUnit.SECONDS)) {
                if (failed) throw new Exception("media.voice_missing");
                return;
            }
        }
        engine.stop(); throw new Exception("media.voice_missing");
    }
    public void render(String text, String path) throws Exception {
        initialize(); failed=false; completion=new CountDownLatch(1);utterance=java.util.UUID.randomUUID().toString();
        if (engine.synthesizeToFile(text, new Bundle(), new File(path), utterance) != TextToSpeech.SUCCESS)
            throw new Exception("media.voice_missing");
        await();
    }
    public void speak(String text) throws Exception {
        initialize(); failed=false; completion=new CountDownLatch(1);utterance=java.util.UUID.randomUUID().toString();
        if (engine.speak(text, TextToSpeech.QUEUE_FLUSH, new Bundle(), utterance) != TextToSpeech.SUCCESS)
            throw new Exception("media.voice_missing");
        await();
    }
    public void stop() {
        cancelled=true;
        ready.countDown();
        if (engine != null) engine.stop();
        if (completion != null) completion.countDown();
    }
    public void close() { stop(); if(engine!=null)engine.shutdown(); }
}
