"""Immediate feedback stays local, permits edits and clears correctly on undo."""
from copy import deepcopy
import mmap
from types import SimpleNamespace
import pytest
from cube.entry_checks import FaceletChecks
from tests.test_input_cache_restore import editor


def blank(n=3):return {f:[['']*n for _ in range(n)] for f in 'UDFBRL'}


def test_adjacent_face_edits_recheck_only_the_affected_piece():
    from cube.coordinates import rc_from_pos
    data=blank();check=FaceletChecks(3);check.update(data)
    f,r,c=check.pieces[(1,1,1)][0];data[f][r][c]='W';check.update(data)
    assert check.checked==1
    f,r,c=check.pieces[(1,1,1)][1];data[f][r][c]='W'
    issues=check.update(data);assert issues[0][0]=='entry.preview_repeat' and check.checked==1
    data[f][r][c]='Y';assert check.update(data)[0][0]=='entry.preview_opposite'
    data[f][r][c]='R';assert check.update(data)==[]
    check.update(data);assert check.checked==0


def test_colour_overflow_clears_when_an_entry_is_erased():
    data=blank(2);check=FaceletChecks(2)
    for f in ('U','D'):
        for row in data[f]:row[:]=['W','W']
    assert any(k=='entry.preview_count' for k,_,_ in check.update(data))
    data['D']=[['',''],['','']]
    assert not any(k=='entry.preview_count' for k,_,_ in check.update(data))


def test_four_by_four_joint_table_is_shared_and_read_only(tmp_path,monkeypatch):
    from solver.reduction import center_solver as module
    monkeypatch.setattr(module,'JOINT_STATE_COUNT',8);monkeypatch.setattr(module,'_JOINT_DIST_CACHE',{})
    path=tmp_path/'joint.bin';path.write_bytes(bytes(range(8)))
    target=SimpleNamespace(joint_dist_path=str(path))
    a=module.CenterSolver4._try_load_joint_dist(target)
    b=module.CenterSolver4._try_load_joint_dist(target)
    assert isinstance(a,mmap.mmap) and b is a and a[7]==7
    with pytest.raises(TypeError):a[0]=1
    module._JOINT_DIST_CACHE.clear();assert a[3]==3
    a.close()


def test_distribution_assets_still_include_active_tables():
    from scripts.bundle_assets import audit,windows_assets
    result=audit();assert result['excluded_bytes']>100_000_000
    assert not any('docs' in p.parts or p.name=='demo.gif' for p in windows_assets())


def test_real_input_local_feedback_is_cleared_by_undo(editor):
    from cube.coordinates import rc_from_pos
    screen,app=editor;screen.on_enter()
    r,c=rc_from_pos(3,'F',(1,1,1));screen._fill_cell('F',r,c,'W')
    screen._ori.turn_next();screen._refresh_view()
    r,c=rc_from_pos(3,'R',(1,1,1));screen._fill_cell('R',r,c,'W')
    assert screen._local_issues and '重复颜色' in screen.msg.text
    screen.undo();assert not screen._local_issues
