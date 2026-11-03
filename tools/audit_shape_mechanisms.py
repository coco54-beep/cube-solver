"""Read-only mechanism audit: a closed colour action is not a shape kernel.

Reads pCubes XML as evidence only; never executes embedded scripts. Does not
modify public catalogue, puzzle definitions, saved states or solve tables.
"""
import json,sys,random,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/optimization/2026-11-02/shape-reality-audit'
REFERENCES={
 'helicopter':'Other cubes/Edge Turning/Helicopter cube/Helicopter cube.xml',
 'rua':'Other forms/Catalan Solids/Rhombic Dodecahedron/Face Turning/Rua.xml',
 'mf8_bauhinia_minx':'Other forms/Platonic solids/Dodecahedron/Vertex Turning/Bauhinia.xml',
 'clover':'Other cubes/Edge Turning/4-Leaf-Clover Cube.xml',
}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    routes=json.loads((ROOT/'reports/reliability-audit/2026-11-02/catalogue/routes.json').read_text())
    result={'scope':'Catalogue inventory and targeted mechanism checks, not physical certification of all routes',
            'inventory_route_count':len(routes),'runtime_probes':[],'local_references':{},'rigid_probes':[]}
    for kind,relative in REFERENCES.items():
        path=ROOT/'bin/pCubes/Puzzles'/relative;root=ET.parse(path).getroot()
        result['local_references'][kind]={'path':str(path.relative_to(ROOT)),
            'names':[e.text for e in root.iter('Name')],
            'links':[e.text for e in root.iter('Link')],
            'axes':[dict(e.attrib) for e in root.iter('Axes')]}
        assert any('JumbleAngle' in e.attrib for e in root.iter('Axes'))
    for kind,n in (('helicopter',3),('rua',3),('mf8_bauhinia_minx',3),('clover',3),
                   ('helicopter_14',3),('kairis_star_finder',3),('aj_curvy_dinominx_4',4)):
        cube=PolyhedralPuzzle(kind,n);geometry=cube.geometry
        polygons=tuple(s.polygon for s in geometry.stickers);before=tuple(cube.colors)
        moves=cube.moves();rng=random.Random(20261102)
        for _ in range(100):cube.apply_move(rng.choice(moves))
        assert cube.geometry is geometry and tuple(s.polygon for s in cube.geometry.stickers)==polygons
        result['runtime_probes'].append({'kind':kind,'order':n,'colour_scramble_changes_state':tuple(cube.colors)!=before,
          'steps':100,'world_polygons_stay_fixed':True,'has_rigid_frames':hasattr(cube,'frames'),
          'degrees_per_primitive':sorted({360/geometry.spec.order(m.axis) for m in moves}),
          'finding':'Only closed colour permutations; cannot represent a protruding or blocked jumbled state'})
    from cube.curvy_copter import JUMBLE
    from cube.polyhedral import Move
    from cube.copter_input import CopterCube
    from cube.suncube import SunCube
    from cube.butterflower import ButterflowerCube
    from cube.flower_copter import FlowerCopterCube
    from cube.twins_state import TwinsState
    for factory in (CopterCube,SunCube,ButterflowerCube,FlowerCopterCube,TwinsState):
        cube=factory();before=cube.signature();paints=cube.paints
        cube.apply_move(Move(0,0,JUMBLE));changed=cube.signature()!=before
        cube.apply_move(Move(0,0,-JUMBLE))
        assert changed and cube.signature()==before and cube.paints==paints
        result['rigid_probes'].append({'kind':cube.puzzle_kind,'partial_turn_and_inverse_passed':True,
                                      'paint_preserved':True,'physical_hardware_certified':False})
    from cube.solid_shape_mods import FACTORIES,faces_for
    from cube.mastermorphix import transform
    from cube.compound_solids import face_normal
    from cube.polyhedral import dot
    from cube.coordinates import coord_values
    result['solid_shell_probes']=[]
    for kind,factory in FACTORIES.items():
        if kind=='trajber_4':continue  # Existing alias, not a second model.
        n=factory.supported_orders[0];cube=factory.solved(n=n);planes={}
        for p in cube.cubies.values():
            for poly,col in faces_for(kind,p.home,n):
                if col<0:continue
                normal=face_normal(poly);bound=dot(normal,poly[0])
                planes[tuple(round(v,7) for v in normal)+(round(bound,7),)]=(normal,bound)
        worst=0.;witness=None;count=0
        for axis in range(3):
            for layer in coord_values(n):
                work=cube.clone();work.turn_layer(axis,(layer,),1);count+=1
                value=max(dot(normal,transform(p.frame,v))-b for p in work.cubies.values()
                          for poly,col in faces_for(kind,p.home,n) for v in poly for normal,b in planes.values())
                if value>worst:worst=value;witness=(axis,layer)
        result['solid_shell_probes'].append({'kind':kind,'order':n,'quarter_layer_actions_checked':count,
            'maximum_outside_solved_hull':worst,'changes_outline_in_current_model':worst>1e-6,
            'witness_axis_layer':witness if worst>1e-6 else None,
            'scope':'All primitive quarter-layer turns against convex solved shell; not hardware certification'})
    (OUT/'mechanisms.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'inventory_routes':len(routes),'fixed_slot_probes':len(result['runtime_probes']),
                      'xml_jumble_definitions':len(REFERENCES),'rigid_partial_roundtrips':len(result['rigid_probes'])}))


if __name__=='__main__':main()
