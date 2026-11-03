"""Cheap local feedback; full legality is still checked before solving."""
from collections import Counter,defaultdict
from cube.coordinates import pos_from_rc
from cube.colors import VALID_COLORS


class EntryIssue(ValueError):
    def __init__(self,key,locations):
        super().__init__(key);self.locations=locations


class FaceletChecks:
    def __init__(self,n):
        self.n=n;self.values={};self.counts=Counter();self.pieces=defaultdict(list)
        self.problems={};self.checked=0
        for f in 'UDFBRL':
            for r in range(n):
                for c in range(n):self.pieces[pos_from_rc(n,f,r,c)].append((f,r,c))

    def update(self,data):
        try:
            if any(len(data[f]) != self.n or any(len(row) != self.n for row in data[f])
                   for f in 'UDFBRL'):
                raise IndexError
        except (KeyError, IndexError, TypeError):
            # A resize callback can arrive before the draft is rebuilt.
            self.values.clear()
            self.counts.clear()
            self.problems.clear()
            self.checked = 0
            return []
        dirty=set();self.checked=0
        for cells in self.pieces.values():
            for loc in cells:
                f,r,c=loc;value=data[f][r][c];old=self.values.get(loc,'')
                if value!=old:
                    if old:self.counts[old]-=1
                    if value:self.counts[value]+=1
                    self.values[loc]=value;dirty.add(pos_from_rc(self.n,*loc))
        opposites=({'W','Y'},{'R','O'},{'B','G'})
        for pos in dirty:
            self.checked+=1;cells=self.pieces[pos];colours=[self.values.get(c,'') for c in cells if self.values.get(c,'')]
            key=('entry.preview_repeat' if len(set(colours))<len(colours) else
                 'entry.preview_opposite' if any(pair<=set(colours) for pair in opposites) else None)
            if key:self.problems[pos]=(key,tuple(cells),{})
            else:self.problems.pop(pos,None)
        result=list(self.problems.values())
        for colour in VALID_COLORS:
            if self.counts[colour]>self.n*self.n:
                cells=tuple(loc for loc,value in self.values.items() if value==colour)
                result.append(('entry.preview_count',cells,dict(colour=colour,count=self.counts[colour],expected=self.n*self.n)))
        return result
