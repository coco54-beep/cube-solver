"""Requested expansion: physical identifiers, independent of the UI.

REQUESTED contains playable profiles. PENDING keeps removed references for
compatibility and research; these do not appear in the public catalogue.
"""
from dataclasses import dataclass

# Explicitly removed playable models. Keep shared mechanism code for the
# remaining models, but never offer these through the app or restore them.
REMOVED_KINDS = frozenset(('lanlan_master_clover', 'lanlan_pisces', 'planar_rhombic_12'))

PLAY_ONLY_KINDS = frozenset((
    'helicopter', 'helicopter_14', 'rua', 'clover', 'mf8_bauhinia_minx',
    'lanlan_curvy_copter', 'lanlan_comet_physical', 'mf8_twins', 'mf8_suncube_2',
    'lanlan_hexagram', 'lanlan_flower_copter', 'lanlan_butterflower',
))


@dataclass(frozen=True)
class RequestedPuzzle:
    kind: str
    name: str
    family: str
    n: int = 3
    mechanism: str = 'reference_needed'


REQUESTED = (
    RequestedPuzzle('lanlan_butterflower','LanLan Butterflower','edge_turning',3,'butterflower'),
    RequestedPuzzle('kairis_star_finder','Kairis Star Finder · regular 120°','football',3,'polyhedral'),
    RequestedPuzzle('lanlan_flower_copter','Flower Copter · regular turns','edge_turning',3,'flower_copter'),
    RequestedPuzzle('lanlan_hexagram','LanLan Curvy Hexagram · geometric profile','tetrahedral',3,'hexagram'),
    RequestedPuzzle('mf8_suncube_2','MF8 SunCube II · geometric profile','edge_turning',3,'suncube'),
    RequestedPuzzle('mf8_twins','MF8 Twins · geometric profile','edge_turning',3,'twins'),
    RequestedPuzzle('lanlan_comet_physical','LanLan Crazy Comet','edge_turning',3,'lanlan_comet'),
    RequestedPuzzle('lanlan_curvy_copter','Curvy Copter · spherical profile','edge_turning',3,'copter'),
    RequestedPuzzle('megaminx_ball','VeryPuzzle Megaminx Ball · D5','round',3,'spherical_minx'),
    RequestedPuzzle('aj_curvy_dinominx_4','AJ 4-Layer Curvy Dinominx','dodecahedral',4,'polyhedral'),
    RequestedPuzzle('mf8_bauhinia_minx','MF8 BauhiniaMinx','dodecahedral',3,'polyhedral'),
    RequestedPuzzle('yeet_ball','YJ Yeet Ball','ivy',3,'ivy'),
    RequestedPuzzle('skewb_rhombic','LanLan Skewb Rhombic Dodecahedron','skewb',3,'polyhedral'),
    RequestedPuzzle('rhombic_3','LanLan 3×3 Rhombic Dodecahedron','dodecahedral',3,'shape'),
    RequestedPuzzle('rhombic_4','LanLan 4×4 Rhombic Dodecahedron','dodecahedral',4,'shape'),
    RequestedPuzzle('rhombic_mask_4','LanLan 4×4 Rhombic Mask','dodecahedral',4,'shape'),
    RequestedPuzzle('caneball_4','LanLan 4×4 Caneball · 8 colours','octahedral',4,'shape'),
    RequestedPuzzle('jewel_fto','LanLan Jewel · 8-Axis Octahedron','octahedral',3,'polyhedral'),
    RequestedPuzzle('rua','LanLan Rua · 12-Axis Dodecahedron','edge_turning',3,'polyhedral'),
    RequestedPuzzle('helicopter_14','LanLan 12-Axis Tetrakaidecahedron','edge_turning',3,'polyhedral'),
    RequestedPuzzle('time_machine','Time Machine','circle',2,'dial_beans'),
    RequestedPuzzle('bean_6','Magic Beans · 6 sides','round',6,'dial_beans'),
    RequestedPuzzle('bean_10','Magic Beans · 10 sides','round',10,'dial_beans'),
    RequestedPuzzle('i_cube', 'I-Cube', 'extended_cube',mechanism='extended'),
    RequestedPuzzle('l_cube', 'L-Cube', 'extended_cube',mechanism='extended'),
    RequestedPuzzle('t_cube', 'T-Cube', 'extended_cube',mechanism='extended'),
    RequestedPuzzle('x_cube', 'X-Cube', 'extended_cube',mechanism='extended'),
    RequestedPuzzle('tri_cube', 'Tri-Cube', 'extended_cube',mechanism='extended'),
    RequestedPuzzle('temple_cube', 'Temple-Cube', 'extended_cube',mechanism='extended'),
    RequestedPuzzle('cross_cube', 'Cross-Cube', 'extended_cube',mechanism='extended'),
    RequestedPuzzle('siamese_a', 'Siamese Cube A', 'compound_cube', mechanism='siamese'),
    RequestedPuzzle('siamese_b', 'Siamese Cube B', 'compound_cube', mechanism='siamese'),
    RequestedPuzzle('trajber', "Trajber’s Octahedron · 4×4", 'octahedral', 4, 'shape'),
    RequestedPuzzle('pyraminx_diamond', 'Pyraminx Diamond', 'octahedral',mechanism='diamond'),
    RequestedPuzzle('pyraminx_crystal', 'Pyraminx Crystal', 'dodecahedral', mechanism='polyhedral'),
    RequestedPuzzle('starminx_i', 'Starminx I', 'dodecahedral', mechanism='polyhedral'),
    RequestedPuzzle('pentultimate', 'Pentultimate', 'dodecahedral', mechanism='polyhedral'),
    RequestedPuzzle('master_pentultimate', 'Master Pentultimate', 'dodecahedral', mechanism='polyhedral'),
    RequestedPuzzle('dodecahedron_2', '2×2 Dodecahedron', 'dodecahedral', 2, 'shape'),
    RequestedPuzzle('rediminx', 'Rediminx', 'dodecahedral', mechanism='polyhedral'),
    RequestedPuzzle('dodecahedron_3', '3×3 Dodecahedron', 'dodecahedral', 3, 'shape'),
    RequestedPuzzle('dogic_i', 'Dogic I · 12 colours', 'icosahedral', mechanism='dogic'),
    RequestedPuzzle('container', 'Container', 'shape_cube', mechanism='skewb_shell'),
    RequestedPuzzle('rubik_cheese', 'Rubik Cheese · 2 layers', 'layered_round', 2, 'cheese'),
    RequestedPuzzle('cheese_3', '3-Layer Cheese', 'layered_round', mechanism='cheese'),
    RequestedPuzzle('masterball', 'Masterball', 'layered_round', 4, 'masterball'),
    RequestedPuzzle('pentagonal_domino', 'Pentagonal Domino', 'pentagonal', 2, 'prism'),
    RequestedPuzzle('pentagonal_prism', 'Pentagonal Prism', 'pentagonal', 3, 'prism'),
    RequestedPuzzle('pentagonal_4', 'Pentagonal 4-Layer', 'pentagonal', 4, 'prism'),
    RequestedPuzzle('professor_pentagonal', 'Professor Pentagonal', 'pentagonal', 5, 'prism'),
    RequestedPuzzle('dogic_20', 'Dogic · 20 colours', 'icosahedral', mechanism='dogic'),
    RequestedPuzzle('master_brilic', 'Master Brilic', 'dodecahedral', mechanism='polyhedral'),
    RequestedPuzzle('blanker', 'Blanker Cube', 'shape_cube', 2, 'blanker'),
    RequestedPuzzle('mirror_kilominx', 'Mirror Kilominx', 'mirror_minx', 2, 'mirror_minx'),
    RequestedPuzzle('mirror_megaminx', 'Mirror Megaminx', 'mirror_minx', 3, 'mirror_minx'),
)
BY_KIND = {entry.kind: entry for entry in REQUESTED}
PENDING = (
    RequestedPuzzle('lanlan_clover_pyraminx','LanLan Clover Pyraminx','tetrahedral'),
    RequestedPuzzle('vp_clover_dodecahedron','VeryPuzzle Clover Dodecahedron','dodecahedral'),
    RequestedPuzzle('lanlan_sunflower','LanLan Sunflower','edge_turning'),
    RequestedPuzzle('lanlan_andromeda','LanLan Andromeda','edge_turning'),
)
PENDING_BY_KIND={entry.kind:entry for entry in PENDING}
PENDING_KINDS=frozenset(PENDING_BY_KIND)
BY_KIND.update(PENDING_BY_KIND)
# Keep the mismatched prototype available to development audits only.
RESEARCH_ONLY = {
    'lanlan_clover_pyraminx':RequestedPuzzle('lanlan_clover_pyraminx',
        'Cornerless Clover Tetrahedron · research prototype','tetrahedral',3,'clover_pyraminx'),
}
BY_KIND.update(RESEARCH_ONLY)
# Two names in the original request refer to the same four-layer model.
BY_KIND['trajber_4']=BY_KIND['trajber']
POLYHEDRAL_KINDS = frozenset(e.kind for e in REQUESTED if e.mechanism == 'polyhedral')
DOGIC_KINDS = frozenset(('dogic_i', 'dogic_20'))
SIAMESE_KINDS = frozenset(('siamese_a', 'siamese_b'))
PRISM_KINDS = frozenset(e.kind for e in REQUESTED if e.mechanism=='prism')
COLOR_ENTRY_KINDS=frozenset(e.kind for e in REQUESTED if e.mechanism in
                          ('polyhedral','prism','dogic','siamese','diamond','masterball','cheese','dial_beans','ivy'))

