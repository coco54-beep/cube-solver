"""Shape-and-colour cards for Tangram Extreme's traditional 3D entry page."""
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from app.i18n import tr
from cube.articulated_observation import colored_outlines_at, colored_outlines_on_ray, contains, polygon_key, centre2, tangram_panel_fits, fitting_tangram_panel, observation_body_key
from ui.widgets import metrics as m
from ui.widgets.buttons import UIButton
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.tangram_entry import TangramPanelPreview, TangramPiecePreview


class TangramShapeCards:
    PAGE_SIZE = 8

    def __init__(self, layout):
        self.layout = layout
        self.screen = layout.screen
        self.caption = Label(size_hint_y=None, height=0, font_size='12sp')
        self.gallery = GridLayout(cols=4, size_hint_y=None, height=0, spacing=m.h(5))
        self.pager = ResponsiveBoxLayout(height_px=0, gap_px=5)
        self.prev = layout.button(self.pager, 'prev', lambda: self.change_page(-1))
        self.page_label = Label(font_size='12sp')
        self.pager.add_widget(self.page_label)
        self.next = layout.button(self.pager, 'next', lambda: self.change_page(1))
        self.hint = Label(size_hint_y=None, height=0, font_size='12sp',
                          halign='center', valign='middle')
        self.hint.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        self.clear()

    def clear(self):
        self.groups = []
        self.group = None
        self.variant = self.page = 0
        self.point = self.key = None
        self.location = None
        self.state = self.gallery_stamp = None

    def selected_item(self):
        if self.key is None:return None
        face, key = self.key
        return next((p for p in self.screen._get_draft().views[face]
                     if polygon_key(p['outline']) == key), None)

    def query_point(self, point, selected=None, ray=None):
        screen = self.screen
        if not screen.entry_can_edit():return
        screen._clear_options()
        face = screen._ao_face
        self.location = (face, selected) if selected is not None else None
        items = screen._get_draft().views[face]
        item = items[selected] if selected is not None and 0 <= selected < len(items) else None
        if item is None and ray is None:
            item = next((p for p in reversed(items) if contains(p['outline'], point)), None)
        if item is None and ray is None:
            # Rendered stickers have a small inset. A tap in that seam still
            # edits the adjoining panel rather than appending a 67th panel.
            def distance(outline):
                best = float('inf')
                for a, b in zip(outline, outline[1:] + outline[:1]):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    t = max(0., min(1., ((point[0]-a[0])*dx + (point[1]-a[1])*dy) / max(dx*dx+dy*dy, 1e-12)))
                    best = min(best, (point[0]-a[0]-t*dx)**2 + (point[1]-a[1]-t*dy)**2)
                return best
            nearest = min(items, key=lambda p: distance(p['outline']), default=None)
            if nearest is not None and distance(nearest['outline']) <= .008**2:
                item = nearest
                point = centre2(item['outline'])
        self.key = (face, polygon_key(item['outline'])) if item else None
        self.point = screen._point = point

        def finish(options):
            grouped = {}
            for option in options:
                grouped.setdefault((option['color'], option['shape']), []).append(option)
            self.groups = list(grouped.values())
            self.group = None
            self.variant = 0
            if item is not None:
                for group, choices in enumerate(self.groups):
                    for variant, option in enumerate(choices):
                        if self.matches(option, item):
                            self.group, self.variant = group, variant
                            break
                    if self.group is not None:break
            self.page = self.group // self.PAGE_SIZE if self.group is not None else 0
            self.state = screen._ao_state
            self.gallery_stamp = None
            screen._message = '' if options else tr('observe.no_outline')
            screen._refresh()

        kind = screen._cube.puzzle_kind
        screen._start(lambda cancel: (colored_outlines_on_ray(kind, face, ray, cancel) if ray is not None
                                      else colored_outlines_at(kind, face, point, cancel)),
                      finish, 'observe.finding')

    def choose(self, group):
        if not self.screen.entry_can_edit():return
        if group == self.group and self.key is not None:return
        previous = self.group, self.variant
        self.group = group
        choices = self.groups[group]
        self.variant = next((i for i, option in enumerate(choices) if self.fits(option)), 0)
        if not self.commit(choices[self.variant]):
            self.group, self.variant = previous
            self.refresh()

    def rotate(self):
        if not self.screen.entry_can_edit() or self.group is None or self.key is None:return
        choices = self.groups[self.group]
        if len(choices) < 2:return
        previous = self.variant
        self.variant = next((i for step in range(1, len(choices))
                             for i in ((previous + step) % len(choices),) if self.fits(choices[i])), previous)
        if self.variant == previous:
            self.screen._message = tr('observe.shape_card_collision')
            self.screen._refresh()
        elif not self.commit(choices[self.variant]):
            self.variant = previous
            self.refresh()

    def fits(self, option):
        screen = self.screen
        old_key = self.key[1] if self.key and self.key[0] == screen._ao_face else None
        new_key = polygon_key(option['outline'])
        items = screen._get_draft().views[screen._ao_face]
        if new_key != old_key and any(polygon_key(p['outline']) == new_key for p in items):return False
        return tangram_panel_fits(screen._cube.puzzle_kind, screen._ao_face, option,
                                  items, old_key, screen._get_draft().views)

    def matches(self, option, item):
        if option['color'] != item['color'] or polygon_key(option['outline']) != polygon_key(item['outline']):return False
        return not option.get('physical') or any(polygon_key(p.world) == polygon_key(item['preview']) and
            (not item.get('body_key') or observation_body_key(self.screen._cube.puzzle_kind, p.home, p.pose) == item['body_key'])
            for p in option['panels'])

    def commit(self, option):
        screen = self.screen
        draft = screen._get_draft()
        face = screen._ao_face
        new_key = polygon_key(option['outline'])
        old_key = self.key[1] if self.key and self.key[0] == face else None
        old = self.selected_item()
        if old_key == new_key and old is not None and self.matches(option, old):
            self.gallery_stamp = None
            self.refresh()
            return True
        if any(polygon_key(p['outline']) == new_key and new_key != old_key for p in draft.views[face]):
            screen._message = tr('observe.shape_card_occupied')
            screen._refresh()
            return False
        panel = fitting_tangram_panel(screen._cube.puzzle_kind, face, option, draft.views[face], old_key, draft.views)
        if panel is None:
            screen._message = tr('observe.shape_card_collision')
            screen._refresh()
            return False
        screen._remember()
        if old_key is not None:
            draft.views[face] = [p for p in draft.views[face] if polygon_key(p['outline']) != old_key]
        draft.record(face, dict(option, panels=(panel,)), option['color'], panel.depth if option.get('physical') else None)
        if option.get('physical'):
            recorded = next(p for p in draft.views[face] if polygon_key(p['outline']) == new_key)
            recorded['world_fixed'] = True
            recorded['body_key'] = observation_body_key(screen._cube.puzzle_kind, panel.home, panel.pose)
        self.key = face, new_key
        screen._color = option['color']
        self.gallery_stamp = None
        screen._sync()
        return True

    def change_page(self, delta):
        if not self.screen.entry_can_edit():return
        pages = max(1, (len(self.groups) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = max(0, min(pages - 1, self.page + delta))
        self.refresh()

    def refresh(self):
        screen = self.screen
        extreme = screen._cube.puzzle_kind == 'tangram_extreme'
        if self.state is not screen._ao_state:
            item = self.selected_item()
            if self.key is not None and item is None:self.clear()
            elif item is not None:
                self.group = None
                for group, choices in enumerate(self.groups):
                    for variant, option in enumerate(choices):
                        if self.matches(option, item):
                            self.group, self.variant = group, variant
                            break
                    if self.group is not None:break
                if self.group is not None:self.page = self.group // self.PAGE_SIZE
            self.state = screen._ao_state
        self.caption.height = m.h(24) if extreme else 0
        self.caption.opacity = 1 if extreme else 0
        self.caption.text = tr('observe.shape_card_choose' if self.point else 'observe.shape_card_pick')
        self.hint.height = m.h(34) if extreme else 0
        self.hint.opacity = 1 if extreme else 0
        self.hint.text = tr('observe.shape_card_hint')
        if self.group is not None:
            count = len(self.groups[self.group])
            self.hint.text += ' ' + (tr('observe.shape_card_fixed_direction') if count == 1 else
                                     tr('observe.direction', n=self.variant + 1, total=count))
        for label in (self.caption, self.hint, self.page_label):label.color = App.get_running_app().theme.text
        show = extreme and bool(self.groups)
        count = min(self.PAGE_SIZE, max(0, len(self.groups)-self.page*self.PAGE_SIZE))
        self.gallery.height = m.h(138 if count > 4 else 66) if show else 0
        self.gallery.opacity = 1 if show else 0
        pages = max(1, (len(self.groups) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = max(0, min(self.page, pages - 1))
        self.pager._height_px = 30 if show and pages > 1 else 0
        self.pager.opacity = 1 if show and pages > 1 else 0
        self.pager._sync_metrics()
        self.page_label.text = f'{self.page + 1}/{pages}'
        palette = tuple(screen.view.palette)
        stamp = id(self.groups), self.group, self.variant, self.page, self.key, palette
        if stamp != self.gallery_stamp:
            self.gallery_stamp = stamp
            self.gallery.clear_widgets()
            if show:
                for index in range(self.page * self.PAGE_SIZE,
                                   min(len(self.groups), (self.page + 1) * self.PAGE_SIZE)):
                    option = self.groups[index][self.variant if index == self.group else 0]
                    button = UIButton(active=index == self.group)
                    if option.get('physical'):
                        preview = TangramPiecePreview(screen._cube.puzzle_kind, option['panels'][0], palette,
                                                       screen._ori.world, size_hint=(None, None))
                    else:
                        preview = TangramPanelPreview(option['outline'], palette[option['color']], size_hint=(None, None))
                    button.add_widget(preview)
                    button.bind(pos=lambda b, *_: setattr(b.children[0], 'pos', (b.x, b.y)),
                                size=lambda b, *_: setattr(b.children[0], 'size', b.size))
                    button.bind(on_release=lambda *_, i=index: self.choose(i))
                    self.gallery.add_widget(button)
        self.refresh_controls()

    def refresh_controls(self):
        busy = self.screen._job is not None or self.screen._busy_turn
        self.gallery.disabled = busy
        self.pager.disabled = busy or self.pager._height_px == 0
        pages = max(1, (len(self.groups) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.prev.disabled = busy or self.page == 0
        self.next.disabled = busy or self.page + 1 >= pages
        self.layout.rotate_button.disabled = busy or self.group is None or self.key is None or len(self.groups[self.group]) < 2
