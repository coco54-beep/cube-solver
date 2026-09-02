"""应用配置（可扩展为用户偏好）。"""

from app.constants import APP_NAME, APP_VERSION


class Config:
    app_name = APP_NAME
    app_version = APP_VERSION

    # 3D 视图默认视角（球坐标：仰角 / 方位角）
    default_elevation = 22.0
    default_azimuth = 35.0
    default_distance = 9.0

    # 转动动画
    turn_duration = 0.35
    auto_play_speed = 1.0

    # 求解线程
    solve_timeout_s = 120
