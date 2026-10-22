"""Traditional main-model picking for Mixup assemblies and panel input."""
from cube.articulated_observation import normal,polygon_key
from cube.polyhedral import add,scale,cross,dot,unit,mean
from renderer.square1_view import Square1View


def _direction_marks(world,direction,slot,home):
    if not direction:return ()
    n=normal(world);tangent=add(direction,scale(n,-dot(direction,n)))
    if dot(tangent,tangent)<1e-12:return ()
    tangent=unit(tangent);side=cross(n,tangent);centre=add(mean(world),scale(n,.007))
    length=min(dot(add(a,scale(b,-1)),add(a,scale(b,-1)))**.5 for a,b in zip(world,world[1:]+world[:1]))*.25
    def point(along,across):return add(add(centre,scale(tangent,length*along)),scale(side,length*across))
    stem=(point(-1,-.09),point(.35,-.09),point(.35,.09),point(-1,.09))
    head=(point(.15,-.45),point(1,0),point(.15,.45))
    return tuple((p,n,-1,slot,0,home,1) for p in (stem,head))


class MixupEntryView(Square1View):
    draft=None;piece_filter=None;candidate=None;linked_selection=()
    def _is_recorded(self,slot):return True
    def _is_selected(self,slot):return slot==self.selected or slot in self.linked_selection
    def _inset(self,points):return points
    def _surface_depth_bias(self,color):
        return 0.
    def set_draft(self,draft,force=False):
        if force or self.draft is not draft:
            # A delayed redraw must not hit old child indices after a change
            # from two components to three/four, or after undo/scramble.
            self._polygons=[]
        self.draft=draft
    def _surfaces(self,cube):
        if self.draft is None:return ()
        result=[];seen=set()
        for bi,block in enumerate(self.draft.blocks):
            cells=block['cells']
            for ci,cell in enumerate(cells):
                slot=bi*1024+ci
                world=cell['world'] or cell['guide'];color=cell['color'] if cell['color']>=0 else -2
                if self.candidate and self.candidate[0]==(bi,ci):world=self.candidate[1];color=-2
                key=(color,polygon_key(world))
                if key in seen:continue
                seen.add(key);n=normal(world);centre=mean(world)
                panel=tuple(add(add(centre,scale(add(p,scale(centre,-1)),.95)),scale(n,.0015)) for p in world)
                # Use the recorded rigid body: a radial cone loses the wedge's
                # bevel and makes a real half turn look like an arrow-only edit.
                # The scaffold still needs a closed, pickable placeholder when
                # no physical body has been entered yet.
                housing=-2 if color==-2 else -1
                body=cell.get('body') if not self.candidate or self.candidate[0]!=(bi,ci) else ()
                if body:
                    result.extend((poly,normal(poly),housing,slot,0,bi,1) for poly in body)
                else:
                    result.append((world,n,housing,slot,0,bi,1))
                    back=tuple(scale(p,.35) for p in world)
                    result.append((tuple(reversed(back)),scale(n,-1),housing,slot,0,bi,1))
                    for i,(p,q) in enumerate(zip(world,world[1:]+world[:1])):
                        side=(p,back[i],back[(i+1)%len(back)],q)
                        side_n=cross(add(side[1],scale(p,-1)),add(side[2],scale(p,-1)))
                        if dot(side_n,side_n)>1e-14:result.append((side,unit(side_n),housing,slot,0,bi,1))
                result.append((panel,n,color,slot,0,bi,1))
                if not body:result.extend(_direction_marks(world,cell.get('inner_direction'),slot,bi))
        return tuple(result)
