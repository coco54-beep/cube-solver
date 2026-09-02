"""测试使用说明弹窗是否能正常打开。"""
import os, sys
os.environ["KIVY_NO_ARGS"] = "1"
sys.path.insert(0, r"D:\coco\cube-solver")

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen

from app.fonts import setup_cjk_font


class TestScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=20, spacing=10)
        btn = Button(text="打开使用说明", font_size="20sp", size_hint_y=None, height=60)
        btn.bind(on_release=lambda *a: self.show_help())
        root.add_widget(btn)
        self.add_widget(root)

    def show_help(self):
        from kivy.uix.popup import Popup
        body = BoxLayout(orientation="vertical", spacing=8, padding=12)
        sections = [
            ("录入", "点击对应阶进入录入页，逐格输入每个面的颜色。\n可用「随机」快速加载一个打乱布局测试破解。"),
            ("求解", "录入完成后点「开始求解」，程序计算还原步骤。"),
            ("回放", "用 3D 视图演示还原：拖动旋转视角，滚轮/双指缩放；\n支持上一步 / 下一步 / 自动播放 / 跳结尾。"),
        ]
        for title, text in sections:
            from kivy.uix.label import Label
            t = Label(text=title, font_size="17sp", bold=True,
                      halign="left", valign="middle", size_hint_y=None, height=30)
            l = Label(text=text, font_size="15sp", color=(0.85, 0.88, 0.93, 1),
                      halign="left", valign="top", size_hint_y=None, height=62)
            body.add_widget(t)
            body.add_widget(l)
        popup = Popup(title="使用说明", content=body, size_hint=(0.9, 0.7))
        for w in body.children:
            if isinstance(w, Label):
                w.bind(size=lambda ins, s: setattr(ins, "text_size", s))
        popup.open()


class TestApp(App):
    def build(self):
        setup_cjk_font()
        from kivy.lang import Builder
        kv_path = os.path.join(os.path.dirname(__file__), "ui", "kv", "app.kv")
        Builder.load_file(kv_path)
        sm = ScreenManager()
        scr = TestScreen(name="test")
        sm.add_widget(scr)
        return sm


if __name__ == "__main__":
    TestApp().run()
