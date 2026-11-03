"""预热调度的懒加载与幂等性测试（不真正加载求解表）。"""

import app.warmup as w


def test_common_warmup_only_runs_common(monkeypatch):
    calls = []
    monkeypatch.setattr(w, "_warm_twophase", lambda: calls.append("common"))
    monkeypatch.setattr(w, "_warm_ref5", lambda: calls.append("ref5"))
    monkeypatch.setattr(w, "_warm_center", lambda: calls.append("center"))
    monkeypatch.setattr(w, "_common_started", False)
    monkeypatch.setattr(w, "_5x5_started", False)

    assert w.warmup_solvers() is None
    assert calls == []
    assert w.warmup_solvers() is None


def test_5x5_warmup_on_demand(monkeypatch):
    monkeypatch.delenv('ANDROID_PRIVATE',raising=False)
    calls = []
    monkeypatch.setattr(w, "_warm_twophase", lambda: calls.append("common"))
    monkeypatch.setattr(w, "_warm_ref5", lambda: calls.append("ref5"))
    monkeypatch.setattr(w, "_warm_center", lambda: calls.append("center"))
    monkeypatch.setattr(w, "_warm_solver5", lambda: None)
    monkeypatch.setattr(w, "_common_started", False)
    monkeypatch.setattr(w, "_5x5_started", False)

    thread = w.warmup_5x5()
    thread.join(5)
    assert calls == ["ref5", "center"]
    assert w.warmup_5x5() is None


def test_android_defers_5x5_warmup_until_solving(monkeypatch):
    monkeypatch.setenv('ANDROID_PRIVATE','test-private')
    monkeypatch.setattr(w,'_5x5_started',False)
    monkeypatch.setattr(w.threading,'Thread',lambda **kw:(_ for _ in ()).throw(AssertionError('Unexpected warmup')))
    assert w.warmup_5x5() is None and not w._5x5_started
