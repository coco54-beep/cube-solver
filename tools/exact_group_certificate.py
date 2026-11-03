"""Incremental deterministic BSGS certificate for offline material tables.

This stores permutations, not solver words. Every added residual belongs to
the supplied generators; exhaustive Schreier checks certify the order.
NumPy only accelerates permutation composition and inversion.
"""
import math
import numpy as np


class Certificate:
    def __init__(self,degree,base,track_words=False):
        self.degree=degree;self.base=tuple(base)
        self.identity=np.arange(degree,dtype=np.int32)
        self.gens=[[] for _ in self.base]
        self.trans=[{b:self.identity} for b in self.base]
        self.inverses=[{b:self.identity} for b in self.base]
        self._known=set()
        self.track_words=track_words;self.words={}
        if track_words:
            from solver.polyhedral import Word
            self.path_words=[{b:Word()} for b in self.base]

    def strip(self,perm,start=0):
        residual,level,word=self._strip(perm,start,None)
        return residual,level

    def _strip(self,perm,start,word):
        residual=np.asarray(perm,dtype=np.int32)
        if np.array_equal(residual,self.identity):return residual,len(self.base),word
        for level in range(start,len(self.base)):
            beta=int(residual[self.base[level]])
            inverse=self.inverses[level].get(beta)
            if inverse is None:return residual,level,word
            if beta!=self.base[level]:
                residual=inverse[residual]
                if word is not None:word=word.then(self.path_words[level][beta].inverse())
        if not np.array_equal(residual,self.identity):
            raise ValueError('Certificate base omits a moved point')
        return residual,len(self.base),word

    def contains(self,perm):return self.strip(perm)[1]==len(self.base)

    def _refresh(self,level):
        paths={self.base[level]:self.identity};queue=[self.base[level]]
        if self.track_words:
            from solver.polyhedral import Word
            words={self.base[level]:Word()}
        for beta in queue:
            path=paths[beta]
            for gen in self.gens[level]:
                gamma=int(gen[beta])
                if gamma not in paths:
                    paths[gamma]=gen[path];queue.append(gamma)
                    if self.track_words:words[gamma]=words[beta].then(self.words[gen.tobytes()])
        self.trans[level]=paths
        self.inverses[level]={beta:np.argsort(path).astype(np.int32) for beta,path in paths.items()}
        if self.track_words:self.path_words[level]=words

    def _remember(self,perm,first,last,word=None):
        key=perm.tobytes()
        if key in self._known:raise ValueError('Nontrivial residue was already certified')
        self._known.add(key)
        if self.track_words:
            if word is None:raise ValueError('Missing certificate witness')
            self.words[key]=word
        for level in range(first,last+1):
            self.gens[level].append(perm);self._refresh(level)

    def add(self,perm,word=None):
        if self.track_words and word is None:raise ValueError('Missing input witness')
        residue,last,word=self._strip(perm,0,word)
        if last==len(self.base):return False
        self._remember(residue,0,last,word)
        level=last
        while level>=0:
            added=False
            for beta,path in tuple(self.trans[level].items()):
                for gen in tuple(self.gens[level]):
                    gamma=int(gen[beta]);schreier=self.inverses[level][gamma][gen[path]]
                    word=(self.path_words[level][beta].then(self.words[gen.tobytes()]).then(self.path_words[level][gamma].inverse())
                          if self.track_words else None)
                    residue,last,word=self._strip(schreier,level+1,word)
                    if last==len(self.base):continue
                    self._remember(residue,level+1,last,word)
                    level=last;added=True;break
                if added:break
            if not added:level-=1
        return True

    @property
    def order(self):return math.prod(len(row) for row in self.trans)
