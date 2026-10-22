"""Traditional Mixup entry: choose the assembly at each scaffold position.

Scaffold assemblies are input guides. Confirmed panels must come from the real
model's pose catalogue; only the observation matcher creates a playable state.
"""
from copy import deepcopy
from functools import lru_cache
from dataclasses import dataclass
import math

from cube.articulated import MIXUP_MODELS
from cube.articulated_observation import (ObservationDraft,_panels,new_cube,normal,
    project,face_world,polygon_key,centre2,contains,Panel,_visible)
from cube.polyhedral import CUBE,dot,clip,unit,mean,rotate

EPS=1e-6


def base_kind(kind):return 'mixup_plus_333' if MIXUP_MODELS[kind][1] else 'mixup_333'


def _box(poly):return min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)


@lru_cache(maxsize=2)
def base_blocks(kind):
    """The actual basic/Plus 333 shell, including separate inner edges."""
    cube=new_cube(base_kind(kind));blocks=[]
    for face in range(6):
        for home in range(len(cube.solids)):
            for panel in _panels(cube,home,0,face):
                blocks.append({'face':face,'role':cube.solids[home].role,'home':home,
                               'outline':panel.outline,'bounds':_box(panel.outline)})
    return tuple(blocks)


def _rect(x1,y1,x2,y2):
    return ((x1,y1),(x2,y1),(x2,y2),(x1,y2))


@dataclass(frozen=True)
class Composition:
    key:str
    parts:tuple


@lru_cache(maxsize=32)
def compositions(kind,role):
    """Complete assemblies for a position, never recursive cutting tools."""
    single=Composition('single',(_rect(-1,-1,1,1),))
    if MIXUP_MODELS[kind][0]==(3,3,3) or role=='corner':return (single,)
    horizontal=Composition('pair_horizontal',(_rect(-1,-1,1,0),_rect(-1,0,1,1)))
    vertical=Composition('pair_vertical',(_rect(-1,-1,0,1),_rect(0,-1,1,1)))
    if MIXUP_MODELS[kind][0].count(4)<2:return single,horizontal,vertical
    return (single,horizontal,vertical,
        Composition('large_top',(_rect(-1,0,1,1),_rect(-1,-1,0,0),_rect(0,-1,1,0))),
        Composition('large_bottom',(_rect(-1,-1,1,0),_rect(-1,0,0,1),_rect(0,0,1,1))),
        Composition('large_left',(_rect(-1,-1,0,1),_rect(0,-1,1,0),_rect(0,0,1,1))),
        Composition('large_right',(_rect(0,-1,1,1),_rect(-1,-1,0,0),_rect(-1,0,0,1))),
        Composition('four',tuple(_rect(x,y,x+1,y+1) for y in (-1,0) for x in (-1,0))))


def composition_outlines(block,composition):
    """Place the complete assembly on the unchanged base position."""
    x1,y1,x2,y2=block['bounds'];result=[]
    parent=block['outline'];cx,cy=centre2(parent)
    for part in composition.parts:
        cell=tuple((x1+(x+1)*(x2-x1)/2,y1+(y+1)*(y2-y1)/2,0.) for x,y in part)
        for p,q in zip(parent,parent[1:]+parent[:1]):
            nx,ny=q[1]-p[1],p[0]-q[0];bound=nx*p[0]+ny*p[1]
            if nx*cx+ny*cy>bound:nx,ny,bound=-nx,-ny,-bound
            cell=clip(cell,(nx,ny,0.),bound)
            if not cell:break
        if cell:result.append(tuple((x,y) for x,y,_ in cell))
    return tuple(result)


def identify_composition(kind,block):
    guides=sorted(polygon_key(c['guide']) for c in block['cells'])
    for choice in compositions(kind,block['role']):
        expected=sorted(polygon_key(face_world(p,block['face'])) for p in composition_outlines(block,choice))
        if guides==expected:return choice.key
    return None


def _cell(outline,face):
    return {'guide':face_world(outline,face),'world':None,'color':-1,'source_slot':None}


def _piece_identity(cell):
    identity=cell.get('piece_key') or (polygon_key(cell['world']),)
    return tuple(tuple(tuple(p) for p in poly) for poly in identity)


@lru_cache(maxsize=2)
def _position_directions(kind):
    """One direction per complete scaffold piece, shared by all its faces."""
    cube=new_cube(base_kind(kind));blocks=base_blocks(kind);result=[]
    for home,solid in enumerate(cube.solids):
        positions=tuple(i for i,b in enumerate(blocks) if b['home']==home)
        vertices=set(p for poly,color in solid.faces if color>=0 for p in poly)
        result.append((positions,solid.role,unit(mean(tuple(vertices)))))
    return tuple(result)


