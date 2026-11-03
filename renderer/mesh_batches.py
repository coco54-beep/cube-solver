"""Triangle-preserving batches for GLES unsigned-short vertex indices."""


def triangle_batches(vertices,indices,stride=7,limit=60000):
    """Yield local vertex/index buffers without splitting any triangle.

    Small scenes keep their existing buffers. Large scenes remap only the
    vertices referenced by each batch, preserving order and vertex attributes.
    """
    if stride<1 or limit<3 or limit>65535 or len(vertices)%stride or len(indices)%3:
        raise ValueError('Invalid triangle buffer layout')
    count=len(vertices)//stride
    if any(type(i) is not int or i<0 or i>=count for i in indices):
        raise ValueError('Triangle index outside its vertex buffer')
    if not indices:return
    if count<=limit:
        yield vertices,indices;return
    mapping={};local_vertices=[];local_indices=[]
    for offset in range(0,len(indices),3):
        triangle=indices[offset:offset+3]
        missing=set(triangle)-mapping.keys()
        if len(mapping)+len(missing)>limit:
            yield local_vertices,local_indices
            mapping={};local_vertices=[];local_indices=[]
        for source in triangle:
            target=mapping.get(source)
            if target is None:
                target=len(mapping);mapping[source]=target
                local_vertices.extend(vertices[source*stride:(source+1)*stride])
            local_indices.append(target)
    if local_indices:yield local_vertices,local_indices
