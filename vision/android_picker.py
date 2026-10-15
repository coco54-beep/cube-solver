"""Android 系统图片选择器，使用所选 URI 的临时读取权限，不扫描共享存储。"""
import os
from threading import Thread


class AndroidPhotoPicker:
    REQUEST_CODE = 0x4355

    def __init__(self, cache_dir, on_result):
        self.cache_dir = cache_dir
        self.on_result = on_result
        self._bound = False
        self._busy = False

    def open(self):
        from android import activity
        from android.runnable import run_on_ui_thread
        from jnius import autoclass
        self._busy = True
        activity.bind(on_activity_result=self._result)
        self._bound = True

        @run_on_ui_thread
        def launch():
            Intent = autoclass('android.content.Intent')
            Build = autoclass('android.os.Build$VERSION')
            current = autoclass('org.kivy.android.PythonActivity').mActivity
            try:
                if Build.SDK_INT >= 33:
                    try:
                        intent = Intent('android.provider.action.PICK_IMAGES')
                        intent.setType('image/*')
                        current.startActivityForResult(intent, self.REQUEST_CODE)
                        return
                    except Exception:
                        pass
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.setType('image/*')
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                current.startActivityForResult(intent, self.REQUEST_CODE)
            except Exception as exc:
                self._deliver(None, str(exc))
        launch()

    def _unbind(self):
        if self._bound:
            from android import activity
            activity.unbind(on_activity_result=self._result)
            self._bound = False

    def _result(self, request_code, result_code, intent):
        if request_code != self.REQUEST_CODE or not self._busy:
            return
        self._unbind()
        if result_code != -1 or intent is None or intent.getData() is None:
            self._deliver(None, None)
            return
        # 将 Java 引用转成稳定的 URI 文本，再到工作线程解码。
        uri = str(intent.getData().toString())
        Thread(target=self._decode, args=(uri,), daemon=True).start()

    def _decode(self, uri_text):
        try:
            path = decode_android_image(uri_text, self.cache_dir)
            self._deliver(path, None)
        except Exception as exc:
            self._deliver(None, str(exc))

    def _deliver(self, path, error):
        from kivy.clock import Clock
        def finish(_dt):
            if not self._busy:
                return
            self._busy = False
            self._unbind()
            self.on_result(path, error)
        Clock.schedule_once(finish, 0)


def decode_android_image(uri_text, cache_dir, max_side=1600):
    """用系统解码 JPEG/PNG/HEIC，并输出已校正 EXIF 方向的私有 PNG。"""
    from jnius import autoclass, PythonJavaClass, java_method
    Uri = autoclass('android.net.Uri')
    Version = autoclass('android.os.Build$VERSION')
    Bitmap = autoclass('android.graphics.Bitmap')
    current = autoclass('org.kivy.android.PythonActivity').mActivity
    resolver = current.getContentResolver()
    uri = Uri.parse(uri_text)
    bitmap = None
    output = None
    try:
        if Version.SDK_INT >= 28:
            Decoder = autoclass('android.graphics.ImageDecoder')
            class Header(PythonJavaClass):
                __javainterfaces__ = ['android/graphics/ImageDecoder$OnHeaderDecodedListener']
                __javacontext__ = 'app'

                @java_method('(Landroid/graphics/ImageDecoder;Landroid/graphics/ImageDecoder$ImageInfo;Landroid/graphics/ImageDecoder$Source;)V')
                def onHeaderDecoded(self, decoder, info, source):
                    size = info.getSize()
                    w, h = size.getWidth(), size.getHeight()
                    ratio = min(1., max_side/max(w, h))
                    decoder.setAllocator(1)  # ALLOCATOR_SOFTWARE
                    decoder.setTargetSize(max(1, round(w*ratio)), max(1, round(h*ratio)))
            header = Header()
            bitmap = Decoder.decodeBitmap(Decoder.createSource(resolver, uri), header)
        else:
            Factory = autoclass('android.graphics.BitmapFactory')
            Options = autoclass('android.graphics.BitmapFactory$Options')
            options = Options()
            options.inJustDecodeBounds = True
            stream = resolver.openInputStream(uri)
            try:
                Factory.decodeStream(stream, None, options)
            finally:
                stream.close()
            sample = 1
            while max(options.outWidth, options.outHeight)/sample > max_side:
                sample *= 2
            options.inJustDecodeBounds = False
            options.inSampleSize = sample
            stream = resolver.openInputStream(uri)
            try:
                bitmap = Factory.decodeStream(stream, None, options)
            finally:
                stream.close()
            if bitmap is not None:
                stream = resolver.openInputStream(uri)
                try:
                    Exif = autoclass('android.media.ExifInterface')
                    orientation = Exif(stream).getAttributeInt('Orientation', 1)
                finally:
                    stream.close()
                matrix = autoclass('android.graphics.Matrix')()
                turns = {3: 180, 5: 90, 6: 90, 7: 270, 8: 270}
                matrix.setRotate(turns.get(orientation, 0))
                if orientation in (2, 4, 5, 7):
                    matrix.postScale(-1. if orientation != 4 else 1., -1. if orientation == 4 else 1.)
                if orientation != 1:
                    rotated = Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), matrix, True)
                    if rotated != bitmap:
                        bitmap.recycle()
                    bitmap = rotated
        if bitmap is None:
            raise ValueError('Image could not be decoded')
        os.makedirs(cache_dir, exist_ok=True)
        path = os.path.join(cache_dir, 'selected-photo.png')
        output = autoclass('java.io.FileOutputStream')(path)
        fmt = autoclass('android.graphics.Bitmap$CompressFormat').PNG
        if not bitmap.compress(fmt, 100, output):
            raise ValueError('Image could not be saved')
        return path
    finally:
        if output is not None:
            output.close()
        if bitmap is not None:
            bitmap.recycle()
