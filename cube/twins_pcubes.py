"""Skewby Twins material from pCubes' declarative partition and cut parameters.

The previous Drawing3 radial continuation is kept as a separate legacy state;
it must not constrain the reference mechanism's independently movable leaves.
The hidden reference material is planar/chamfered. The display binds Drawing3
curved face panels to these same identities; it does not change move legality.
"""
import json,zlib,math
from pathlib import Path
from functools import lru_cache
from cube.planar_twins_state import PlanarTwinsState,AXES
from cube.appearance import ROTATIONS
from cube.polyhedral import CUBE
from cube.twins_material import EDGE_CUT

SOURCE_XML='Other cubes/Mixed/Edge-Vertex/Skewby Twins.xml'
XML_SHA256='7bb5b53167b223874f591f99db9392cdaeab03cbe11b9bbceafe61a6ece2615e'


@lru_cache(maxsize=1)
def data():
    value=json.loads(zlib.decompress((Path(__file__).parent/'data/twins_pcubes_material.bin').read_bytes()))
    if (value.get('version')!=1 or value.get('profile')!='pcubes-skewby-twins-coloured-shell-v1'
            or value.get('xml_sha256')!=XML_SHA256):
        raise ValueError('Invalid Twins reference material')
    return value


def fingerprint():return data()['source']


@lru_cache(maxsize=1)
def structure():
    solids=tuple(tuple((tuple(tuple(v) for v in poly),f) for poly,f in row) for row in data()['solids'])
    panels=tuple((h,f,tuple(tuple(v) for v in poly)) for h,f,poly in data()['panels'])
    return tuple(range(len(solids))),solids,panels


class TwinsPCubesState(PlanarTwinsState):
    layout=staticmethod(structure)
    puzzle_kind='mf8_twins'
    geometry_profile='pcubes-skewby-twins-v1'
    observation_model='mf8-twins-pcubes-material-v1'
    cut_bounds=(2*EDGE_CUT,)*12+(0.,)*8

    @property
    def geometry_fingerprint(self):return fingerprint()

    def observation_data(self):
        value=super().observation_data();value['source']=fingerprint();return value

    @classmethod
    def from_observation(cls,value):
        if type(value) is not dict or value.get('source')!=fingerprint():raise ValueError('twins.legacy_entry')
        return super().from_observation(value)

    def aligned_frames(self,home):return ROTATIONS

    def frame_aligned(self,home,frame):
        return any(max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7 for r in ROTATIONS)

    def shape_weights(self):return (1,)*len(self.frames)

    def panel_normal(self,face,poly):return CUBE[face]

    def validate_pose(self):
        # A separated, unaligned shape is supported and repaired before colour solving.
        try:self.aligned_permutation()
        except ValueError as error:
            if str(error)!='copter.align_first':raise

    def allowed_amount(self,axis,amount):
        from cube.curvy_copter import JUMBLE
        second=math.degrees(math.acos(1/math.sqrt(3)))
        if axis>=12:return abs((amount+30)%60-30)<1e-7
        return any(abs((amount-a+180)%360-180)<1e-7 for a in
                   (0.,180.,JUMBLE,-JUMBLE,180.-JUMBLE,JUMBLE-180.,second,-second,180.-second,second-180.))

    def proposed(self,move,guard=None):
        if (type(move.axis) is not int or move.axis not in range(20) or
                type(move.amount) not in (int,float) or not math.isfinite(move.amount)):
            raise ValueError('rigid.invalid')
        if not self.allowed_amount(move.axis,move.amount):raise ValueError('rigid.blocked')
        return super().proposed(move,guard)
