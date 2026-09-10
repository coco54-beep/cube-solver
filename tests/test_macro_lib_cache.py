"""macro_lib 宏库结构与磁盘缓存回归。

宏库在导入时构建（约 6.8s，10 万次 compute_effect），因此加了版本化磁盘缓存。
本测试不依赖 Kivy；只验证缓存读写不改变库内容，且结构不变量成立。
"""
import os
import pickle

from solver.reduction.ref5 import macro_lib as ml


def test_reachable_structure():
    assert ml.BASE_MIDDLE_3CYCLES
    assert ml.REACHABLE
    for combo, arr in ml.REACHABLE.items():
        assert len(combo) == 3
        assert arr, "每个可达槽组合至少有一个宏"
        for seq, cyc, rev in arr:
            assert seq
            assert frozenset(cyc) == combo
            assert isinstance(rev, bool)


def test_cache_roundtrip_matches_module(tmp_path, monkeypatch):
    """把当前库写入缓存文件后，_load_or_build 读出的内容应与内存中一致。"""
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ANDROID_PRIVATE", raising=False)
    monkeypatch.delenv("ANDROID_APP_PATH", raising=False)

    path = ml._cache_path()
    assert path is not None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump({"key": ml._CACHE_KEY,
                     "base": ml.BASE_MIDDLE_3CYCLES,
                     "reachable": ml.REACHABLE}, f)

    base, reachable = ml._load_or_build()
    assert base == ml.BASE_MIDDLE_3CYCLES
    assert reachable == ml.REACHABLE
