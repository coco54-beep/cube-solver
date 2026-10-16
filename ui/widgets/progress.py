"""公式学习进度的统一读写。

进度键名（"formula_progress"）之前散落在公式库 / 练习页里多处硬编码，
集中到这里，避免以后改名漏改某处。
"""

_PROGRESS_KEY = "formula_progress"


def load_learning_progress():
    from app import prefs
    from demo.learning import LearningProgress
    return LearningProgress(prefs.get(_PROGRESS_KEY, {}))


def save_learning_progress(progress):
    from app import prefs
    prefs.set(_PROGRESS_KEY, progress.records)