# Navigation families describe the collection, not the date a model was added.
# Each requested physical model has one home; Trajber's alias is not a second entry.
CATALOGUE_FAMILIES={
    'pyraminx':('lanlan_hexagram',),
    'football':('kairis_star_finder',),
    'circle_family':('time_machine',),
    'extended_family':('i_cube','l_cube','t_cube','x_cube','tri_cube','temple_cube','cross_cube'),
    'bandaged_family':('siamese_a','siamese_b'),
    'fto':('trajber','pyraminx_diamond','jewel_fto','caneball_4'),
    'megaminx':('pyraminx_crystal','starminx_i','pentultimate','master_pentultimate',
                'dodecahedron_2','rediminx','dodecahedron_3','master_brilic',
                'rhombic_3','rhombic_4','rhombic_mask_4','mf8_bauhinia_minx','aj_curvy_dinominx_4'),
    'icosahedron':('dogic_i','dogic_20'),
    'skewb':('container','skewb_rhombic'),
    'edge_family':('lanlan_flower_copter','rua','helicopter_14','lanlan_curvy_copter','lanlan_comet_physical','mf8_twins','mf8_suncube_2',
                   'lanlan_butterflower'),
    'ivy_family':('yeet_ball',),
    'round_family':('rubik_cheese','cheese_3','masterball','bean_6','bean_10','megaminx_ball'),
    'pentagonal_family':('pentagonal_domino','pentagonal_prism','pentagonal_4','professor_pentagonal'),
    'mirror':('blanker','mirror_kilominx','mirror_megaminx'),
}


def catalogue_family(kind):
    kind=BY_KIND[kind].kind if kind in BY_KIND else kind
    return next((family for family,kinds in CATALOGUE_FAMILIES.items() if kind in kinds),None)
