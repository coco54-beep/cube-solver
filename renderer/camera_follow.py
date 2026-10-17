"""Bring an obscured turn into view before the layer animation starts."""
import math
import weakref

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, BooleanProperty

from app.prefs import get, set as save
from cube.polyhedral import dot, mean, unit

DEFAULT_RATE = 180
MIN_RATE = 30
MAX_RATE = 360


class CameraFollowSettings(EventDispatcher):
    """One persisted rate shared by every turn and playback control; zero is off."""
    rate = NumericProperty(DEFAULT_RATE)
    locked = BooleanProperty(False)

    def __init__(self):
        value = get('camera_follow_rate', DEFAULT_RATE)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            value = DEFAULT_RATE
        enabled = get('camera_follow_enabled', True) is True
        locked = get('camera_view_locked', False) is True
        super().__init__(rate=max(MIN_RATE, min(MAX_RATE, value)) if enabled and value>0 and not locked else 0,
                         locked=locked)
        self.bind(rate=self._save)
        self.bind(locked=self._lock_changed)

    def _save(self, _instance, rate):
        if rate>0 and self.locked:
            self.locked=False
            return  # The lock handler persists the complete new mode.
        save('camera_follow_enabled', rate > 0)
        save('camera_follow_rate', rate)

    def _lock_changed(self,_instance,locked):
        save('camera_view_locked',locked)
        if locked and self.rate!=0:
            self.rate=0
        else:
            save('camera_follow_enabled',self.rate>0)
            save('camera_follow_rate',self.rate)


FOLLOW_SETTINGS = CameraFollowSettings()


class _ViewSettings:
    """Weak subscriptions survive as long as their view, including replacements."""
    def __init__(self,view,on_change=None):
        self.view=weakref.ref(view)
        self.on_change=weakref.WeakMethod(on_change) if on_change is not None else None
        FOLLOW_SETTINGS.bind(locked=self.sync)
        self.sync(FOLLOW_SETTINGS,FOLLOW_SETTINGS.locked)

    def sync(self,_settings,locked):
        view=self.view()
        if view is None:
            return
        if hasattr(view,'cancel_touch'):
            view.cancel_touch()
        view.lock_rotation=locked
        if hasattr(view,'lock_view'):
            view.lock_view=locked
        callback=self.on_change() if self.on_change is not None else None
        if callback is not None:
            callback(locked)


def bind_camera_settings(view,on_change=None):
    previous=getattr(view,'_view_settings',None)
    if previous is not None:
        FOLLOW_SETTINGS.unbind(locked=previous.sync)
    view._view_settings=_ViewSettings(view,on_change)


def reset_camera_view(view):
    """Reset only the angle; never interrupt a pending turn or change modes."""
    if (getattr(view,'_camera_follow_active',False) or
            getattr(view,'_move',None) is not None or getattr(view,'camera_busy',False)):
        return False
    if hasattr(view,'cancel_touch'):
        view.cancel_touch()
    view.reset_camera()
    return True


def preferences():
    rate = FOLLOW_SETTINGS.rate
    return rate > 0 and not FOLLOW_SETTINGS.locked, max(MIN_RATE, min(MAX_RATE, rate))


def polyhedral_target(cube, move):
    if getattr(move, 'rotation_axis', None) is not None:
        return (0., 0., 0.)
    g = cube.geometry
    # 魔塔是四面体、绕角转：转动层质心方向就是"正在转的那个角"，正对上去会被
    # 近处的曲面挡住。改为对准"另一个角"（相邻角之一），动画就看得见。
    # 仅改魔塔，其它魔方不动。
    if getattr(cube, 'puzzle_kind', None) == 'moyu':
        normals = g.spec.normals
        return unit(tuple(normals[(move.axis + 1) % len(normals)]))
    return mean(tuple(g.centres[p] for p in g.layers[move.axis][move.layer]))


def layer_target(axis, layers):
    position = sum(layers) / len(layers)
    return tuple(position if i == axis else 0. for i in range(3))


def square1_target(move):
    if move.axis<2:
        return (0.,1. if move.axis==0 else -1.,0.)
    # The slice moves the half centred opposite the SQ1's diagonal spindle.
    return (-math.sin(math.radians(75)),0.,-math.cos(math.radians(75)))


def cancel_follow(view):
    event = getattr(view, '_camera_follow_event', None)
    if event is not None:
        event.cancel()
    view._camera_follow_event = None
    view._camera_follow_active = False
    if hasattr(view, 'camera_busy'):
        view.camera_busy = False


def follow_turn(view, target, on_ready):
    """Only move the camera when the selected turn points away from it.

    This changes display angles, never piece positions or entered colours.
    Centre slices with no preferred side keep the existing camera direction.
    """
    cancel_follow(view)
    enabled, rate = preferences()
    if not enabled or dot(target, target) < 1e-12:
        on_ready()
        return
    world = (view.observation_world() if hasattr(view, 'observation_world')
             else getattr(view, '_whole_world', None))
    if world is not None:
        target = world.transform(*target)
    target = unit(target)
    camera = getattr(view, 'camera', None)
    yaw = camera.azimuth if camera is not None else view.yaw
    pitch = camera.elevation if camera is not None else view.pitch
    yr, pr = math.radians(yaw), math.radians(pitch)
    eye = (math.sin(yr)*math.cos(pr), math.sin(pr), math.cos(yr)*math.cos(pr))
    if dot(target, eye) >= .35:
        on_ready()
        return
    if hasattr(view,'cancel_touch'):
        view.cancel_touch()
    elif getattr(view,'_touch0',None) is not None:
        view._touch0.ungrab(view)
        view._touch0=None
    # Retain a slight oblique view instead of flattening a face head-on.
    target = unit(tuple(.9*t + .1*e for t, e in zip(target, eye)))
    target_pitch = max(-75., min(75., math.degrees(
        math.atan2(target[1], math.hypot(target[0], target[2])))))
    target_yaw = math.degrees(math.atan2(target[0], target[2]))
    yaw_delta = (target_yaw-yaw+180.) % 360.-180.
    pitch_delta = target_pitch-pitch
    duration = max(.12, math.hypot(yaw_delta, pitch_delta)/rate)
    view._camera_follow_active = True
    if hasattr(view, 'camera_busy'):
        view.camera_busy = True
    elapsed = 0.

    def finish():
        view._camera_follow_event = None
        view._camera_follow_active = False
        if hasattr(view, 'camera_busy'):
            view.camera_busy = False
        on_ready()
        return False

    def tick(dt):
        nonlocal elapsed
        enabled, current_rate = preferences()
        if not enabled:
            # Continue the pending turn from the current view when switched off.
            return finish()
        elapsed += max(0., dt)*current_rate/rate
        fraction = min(1., elapsed/duration)
        eased = fraction*fraction*(3.-2.*fraction)
        if camera is not None:
            camera.azimuth = yaw+yaw_delta*eased
            camera.elevation = pitch+pitch_delta*eased
            view._redraw()
        else:
            view.yaw = yaw+yaw_delta*eased
            view.pitch = pitch+pitch_delta*eased
            view.refresh()
        if fraction >= 1.:
            return finish()
    g = getattr(getattr(view, 'cube', None), 'geometry', None)
    interval = 1/12 if g is not None and len(g.stickers) >= 600 else 1/24
    view._camera_follow_event = Clock.schedule_interval(tick, interval)
