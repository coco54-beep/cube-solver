"""Ownership and shape checks for six-face drafts shared by input/camera/twist."""
def cache_key(kind,n):
    from cube.appearance import VARIANTS
    if kind in VARIANTS or kind=='pandora':return kind
    return n if kind in (None,'cube') else (kind,n)


def fits(facelets,n,partial=False):
    from app.constants import FACES
    if not isinstance(facelets,dict) or not facelets:return False
    if not partial and not all(face in facelets for face in FACES):return False
    return all(isinstance(grid,(list,tuple)) and len(grid)==n
               and all(isinstance(row,(list,tuple)) and len(row)==n
                       and all(isinstance(col,str) for col in row) for row in grid)
               for face,grid in facelets.items() if face in FACES) and any(face in FACES for face in facelets)


def saved_draft(app,key,n,allow_legacy=True):
    """A global draft is authoritative only for its owner (or a fitting legacy draft)."""
    recent=getattr(app,'facelets_input',None);owner=getattr(app,'facelets_input_key',None)
    if (owner==key or owner is None and allow_legacy) and fits(recent,n):return recent
    cache=getattr(app,'facelets_cache',{})
    stored=cache.get(key) if isinstance(cache,dict) else None
    return stored if fits(stored,n) else None


def remember_recent(app,facelets):
    app.facelets_input=facelets
    app.facelets_input_key=cache_key(getattr(app,'puzzle_kind','cube'),app.n)
