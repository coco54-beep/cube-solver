"""纵向滚动列表的通用包装：容器自动按内容高度增长。

多处弹窗/页面都在重复「ScrollView + size_hint_y=None 的 BoxLayout +
bind(minimum_height=...)」。抽成一个helper，免得改一处漏一处。
"""


def wrap_scroll(inner, **scroll_kwargs):
    """给一个纵向 BoxLayout 套上 ScrollView，并接好自动高度。

    返回创建好的 ScrollView；inner 会被设为 size_hint_y=None 并绑定
    minimum_height，随后加进去。
    """
    from kivy.uix.scrollview import ScrollView
    scroll = ScrollView(**scroll_kwargs)
    inner.size_hint_y = None
    inner.bind(minimum_height=inner.setter("height"))
    scroll.add_widget(inner)
    return scroll