@lru_cache(maxsize=2)
def _inner_position_ridges(kind):
    from cube.mixup_assembly import AssemblyPiece,inner_ridge,inner_turn_axis
    cube=new_cube(base_kind(kind));blocks=base_blocks(kind);result=[]
    for home,solid in enumerate(cube.solids):
        if solid.role!='inner_edge':continue
        faces=cube.placed_faces(home)
        part=AssemblyPiece('inner_edge',tuple(p for p,c in faces if c>=0),0,tuple(p for p,c in faces))
        ridge=inner_ridge(part);radial,_=inner_turn_axis((part,))
        direction=unit(tuple(b-a for a,b in zip(*ridge)))
        result.append((tuple(i for i,b in enumerate(blocks) if b['home']==home),radial,direction))
    return tuple(result)


def _piece_positions(kind,panels,role,body=()):
    # A 45-degree edge has two sloping panels on opposite sides of a centre
    # position. Classifying each panel's projected centroid separately splits
    # that one piece across the neighbouring edge AND centre positions.
    if role=='inner_edge' and body:
        from cube.mixup_assembly import AssemblyPiece,inner_ridge,inner_turn_axis
        part=AssemblyPiece(role,panels,0,body);ridge=inner_ridge(part)
        radial,_=inner_turn_axis((part,));along=unit(tuple(b-a for a,b in zip(*ridge)))
        return max(_inner_position_ridges(base_kind(kind)),
                   key=lambda p:dot(radial,p[1])+.2*abs(dot(along,p[2])))[0]
    direction=unit(mean(tuple(set(p for poly in panels for p in poly))))
    candidates=[item for item in _position_directions(kind)
                if (item[1]=='corner')==(role=='corner')]
    return max(candidates,key=lambda item:dot(direction,item[2]))[0]


def _inherited_colour(world,panels,strict=False):
    """Keep a colour when a coplanar surface is split or merged unambiguously."""
    from cube.mixup_assembly import area2
    n=normal(world);face=max(range(6),key=lambda f:dot(n,CUBE[f]))
    outline=project(world,face);total=area2(outline);covered=0.;colours=set()
    if total<EPS:return -1
    for old,color in panels:
        if dot(n,normal(old))<1-EPS or any(abs(sum(n[a]*(p[a]-world[0][a]) for a in range(3)))>EPS for p in old):continue
        boundary=project(old,face);centre=centre2(boundary)
        part=tuple((x,y,0.) for x,y in outline)
        for p,q in zip(boundary,boundary[1:]+boundary[:1]):
            nx,ny=q[1]-p[1],p[0]-q[0];bound=nx*p[0]+ny*p[1]
            if nx*centre[0]+ny*centre[1]>bound:nx,ny,bound=-nx,-ny,-bound
            part=clip(part,(nx,ny,0.),bound)
            if not part:break
        overlap=area2(tuple((x,y) for x,y,_ in part)) if part else 0.
        if overlap>EPS:
            colours.add(color);covered+=overlap
            if len(colours)>1:
                if strict:raise ValueError('mixup.entry_colour_merge_conflict')
                return -1
    return next(iter(colours)) if len(colours)==1 and abs(covered-total)<=EPS*max(1.,total) else -1


def _panel_shape(world):
    """Rigid panel shape, independent of its spatial orientation."""
    return len(world),tuple(sorted(round(math.dist(p,q),6)
        for i,p in enumerate(world) for q in world[i+1:]))


def _oriented_colour(world,role,old_cells):
    """Retain an identifiable same-shaped panel when only its direction changes."""
    shape=_panel_shape(world)
    matches=[c for c in old_cells if c['color']>=0 and c.get('panel_role')==role
             and _panel_shape(c['world'])==shape]
    colours={c['color'] for c in matches}
    return next(iter(colours)) if len(colours)==1 else -1


def _inner_colour(cell,old_cells):
    """Carry colours by fixed ridge intervals even when the skins tilt."""
    from cube.mixup_assembly import AssemblyPiece,inner_ridge,area
    def piece(c):return AssemblyPiece('inner_edge',(c['world'],),0,c.get('body',()),c.get('inner_direction',()))
    try:left,right=inner_ridge(piece(cell))
    except ValueError:return -1
    length=math.dist(left,right);axis=unit(tuple(b-a for a,b in zip(left,right)))
    width=area(cell['world'])/length;intervals=[];colours=set();seen=set()
    for old in old_cells:
        if old.get('panel_role')!='inner_edge' or old['color']<0:continue
        try:p,q=inner_ridge(piece(old))
        except ValueError:continue
        if abs(area(old['world'])/math.dist(p,q)-width)>EPS:continue
        distances=[];valid=True
        for point in (p,q):
            delta=tuple(point[i]-left[i] for i in range(3));along=dot(delta,axis)
            if sum((delta[i]-along*axis[i])**2 for i in range(3))>EPS*EPS:valid=False;break
            distances.append(along)
        if not valid:continue
        low=max(0.,min(distances));high=min(length,max(distances))
        if high-low<=EPS:continue
        signature=(round(low,6),round(high,6),old['color'])
        if signature in seen:continue
        seen.add(signature);colours.add(old['color']);intervals.append((low,high))
    if len(colours)>1:raise ValueError('mixup.entry_colour_merge_conflict')
    covered=0.;end=0.
    for low,high in sorted(intervals):
        covered+=max(0.,high-max(low,end));end=max(end,high)
    return next(iter(colours)) if len(colours)==1 and covered>=length-EPS else -1


