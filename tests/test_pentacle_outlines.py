"""Tessellation must never become a physical cut in the star-cube display."""
from cube.pentacle import PentacleCube,shell
from cube.polyhedral import Move,CUBE


def test_outside_panels_have_only_union_boundaries():
    from renderer.pentacle_view import _panel_outlines
    panels,_,_=shell();outlines=_panel_outlines()
    grouped=[i for i,p in enumerate(panels) if len(p.patches)>1]
    assert grouped
    assert all(len(outlines[i])<sum(len(poly) for poly in panels[i].patches) for i in grouped)


def test_disc_has_central_pentagon_and_ten_surrounding_regions():
    from renderer.pentacle_view import _panel_outlines
    panels,_,discs=shell()
    for face in range(6):
        circle=[i for i,p in enumerate(panels) if p.face==face and p.home in discs]
        assert len(circle)==11
        # Petal arc tessellation can also produce five boundary segments.
        # The centre is the unique polygon entirely inside the circular rim.
        import math
        from cube.polyhedral import dot
        from cube.pentacle import RADIUS
        centres=[i for i in circle if all(math.sqrt(sum((v[a]-CUBE[face][a])**2 for a in range(3)))<RADIUS-1e-6
                                         for patch in panels[i].patches for v in patch)]
        assert len(centres)==1 and len(_panel_outlines()[centres[0]])==5


def test_display_boundary_does_not_change_legality_or_physical_state():
    from renderer.pentacle_view import PentacleView
    from types import SimpleNamespace
    cube=PentacleCube();cube.apply_move(Move(0,0,27.5))
    before=cube.colors
    assert not cube.can_apply(Move(1,1,90))
    outlines=PentacleView._physical_outlines(SimpleNamespace(cube=cube))
    assert set(outlines)==set(cube.paint_slots) and cube.colors==before
    cube.apply_moves(cube.alignment_moves(1))
    assert cube.can_apply(Move(1,1,90))


def test_internal_carriers_are_not_input_stickers_or_visible_edges():
    from renderer.pentacle_view import PentacleView
    from types import SimpleNamespace
    cube=PentacleCube()
    assert len(cube.hidden_panels)==24
    assert len(cube.paint_slots)==90
    blank=PentacleCube(paints=[-1]*len(cube.panels))
    assert all(blank._paints[i]==-1 for i in blank.paint_slots)
    assert all(blank._paints[i]==-2 for i in blank.hidden_panels)
    for slot in cube.hidden_panels:
        before=cube.colors
        cube.paint(slot,5)
        assert cube.colors==before
    surfaces=PentacleView._surfaces(SimpleNamespace(),blank)
    assert all(color==-1 for _,_,color,slot,*_ in surfaces if slot in blank.hidden_panels)


def test_old_coloured_carriers_are_removed_on_load_and_checkpoint_restore():
    cube=PentacleCube()
    old=[(p.face,cube.frames[p.home]) for p in cube.panels]
    cube.colors=old
    assert all(cube._paints[i]==-2 for i in cube.hidden_panels)
    assert cube.is_solved()
