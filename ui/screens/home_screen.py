"""首页：选择 3 阶 / 4 阶、使用说明、版本号（美观启动页式）。"""

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout

from app.config import Config


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=12, padding=[24, 24, 24, 14])

        # ---- 标题区（顶部）----
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=8)
        self.title = Label(text=Config.app_name, font_size="34sp", bold=True,
                           halign="center", valign="middle", size_hint_y=None, height=90)
        self.subtitle = Label(text="3 阶与 4 阶魔方 · 智能还原", font_size="15sp",
                              color=(0.72, 0.76, 0.85, 1), halign="center",
                              valign="middle", size_hint_y=None, height=42)
        head.add_widget(self.title)
        head.add_widget(self.subtitle)
        root.add_widget(head)

        # 弹性空白：让主选择区在竖直方向居中
        root.add_widget(BoxLayout(size_hint_y=1))

        # ---- 主选择区：3 阶 / 4 阶（大卡片按钮）----
        cols = BoxLayout(orientation="horizontal", spacing=20,
                         size_hint=(1.0, None), height=self._card_height(), padding=0)
        b3 = self._card("3", "3 阶魔方", "还原 Rubik's Cube", onClick=lambda *a: self.pick(3))
        b4 = self._card("4", "4 阶魔方", "还原 Rubik's Revenge", onClick=lambda *a: self.pick(4))
        cols.add_widget(b3)
        cols.add_widget(b4)
        root.add_widget(cols)

        # ---- 操作区 ----
        actions = BoxLayout(orientation="vertical", spacing=10,
                            size_hint=(1.0, None), height=238)
        zong = Button(text="粽子魔方 · 四角锥", font_size="17sp")
        zong.bind(on_release=lambda *a: self.pick(3, "mastermorphix"))
        demo3 = Button(text="3阶演示 · 七步法", font_size="17sp")
        demo3.bind(on_release=lambda *a: self.start_demo(3))
        demo4 = Button(text="4阶演示 · 降阶法", font_size="17sp")
        demo4.bind(on_release=lambda *a: self.start_demo(4))
        help_btn = Button(text="使用说明", font_size="17sp")
        help_btn.bind(on_release=lambda *a: self.show_help())
        actions.add_widget(zong)
        actions.add_widget(demo3)
        actions.add_widget(demo4)
        actions.add_widget(help_btn)
        root.add_widget(actions)

        # 弹性空白
        root.add_widget(BoxLayout(size_hint_y=1))

        # ---- 底部版本 ----
        bottom = AnchorLayout(size_hint_y=None, height=40)
        ver = Label(text=f"版本 {Config.app_version}", font_size="13sp",
                    color=(0.5, 0.53, 0.62, 1), halign="center", valign="middle")
        bottom.add_widget(ver)
        root.add_widget(bottom)

        self.add_widget(root)

    def _card_height(self):
        """卡片区高度，随屏幕尺寸微调（基准高屏 240，小屏略降）。"""
        from kivy.core.window import Window
        h = Window.height if Window.height else 800
        return int(max(180, min(240, h * 0.30)))

    def _card(self, big, title, desc, onClick):
        """创建一个卡片式按钮（大字标题 + 描述）。"""
        from kivy.graphics import Color, RoundedRectangle
        card = BoxLayout(orientation="vertical", spacing=2, padding=10)
        card.bind(on_touch_down=lambda instance, touch, c=card: self._on_card_touch(c, touch))
        with card.canvas.before:
            Color(0.17, 0.23, 0.34, 1)
            rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[16, 16, 16, 16])
        card.bind(pos=lambda *a: setattr(rect, "pos", card.pos),
                  size=lambda *a: setattr(rect, "size", card.size))
        # 用 size_hint 比例占满卡片，避免固定高度导致文字重叠
        big_label = Label(text=big, font_size="46sp", bold=True, halign="center",
                          valign="middle", color=(1, 1, 1, 1), size_hint_y=0.52)
        title_label = Label(text=title, font_size="19sp", bold=True, halign="center",
                            valign="middle", size_hint_y=0.26)
        desc_label = Label(text=desc, font_size="13sp", halign="center",
                           valign="middle", color=(0.8, 0.84, 0.9, 1), size_hint_y=0.22)
        card.add_widget(big_label)
        card.add_widget(title_label)
        card.add_widget(desc_label)
        card._on_click = onClick
        return card

    def _on_card_touch(self, card, touch):
        if card.collide_point(*touch.pos):
            if getattr(card, "_on_click", None):
                card._on_click()
            return True
        return False

    def pick(self, n: int, puzzle: str = "cube"):
        app = _app()
        app.new_cube(n, puzzle)
        self.manager.current = "InputScreen"

    def start_demo(self, n):
        menu = self.manager.get_screen("DemoMenuScreen")
        menu.set_mode(n)
        self.manager.current = "DemoMenuScreen"

    def show_help(self):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        body = BoxLayout(orientation="vertical", spacing=8, padding=12)
        sections = [
            ("录入", "点击对应阶进入录入页，逐格输入每个面的颜色。\n"
                     "可用「随机」快速加载一个打乱布局测试破解。"),
            ("求解", "录入完成后点「开始求解」，程序计算还原步骤。"),
            ("回放", "用 3D 视图演示还原：拖动旋转视角，滚轮/双指缩放；\n"
                     "支持上一步 / 下一步 / 自动播放 / 跳结尾。"),
        ]
        for title, text in sections:
            t = Label(text=title, font_size="17sp", bold=True,
                      halign="left", valign="middle", size_hint_y=None, height=30)
            l = Label(text=text, font_size="15sp", color=(0.85, 0.88, 0.93, 1),
                      halign="left", valign="top", size_hint_y=None, height=62)
            body.add_widget(t)
            body.add_widget(l)
        popup = Popup(title="使用说明", content=body, size_hint=(0.9, 0.7))
        # 文字换行：绑定 text_size 到各自尺寸
        for w in body.children:
            if isinstance(w, Label):
                w.bind(size=lambda ins, s: setattr(ins, "text_size", s))
        popup.open()


def _app():
    from kivy.app import App
    return App.get_running_app()
