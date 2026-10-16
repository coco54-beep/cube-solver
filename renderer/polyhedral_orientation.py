"""Adjacent-face entry navigation with a single hinge rotation per step."""
import math
from functools import lru_cache

from cube.polyhedral import body_faces, cross, dot, key, unit
from renderer.mat4 import Mat4


@lru_cache(maxsize=16)
def _route(faces):
    vertices=[set(face) for face in faces]
    neighbours=[tuple(j for j,other in enumerate(vertices)
                      if j!=i and len(face & other)>=2)
                for i,face in enumerate(vertices)]
    path=[0]
    used={0}
    visits=0

    def search():
        nonlocal visits
        visits+=1
        if visits>50000:
            return False
        if len(path)==len(faces):
            return 0 in neighbours[path[-1]]
        remaining=set(range(len(faces)))-used
        available=remaining | {path[-1],0}
        # Every remaining face needs two edges in the completed cycle.
        # Prune isolated pockets before spending the search budget inside them.
        if any(sum(q in available for q in neighbours[p])<2 for p in remaining):
            return False
        reached={path[-1]}
        frontier=[path[-1]]
        while frontier:
            for q in neighbours[frontier.pop()]:
                if q in available and q not in reached:
                    reached.add(q);frontier.append(q)
        if not available<=reached:
            return False
        choices=sorted((p for p in neighbours[path[-1]] if p not in used),
                       key=lambda p:(sum(q not in used for q in neighbours[p]),p))
        for p in choices:
            used.add(p);path.append(p)
            if search():
                return True
            path.pop();used.remove(p)
        return False

    if search():
        return tuple(path)
    # A connected non-Hamiltonian shell can still be traversed without jumps.
    path=[0];used={0}
    def walk(p):
        for q in neighbours[p]:
            if q not in used:
                used.add(q);path.append(q)
                walk(q);path.append(p)
    walk(0)
    if len(used)!=len(faces):
        raise ValueError('Disconnected face adjacency')
    return tuple(path[:-1]) if len(path)>1 else (0,)


class PolyhedralOrientation:
    def __init__(self,spec,roll=0):
        self.normals=spec.normals
        self.sequence=_route(tuple(tuple(key(p) for p in face) for face in body_faces(spec)))
        self.index=0
        normal=unit(self.normals[0])
        yaw=math.atan2(normal[0],normal[2])
        right=(math.cos(yaw),0.,-math.sin(yaw))
        up=cross(normal,right)
        angle=math.radians(roll)
        right,up=(tuple(r*math.cos(angle)+u*math.sin(angle) for r,u in zip(right,up)),
                  tuple(u*math.cos(angle)-r*math.sin(angle) for r,u in zip(right,up)))
        self.world=Mat4((right[0],up[0],normal[0],0,
                         right[1],up[1],normal[1],0,
                         right[2],up[2],normal[2],0,0,0,0,1))

    def transition(self,direction):
        index=(self.index+(1 if direction>0 else -1))%len(self.sequence)
        normal=unit(self.world.transform(*self.normals[self.sequence[index]]))
        axis=cross(normal,(0.,0.,1.))
        length=math.sqrt(dot(axis,axis))
        angle=math.degrees(math.atan2(length,normal[2]))
        return index,angle,unit(axis) if length>1e-10 else (1.,0.,0.)

    def commit(self,index,angle,axis):
        self.world=Mat4.rotation_axis(angle,axis)*self.world
        self.index=index
        return self.sequence[index]
