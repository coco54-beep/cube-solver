"""主题化 Popup 辅助。

Kivy 默认 Popup 的背景是深色贴图，浅色主题下 `app.theme.text`（深色）会与
深色底撞色、文字看不清。这里把背景替换为主题 surface 色，使浅/深主题都清晰。
"""

from kivy.graphics import Color, Rectangle


def theme_popup(popup, theme):
    """把 Popup 背景替换为 theme.surface（去掉默认深色底图）。返回 popup。

    注意：仅把 background 置空会让 Popup 底成一块纯白，深色模式下与浅色文字撞色。
    必须同时把 background_color 设为主题 surface（空贴图=纯白，乘上 surface 即得主题底色）。
    """
    try:
        popup.background = ""
    except Exception:
        pass
    popup.background_color = theme.surface
    with popup.canvas.before:
        popup._theme_bg_color = Color(*theme.surface)
        popup._theme_bg_rect = Rectangle(pos=popup.pos, size=popup.size)

    def _sync(*_a):
        popup._theme_bg_rect.pos = popup.pos
        popup._theme_bg_rect.size = popup.size

    popup.bind(pos=_sync, size=_sync)

    def _on_palette(*_a):
        popup.background_color = theme.surface

    theme.bind(on_palette=_on_palette)
    popup.bind(on_dismiss=lambda *_a: theme.unbind(on_palette=_on_palette))
    # A confirmation belongs to the page that opened it. A completed worker
    # or navigation event must not leave old destructive actions over a new page.
    from kivy.app import App
    app=App.get_running_app()
    manager=getattr(app,'root',None)
    if manager is not None and hasattr(manager,'current'):
        source=manager.current
        def _page_changed(_manager,current):
            if current!=source:popup.dismiss()
        manager.bind(current=_page_changed)
        popup.bind(on_dismiss=lambda *_:manager.unbind(current=_page_changed))
    return popup
