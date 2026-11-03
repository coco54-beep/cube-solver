"""Reviewable outer shell from Drawing3, without inventing rigid connections.

Each face patch is an observation region, never a separately movable cubie.
The OBJ is a surface reference; it does not define an internal mechanism.
"""
import sys,json,math,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import LineCollection
from matplotlib.font_manager import FontProperties
from cube.polyhedral import CUBE,add,scale,cross,dot,triangulate
from tools.cad_face_regions import curves_from_entities,face_regions,with_central_radius

OUT=Path('reports/expansion/2026-10-29/twins-dwg')


def face_point(normal,point):
    u=next(p for p in CUBE if dot(p,normal)==0);v=cross(normal,u)
    return add(normal,add(scale(u,point[0]),scale(v,point[1])))


def export_shell(regions,output):
    vertices={};objects=[]
    for f,n in enumerate(CUBE):
        for i,region in enumerate(regions):
            points=tuple(face_point(n,p) for p in list(region.exterior.coords)[:-1]);triangles=triangulate(points,n);faces=[]
            for triangle in triangles:
                ids=[]
                for p in triangle:
                    p=tuple(round(v,8) for v in p)
                    if p not in vertices:vertices[p]=len(vertices)+1
                    ids.append(vertices[p])
                faces.append(tuple(ids))
            objects.append((f,i,faces))
    lines=['# Drawing3 CAD outer surface only; patches are not rigid cubies.',
           '# Normalized cube side 2; original CAD face side 10.',
           'mtllib twins-cad-shell.mtl']
    lines.extend('v '+' '.join(f'{v:.8f}' for v in p) for p in vertices)
    for f,i,faces in objects:
        lines.extend((f'g face_{f+1}_patch_{i+1}',f'usemtl face_{f+1}'))
        lines.extend('f '+' '.join(map(str,ids)) for ids in faces)
    output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    colors=((.98,.40,.04),(.96,.85,.04),(.05,.18,.85),(.84,.05,.05),(.96,.96,.96),(.04,.65,.13))
    output.with_suffix('.mtl').write_text('\n'.join(f'newmtl face_{i+1}\nKd {r} {g} {b}\n' for i,(r,g,b) in enumerate(colors)),encoding='utf-8')
    return dict(face_patches=len(objects),triangles=sum(len(faces) for f,i,faces in objects),vertices=len(vertices))


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--central-radius',type=float,help='Provisional centre radius in side-ten CAD units; source is unchanged')
    parser.add_argument('--output-dir',type=Path,default=OUT)
    args=parser.parse_args();OUT=args.output_dir
    OUT.mkdir(parents=True,exist_ok=True)
    data=json.loads(Path('tests/data/twins_face_curves.json').read_text())
    original=curves_from_entities(data['entities']);curves=original
    if args.central_radius is not None:curves=with_central_radius(original,args.central_radius,data['width'])
    regions,paths=face_regions(curves)
    if len(regions)!=32:raise ValueError('Radius changes the 32-region face topology; preview not exported')
    # Check every drawn cut participates in a closed face, including the four
    # separate arcs of the central circle. No silently discarded dangles.
    from shapely.geometry import LineString
    from shapely.ops import unary_union,polygonize_full
    polygons,cuts,dangles,invalid=polygonize_full(unary_union([LineString(p) for h,p in paths]))
    if max(cuts.length,dangles.length,invalid.length)>1e-7:raise ValueError('Drawing contains unclosed cuts')
    font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
    fig,ax=plt.subplots(figsize=(8,8));ax.set_aspect('equal');ax.set_xlim(-1.08,1.08);ax.set_ylim(-1.08,1.08);ax.axis('off')
    for i,p in enumerate(regions):
        ax.add_patch(Polygon(list(p.exterior.coords),facecolor=plt.get_cmap('tab20')(i%20),edgecolor='none',alpha=.42))
        label=p.representative_point();ax.text(label.x,label.y,str(i+1),ha='center',va='center',fontsize=9)
    ax.add_collection(LineCollection([p for h,p in paths],colors='#17232d',linewidths=1.0))
    ax.set_title(f'图纸分区：{len(regions)} 区（编号不代表独立转块）',fontproperties=font,fontsize=14)
    fig.savefig(OUT/'face-numbered.png',dpi=150,bbox_inches='tight');plt.close(fig)

    fig,ax=plt.subplots(figsize=(8,8));ax.set_aspect('equal');ax.axis('off')
    def project(p):return (.85*(p[0]-p[1]),.42*(p[0]+p[1])+.98*p[2])
    colors={4:'#f4f5f7',3:'#db2828',2:'#2445c0'}
    for f in (2,4,3):
        n=CUBE[f];corners=tuple(project(face_point(n,p)) for p in ((-1,-1),(1,-1),(1,1),(-1,1)))
        ax.add_patch(Polygon(corners,facecolor=colors[f],edgecolor='#1b2632',linewidth=1.6))
        ax.add_collection(LineCollection([tuple(project(face_point(n,p)) for p in points) for h,points in paths],
                                         colors='#17232d',linewidths=.95))
    ax.autoscale_view();ax.margins(.06)
    ax.set_title('双子星：按单面图纸重复六面的外壳预览',fontproperties=font,fontsize=13)
    fig.text(.5,.04,'外壳参考，内部连接与拧动规则尚未定义',fontproperties=font,fontsize=11,ha='center',color='#576776')
    fig.savefig(OUT/'twins-cad-shell.png',dpi=140,bbox_inches='tight',facecolor='white');plt.close(fig)
    summary=export_shell(regions,OUT/'twins-cad-shell.obj')
    summary.update(source_sha256=data['source_sha256'],arcs=12,internal_lines=6,patches_per_face=len(regions),
                   area=sum(p.area for p in regions),unclosed_length=max(cuts.length,dangles.length,invalid.length),
                   mechanism_verified=False,all_lines_confirmed_seams=True,six_faces_assumed_identical=True,
                   central_radius=next(c.radius for c in curves if c.kind=='arc' and c.a==(0.,0.))*data['width']/2,
                   central_radius_status='provisional_user_uncertain',source_geometry_overridden=args.central_radius is not None)
    (OUT/'face-regions.json').write_text(json.dumps(dict(source=data['source_sha256'],
        regions=[dict(id=i+1,outline=list(p.exterior.coords)[:-1],label=list(p.representative_point().coords)[0],area=p.area)
                 for i,p in enumerate(regions)]),indent=2),encoding='utf-8')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # Illustrative alternatives only: these are not measured physical sizes.
    fig,axes=plt.subplots(1,3,figsize=(14,5))
    for ax,radius in zip(axes,(2.6,2.8,3.0)):
        variant=with_central_radius(original,radius,data['width']);vr,vp=face_regions(variant)
        if len(vr)!=32:raise ValueError('Comparison radius changes topology')
        central_handles={c.handle for c in variant if c.kind=='arc' and c.a==(0.,0.)}
        ax.set_aspect('equal');ax.axis('off');ax.set_xlim(-1.04,1.04);ax.set_ylim(-1.04,1.04)
        ax.add_collection(LineCollection([p for h,p in vp],colors=['#d33a35' if h in central_handles else '#536471' for h,p in vp],linewidths=1.2))
        ax.set_title(f'暂定半径 {radius:g} / 面边长 10',fontproperties=font,fontsize=12)
    fig.suptitle('中央四段圆弧联动对比（仅供比例核对，非实测尺寸）',fontproperties=font,fontsize=15)
    fig.tight_layout();fig.savefig(OUT/'radius-comparison.png',dpi=140,bbox_inches='tight');plt.close(fig)
    print(summary)


if __name__=='__main__':main()