def edge_other_side(points,source_face,target_face):
    """Fold a guide across its shared cube edge, preserving the along-edge axis.

    This maps scaffold guides only. Real poses and colours are never reflected
    from one face to another; they still require their own observations.
    """
    if source_face==target_face:return tuple(points)
    source=CUBE[source_face];target=CUBE[target_face]
    a=max(range(3),key=lambda i:abs(source[i]));b=max(range(3),key=lambda i:abs(target[i]))
    if a==b:raise ValueError('observe.invalid')
    factor=source[a]*target[b];result=[]
    for point in points:
        mapped=list(point);mapped[a]=point[b]*factor;mapped[b]=point[a]*factor
        result.append(tuple(mapped))
    # Swapping the two axes reverses handedness; keep outward winding.
    return tuple(reversed(result))


class MixupEntryDraft:
    def __init__(self,kind,state=None):
        if kind not in MIXUP_MODELS:raise ValueError('observe.invalid')
        self.kind=kind;self.blocks=[];self.repaired=False
        for block in base_blocks(kind):
            configured=block['role']=='corner'
            item=dict(block);item.update(configured=configured,composition='single' if configured else None,
                                        rotation=0,assembly_source=None,
                                        cells=[_cell(block['outline'],block['face'])])
            self.blocks.append(item)
        if state is not None:
            if state.get('kind')!=kind or state.get('version') not in (1,2,3,4,5,6,7,8) or len(state['blocks'])!=len(self.blocks):raise ValueError('observe.invalid')
            for dest,src in zip(self.blocks,state['blocks']):
                if not isinstance(src['cells'],(list,tuple)) or len(src['cells'])>128:raise ValueError('observe.invalid')
                dest['configured']=bool(src['configured'])
                rotation=src.get('rotation',0);source=src.get('assembly_source')
                if type(rotation) is not int or not 0<=rotation<4:raise ValueError('observe.invalid')
                if source is not None and not (isinstance(source,str) and source.startswith('assembly_')):raise ValueError('observe.invalid')
                dest.update(rotation=rotation,assembly_source=source)
                dest['cells']=deepcopy(src['cells'])
                for cell in dest['cells']:
                    if type(cell['color']) is not int or not -1<=cell['color']<6:raise ValueError('observe.invalid')
                    for field in ('guide','world'):
                        if cell[field] is None:
                            if field=='guide':raise ValueError('observe.invalid')
                            continue
                        poly=tuple(tuple(float(v) for v in p) for p in cell[field])
                        if not 3<=len(poly)<=16 or any(len(p)!=3 or any(not math.isfinite(v) or abs(v)>3 for v in p) for p in poly):raise ValueError('observe.invalid')
                        cell[field]=poly
                    if cell.get('body'):
                        cell['body']=tuple(tuple(tuple(float(v) for v in p) for p in poly) for poly in cell['body'])
                        cell['body_key']=tuple(sorted(polygon_key(poly) for poly in cell['body']))
                    if cell.get('inner_direction'):cell['inner_direction']=tuple(float(v) for v in cell['inner_direction'])
                    if (cell.get('panel_role')=='inner_edge' and cell.get('body') and
                            cell.get('inner_direction') and cell['world'] is not None and
                            dot(cell['inner_direction'],normal(cell['world']))>EPS):
                        # Old catalogue v4 reversed only a direction vector.
                        # Turn its actual body about the fixed ridge and update
                        # its skin together, retaining the recorded colour.
                        from cube.mixup_assembly import AssemblyPiece,half_turn_inner
                        piece=AssemblyPiece('inner_edge',(cell['world'],),0,cell['body'],
                                            tuple(-v for v in cell['inner_direction']))
                        repaired=half_turn_inner(piece)
                        cell.update(world=repaired.panels[0],guide=face_world(project(repaired.panels[0],dest['face']),dest['face']),
                                    piece_key=tuple(polygon_key(p) for p in repaired.panels),
                                    body=repaired.body,inner_direction=repaired.direction,
                                    body_key=tuple(sorted(polygon_key(poly) for poly in repaired.body)))
                        dest.update(assembly_source=None,rotation=0)
                        self.repaired=True
                    if cell.get('piece_key'):cell['piece_key']=_piece_identity(cell)
                if state['version']>=3:
                    key=src.get('composition')
                    if key is not None and not (isinstance(key,str) and key.startswith('assembly_')) and key not in {c.key for c in compositions(kind,dest['role'])}:
                        raise ValueError('observe.invalid')
                    dest['composition']=key if dest['configured'] else None
                else:
                    dest['composition']=identify_composition(kind,dest) if dest['configured'] else None
            if state['version']<4:self._restore_edge_links()
            if state['version']<7:self._regroup_pieces()
            if state['version']<8:self._migrate_inner_geometry()
            if state['version']<8:self._regroup_inner_pieces()

    def state(self):
        return {'version':8,'kind':self.kind,'blocks':[{k:deepcopy(b[k]) for k in ('configured','composition','rotation','assembly_source','cells')} for b in self.blocks]}

    def physical_signature(self):
        """Complete coloured pieces, independent of editor guides and IDs.

        Only an exact physical match may reuse a previously verified cube.
        Include piece connectivity and inner bodies, not just visible colours.
        Incomplete or contradictory observations never match a known state.
        """
        pieces={};owners={}
        for block in self.blocks:
            if not block['configured']:return None
            for cell in block['cells']:
                if cell['world'] is None or cell['color']<0:return None
                role=cell.get('panel_role')
                if role not in ('corner','edge','centre','inner_edge'):return None
                identity=_piece_identity(cell)
                body=tuple(sorted(polygon_key(poly) for poly in cell.get('body',())))
                direction=tuple(round(v,6) for v in cell.get('inner_direction',()))
                if role=='inner_edge' and (not body or not direction):return None
                shape=(role,body,direction)
                piece=pieces.setdefault(identity,(shape,{}))
                if piece[0]!=shape:return None
                panel=polygon_key(cell['world']);colour=cell['color']
                if panel in owners and owners[panel]!=identity:return None
                owners[panel]=identity
                if panel in piece[1] and piece[1][panel]!=colour:return None
                piece[1][panel]=colour
        if not pieces:return None
        return tuple(sorted((shape,tuple(sorted(panels.items()))) for shape,panels in pieces.values()))

    def _migrate_inner_geometry(self):
        """Repair recognised v7 presets without guessing imported real poses."""
        from cube.mixup_assembly import legacy_inner_sources,inner_ridge
        for index,block in enumerate(self.blocks):
            if block['role']!='inner_edge' or not block.get('assembly_source'):continue
            entered=self.assembly_at(index)
            if entered is None:continue
            source=legacy_inner_sources(self.kind,self.blocks,(index,)).get(block['assembly_source'])
            if source is None:continue
            replacement,expected=source;turn=block['rotation']
            if entered.key!=expected.get(turn):continue
            ridge=inner_ridge(replacement.pieces[0]);along=unit(tuple(b-a for a,b in zip(*ridge)))
            def interval(world):
                values=[dot(p,along) for p in world]
                return round(min(values),6),round(max(values),6)
            colours={interval(c['world']):c['color'] for c in block['cells']}
            self._set_assembly(index,replacement)
            for cell in self.blocks[index]['cells']:cell['color']=colours.get(interval(cell['world']),-1)
            self.repaired=True

    def _regroup_pieces(self):
        """Migrate old panel-based slots without changing any recorded surface."""
        pieces={};affected=set()
        for bi,block in enumerate(self.blocks):
            keep=[]
            for cell in block['cells']:
                if cell['world'] is None or not cell.get('piece_key'):
                    keep.append(cell);continue
                pieces.setdefault(_piece_identity(cell),{}).setdefault(
                    (polygon_key(cell['world']),cell['color']),cell)
                affected.add(bi)
            block['cells']=keep
        for panels in pieces.values():
            cells=list(panels.values())
            positions=_piece_positions(self.kind,tuple(c['world'] for c in cells),cells[0].get('panel_role'))
            for cell in cells:
                bi=max(positions,key=lambda i:dot(normal(cell['world']),CUBE[self.blocks[i]['face']]))
                self.blocks[bi]['cells'].append(cell);affected.add(bi)
        for bi in affected:
            block=self.blocks[bi]
            block.update(configured=all(c['world'] is not None for c in block['cells']),
                         composition=None,rotation=0,assembly_source=None)

    def _regroup_inner_pieces(self):
        """Different coloured planes on one black ridge share one input region."""
        moves=[];affected=set()
        for index,block in enumerate(self.blocks):
            keep=[]
            for cell in block['cells']:
                if cell.get('panel_role')=='inner_edge' and cell.get('body') and cell['world'] is not None:
                    target=_piece_positions(self.kind,(cell['world'],),'inner_edge',cell['body'])[0]
                    if target!=index:
                        moves.append((target,cell));affected.update((index,target));continue
                keep.append(cell)
            block['cells']=keep
        for target,cell in moves:
            block=self.blocks[target]
            if not block['configured'] and all(c['world'] is None and c['color']<0 for c in block['cells']):
                block['cells']=[]
            block['cells'].append(cell);block['configured']=True
        for index in affected:
            self.blocks[index].update(composition=None,assembly_source=None,rotation=0)

    def linked_positions(self,index):
        block=self.blocks[index]
        if block['role']!='edge':return (index,)
        return tuple(i for i,b in enumerate(self.blocks) if b['role']=='edge' and b['home']==block['home'])

    def linked_cells(self,index,child):
        block=self.blocks[index];cell=block['cells'][child];piece=cell.get('piece_key')
        if piece is not None:
            return tuple((bi,ci) for bi,b in enumerate(self.blocks) for ci,c in enumerate(b['cells']) if c.get('piece_key')==piece)
        guide=cell['guide'];result=[]
        for peer in self.linked_positions(index):
            other=self.blocks[peer]
            expected=polygon_key(edge_other_side(guide,block['face'],other['face']))
            result.extend((peer,ci) for ci,cell in enumerate(other['cells']) if polygon_key(cell['guide'])==expected)
        return tuple(result)

    def _replace_linked(self,index,guides):
        """Prepare both sides before committing, preserving each side's records."""
        source=self.blocks[index];updates=[]
        for peer in self.linked_positions(index):
            block=self.blocks[peer];cells=[];retained=set()
            for guide in guides:
                world=edge_other_side(guide,source['face'],block['face'])
                cell={'guide':world,'world':None,'color':-1,'source_slot':None}
                old=next((i for i,c in enumerate(block['cells']) if polygon_key(c['guide'])==polygon_key(world)),None)
                if old is not None:cell=deepcopy(block['cells'][old]);retained.add(old)
                cells.append(cell)
            if any(c['color']>=0 and i not in retained for i,c in enumerate(block['cells'])):
                raise ValueError('mixup.entry_link_conflict' if peer!=index else 'mixup.entry_composition_conflict')
            proposed=dict(block,cells=cells)
            updates.append((block,cells,identify_composition(self.kind,proposed)))
        for block,cells,key in updates:block.update(cells=cells,configured=True,composition=key,rotation=0,assembly_source=None)

    def _restore_edge_links(self):
        """Migrate independent old views without losing an entered face."""
        visited=set()
        for index,block in enumerate(self.blocks):
            if index in visited:continue
            peers=self.linked_positions(index);visited.update(peers)
            if len(peers)<2:continue
            sources=[i for i in peers if self.blocks[i]['configured'] and self.blocks[i]['composition'] is not None]
            sources.sort(key=lambda i:sum(c['color']>=0 for c in self.blocks[i]['cells']),reverse=True)
            for source in sources:
                try:self._replace_linked(source,[c['guide'] for c in self.blocks[source]['cells']])
                except ValueError:continue
                break

    def set_composition(self,index,key):
        """Choose a full assembly, retaining records on unchanged parts."""
        block=self.blocks[index]
        choice=next((c for c in compositions(self.kind,block['role']) if c.key==key),None)
        if choice is None:raise ValueError('observe.invalid')
        guides=[face_world(p,block['face']) for p in composition_outlines(block,choice)]
        self._replace_linked(index,guides)

    def set_assembly(self,index,assembly):
        """Use complete real piece geometry, with shared single-colour faces."""
        candidate=MixupEntryDraft(self.kind,self.state())
        candidate._set_assembly(index,assembly)
        self._commit_region(index,candidate)

    def _set_assembly(self,index,assembly):
        peers=self.linked_positions(index)
        if assembly.kind!=self.kind or set(assembly.positions)!=set(peers):raise ValueError('observe.invalid')
        turns=self.blocks[index]['rotation'];updates=[];colours={};surfaces={};old_cells=[]
        for bi in peers:
            block=self.blocks[bi]
            for ci,cell in enumerate(block['cells']):
                if cell['world'] is None:continue
                if cell['color']<0:continue
                old_cells.append(cell)
                key=polygon_key(cell['world'])
                if key in colours and colours[key]!=cell['color']:raise ValueError('mixup.entry_composition_conflict')
                colours[key]=cell['color']
                surfaces[key]=(cell['world'],cell['color'])
        for peer in peers:
            block=self.blocks[peer];cells=[]
            for piece in assembly.pieces:
                piece_key=tuple(sorted(polygon_key(p) for p in piece.panels))
                for world in piece.panels:
                    if dot(normal(world),CUBE[block['face']])<=EPS:continue
                    cell={'guide':face_world(project(world,block['face']),block['face']),
                          'world':world,'color':-1,
                          'source_slot':None,'panel_role':piece.role,'piece_key':piece_key,
                          'body':piece.body,'inner_direction':piece.direction}
                    if piece.body:cell['body_key']=tuple(sorted(polygon_key(p) for p in piece.body))
                    cells.append(cell)
            updates.append((block,cells))
        if ({polygon_key(c['world']) for _,cells in updates for c in cells}!=
                {polygon_key(p) for piece in assembly.pieces for p in piece.panels}):
            raise ValueError('observe.invalid')
        for block,cells in updates:block.update(cells=cells,configured=True,composition=assembly.key,
                                               rotation=0,assembly_source=assembly.key)
        if turns:self._rotate_assembly(index,turns,assembly.key)
        for peer in peers:
            for cell in self.blocks[peer]['cells']:
                signature=polygon_key(cell['world'])
                inner=cell.get('panel_role')=='inner_edge' and cell.get('body')
                cell['color']=(colours[signature] if signature in colours else _inner_colour(cell,old_cells) if inner else
                               _inherited_colour(cell['world'],tuple(surfaces.values()),strict=True))
                if cell['color']<0 and not inner:
                    cell['color']=_oriented_colour(cell['world'],cell.get('panel_role'),old_cells)

    def _commit_region(self,index,candidate):
        """Reject intersecting skins atomically; never erase or move a neighbour."""
        from cube.mixup import skins_cross
        peers=set(self.linked_positions(index));old={};changed={};outside={}
        for bi,block in enumerate(self.blocks):
            for cell in block['cells']:
                if cell['world'] is None:continue
                (old if bi in peers else outside)[polygon_key(cell['world'])]=cell['world']
        for bi in peers:
            for cell in candidate.blocks[bi]['cells']:
                if cell['world'] is not None:changed[polygon_key(cell['world'])]=cell['world']
        # An unchanged skin may already be part of an unfinished observation.
        # Check newly placed skins, including unpainted components, against
        # recorded neighbours. Piece inventory/reachability is checked later.
        for key,world in changed.items():
            if key in old:continue
            for other_key,other in outside.items():
                if key==other_key or skins_cross(((world,0),),((other,0),)):
                    raise ValueError('mixup.entry_neighbour_conflict')
        for bi in peers:self.blocks[bi]=candidate.blocks[bi]

    def restore_region(self,index,blocks):
        """Restore a retained choice, including its colours and orientation."""
        if set(blocks)!=set(self.linked_positions(index)):raise ValueError('observe.invalid')
        candidate=MixupEntryDraft(self.kind,self.state())
        for bi,block in blocks.items():candidate.blocks[bi]=deepcopy(block)
        self._commit_region(index,candidate)

    def assembly_at(self,index):
        """Read the entered physical pieces, independently of scaffold labels."""
        from cube.mixup_assembly import Assembly,AssemblyPiece,assembly_key
        peers=self.linked_positions(index);pieces={}
        for peer in peers:
            block=self.blocks[peer]
            if not block['configured']:return None
            for cell in block['cells']:
                if cell['world'] is None:return None
                identity=_piece_identity(cell)
                piece=pieces.setdefault(identity,{'role':cell.get('panel_role') or 'unknown','panels':{},
                    'body':cell.get('body',()),'direction':cell.get('inner_direction',())})
                piece['panels'][polygon_key(cell['world'])]=cell['world']
        if not pieces:return None
        parts=tuple(AssemblyPiece(p['role'],tuple(p['panels'].values()),0,p['body'],p['direction']) for p in pieces.values())
        return Assembly(assembly_key(parts),self.kind,peers,parts)

    def can_rotate_assembly(self,index):
        assembly=self.assembly_at(index)
        if self.blocks[index]['role']=='corner' or assembly is None:return False
        if all(p.role=='inner_edge' for p in assembly.pieces):
            from cube.mixup_assembly import inner_turn_axis
            try:inner_turn_axis(assembly.pieces)
            except ValueError:return False
        return True

    def rotation_step(self,index):
        """Inner strips use half turns; other input assemblies use quarters."""
        if self.blocks[index]['role']=='inner_edge':return 2
        assembly=self.assembly_at(index)
        return 2 if assembly is not None and all(p.role=='inner_edge' for p in assembly.pieces) else 1

    def rotate_assembly(self,index,quarters,source_key=None):
        """Rotate the observation by 90 degrees; validate the full state later.

        This changes the input draft, not a playable layer. Colours, linked
        faces and each inner-edge bevel rotate as one rigid local assembly.
        """
        candidate=MixupEntryDraft(self.kind,self.state())
        candidate._rotate_assembly(index,quarters,source_key)
        self._commit_region(index,candidate)

    def _rotate_assembly(self,index,quarters,source_key=None):
        if type(quarters) is not int or not self.can_rotate_assembly(index):
            raise ValueError('mixup.entry_composition_first')
        peers=self.linked_positions(index);source=self.blocks[index]
        axis=unit(tuple(sum(CUBE[self.blocks[i]['face']][a] for i in peers) for a in range(3)))
        vertices={polygon_key((p,))[0]:p for i in peers
                  for p in face_world(self.blocks[i]['outline'],self.blocks[i]['face'])}
        assembly=self.assembly_at(index)
        from cube.mixup_assembly import inner_pattern,inner_turn_axis
        if assembly is not None and inner_pattern(assembly.pieces) is not None:
            axis,pivot=inner_turn_axis(assembly.pieces)
        else:pivot=mean(tuple(vertices.values()))
        angle=-quarters*math.pi/2
        def vector(v):return rotate(v,axis,angle)
        def point(p):
            v=vector(tuple(p[a]-pivot[a] for a in range(3)))
            return tuple(v[a]+pivot[a] for a in range(3))
        def polygon(poly):return tuple(point(p) for p in poly)
        turn=(source['rotation']+quarters)%4
        origin=source.get('assembly_source') or source_key
        updates=[]
        for bi in peers:
            block=self.blocks[bi]
            cells=[]
            for old in block['cells']:
                cell=deepcopy(old)
                world=polygon(cell['world'])
                cell.update(world=world,guide=face_world(project(world,block['face']),block['face']),source_slot=None)
                if cell.get('piece_key'):
                    cell['piece_key']=tuple(sorted(polygon_key(polygon(poly)) for poly in cell['piece_key']))
                if cell.get('body'):
                    cell['body']=tuple(polygon(poly) for poly in cell['body'])
                    cell['body_key']=tuple(sorted(polygon_key(poly) for poly in cell['body']))
                if cell.get('inner_direction'):cell['inner_direction']=vector(cell['inner_direction'])
                cells.append(cell)
            updates.append((bi,cells))
        for bi,cells in updates:self.blocks[bi]['cells']=cells
        key=self.assembly_at(index).key
        for peer in peers:self.blocks[peer].update(composition=key,rotation=turn,assembly_source=origin)

    def paint(self,index,child,color):
        if type(color) is not int or not 0<=color<6:raise ValueError('observe.invalid')
        block=self.blocks[index];cell=block['cells'][child]
        if not block['configured'] and cell['world'] is None and block['role']!='corner':
            raise ValueError('mixup.entry_composition_first')
        if cell['world'] is None:
            if block['role']!='corner':raise ValueError('mixup.entry_composition_first')
            cell.update(world=cell['guide'],panel_role='corner')
        signature=polygon_key(cell['world'])
        for other in self.blocks:
            for item in other['cells']:
                if item['world'] is not None and polygon_key(item['world'])==signature:
                    item.update(color=color,source_slot=None)

    def clear_paint(self,index,child):
        cell=self.blocks[index]['cells'][child]
        signature=polygon_key(cell['world']) if cell['world'] is not None else None
        for block in self.blocks:
            for item in block['cells']:
                if item is cell or (signature is not None and item['world'] is not None and polygon_key(item['world'])==signature):
                    item.update(color=-1,source_slot=None)

    def clear_position(self,index):
        for peer in self.linked_positions(index):
            block=self.blocks[peer]
            configured=block['role']=='corner'
            block.update(cells=[_cell(block['outline'],block['face'])],configured=configured,
                         composition='single' if configured else None,rotation=0,assembly_source=None)

    def confirm(self,index,child,world,color):
        from cube.mixup import skins_cross
        if not self.blocks[index]['configured']:raise ValueError('mixup.entry_composition_first')
        signature=polygon_key(world)
        for bi,block in enumerate(self.blocks):
            for ci,cell in enumerate(block['cells']):
                if (bi,ci)==(index,child) or cell['color']<0 or cell['world'] is None:continue
                if polygon_key(cell['world'])==signature:
                    if bi==index:raise ValueError('mixup.entry_duplicate')
                    if cell['color']!=color:raise ValueError('observe.conflict')
                    continue
                if skins_cross(((world,color),),((cell['world'],cell['color']),)):raise ValueError('rigid.overlap')
        self.blocks[index]['cells'][child].update(world=tuple(world),color=color,source_slot=None)

    def observations(self):
        if any(not b['configured'] or any(c['color']<0 or c['world'] is None for c in b['cells']) for b in self.blocks):
            raise ValueError('mixup.entry_incomplete')
        for index,block in enumerate(self.blocks):
            if block['composition'] is None:continue
            for peer in self.linked_positions(index):
                other=self.blocks[peer]
                if peer<=index or other['composition'] is None:continue
                if block['composition'].startswith('assembly_') or other['composition'].startswith('assembly_'):
                    if block['composition']!=other['composition']:raise ValueError('mixup.entry_link_conflict')
                    continue
                expected=sorted(polygon_key(edge_other_side(c['guide'],block['face'],other['face'])) for c in block['cells'])
                if expected!=sorted(polygon_key(c['guide']) for c in other['cells']):
                    raise ValueError('mixup.entry_link_conflict')
        draft=ObservationDraft(self.kind);seen=set();views=[[] for _ in range(6)];roles={};bodies={}
        for block in self.blocks:
            for cell in block['cells']:
                world=cell['world'];color=cell['color'];key=polygon_key(world)
                if (color,key) in seen:continue
                seen.add((color,key));n=normal(world)
                roles[color,key]=cell.get('panel_role')
                bodies[color,key]=cell.get('body_key')
                for face in range(6):
                    if dot(n,CUBE[face])<=EPS:continue
                    views[face].append(Panel(0,0,color,world,project(world,face),
                                            sum(dot(p,CUBE[face]) for p in world)/len(world),n))
        for face,panels in enumerate(views):
            for panel in panels:
                if _visible(panel,panels,face):
                    role=roles[panel.color,polygon_key(panel.world)]
                    draft.views[face].append({'outline':panel.outline,'color':panel.color,'depth':panel.depth,
                                             'preview':panel.world,'region':0,'world_fixed':True,
                                             'roles':(role,) if role else None,
                                             'body_key':bodies[panel.color,polygon_key(panel.world)]})
        # All scaffold cells have been addressed. Visibility and the actual
        # physical piece count are still checked by the observation matcher.
        draft.complete=[True]*6;return draft

    @classmethod
    def from_observations(cls,kind,state):
        """Keep old observations as provisional guides for reconfirmation.

        An old automatic-depth preview is not a uniquely known world pose.
        Preserve its colour suggestion without promoting it to confirmed data.
        """
        result=cls(kind);source=ObservationDraft(kind,state);seen=set();replaced=set()
        for face,items in enumerate(source.views):
            for item in items:
                world=item['preview'];key=(item['color'],polygon_key(world))
                if key in seen:continue
                seen.add(key);point=centre2(project(world,face))
                choices=[(i,b) for i,b in enumerate(result.blocks) if b['face']==face]
                index=next((i for i,b in choices if contains(b['outline'],point)),None)
                if index is None:index=min(choices,key=lambda ib:sum((a-b)**2 for a,b in zip(point,centre2(ib[1]['outline']))))[0]
                block=result.blocks[index]
                if index not in replaced:block['cells']=[];block['configured']=True;replaced.add(index)
                block['cells'].append({'guide':world,'world':None,'color':-1,'source_slot':None,
                    'suggested_color':item['color'],'legacy_observation':deepcopy(item)})
        for block in result.blocks:
            block['composition']=identify_composition(kind,block) if block['configured'] else None
        return result

    @classmethod
    def from_cube(cls,cube):
        from cube.mixup_assembly import inner_direction
        result=cls(cube.puzzle_kind)
        for b in result.blocks:b['cells']=[];b['configured']=True
        for home,pose in enumerate(cube.frames):
            slots=iter(cube.geometry.pieces[home])
            piece_key=tuple(sorted(polygon_key(world) for world,color in cube.placed_faces(home) if color>=0))
            panels=tuple(world for world,color in cube.placed_faces(home) if color>=0)
            body=tuple(world for world,color in cube.placed_faces(home)) if cube.solids[home].role=='inner_edge' else ()
            positions=_piece_positions(cube.puzzle_kind,panels,cube.solids[home].role,body)
            direction=inner_direction(cube,home)
            for world,color in cube.placed_faces(home):
                if color<0:continue
                slot=next(slots);n=normal(world)
                index=max(positions,key=lambda i:dot(n,CUBE[result.blocks[i]['face']]))
                result.blocks[index]['cells'].append({'guide':world,'world':world,'color':color,'source_slot':slot,
                    'panel_role':cube.solids[home].role,'piece_key':piece_key,'body':body,'inner_direction':direction,
                    'body_key':tuple(sorted(polygon_key(p) for p in body)) if body else None})
        for block in result.blocks:block['composition']=identify_composition(cube.puzzle_kind,block)
        return result
