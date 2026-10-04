#!/usr/bin/env python3
"""Step counter v1: editable solid CAD + STL + native OpenSCAD export.

Units mm. Assembly X=right, Y=up, Z=front-to-back. Frontmost accents Z=0.
Run: python generate_model.py [parameters.json]. Python is the master parametric
source; the matching .scad is generated from the same constructive solid tree.
No guessed PCB mounting-hole patterns: adjustable PCB edge retainers instead.
"""
from pathlib import Path
from itertools import combinations
import json, sys, hashlib
import numpy as np
import manifold3d as m
import trimesh

ROOT=Path(__file__).resolve().parents[1]
P=json.loads(Path(sys.argv[1]).read_text() if len(sys.argv)>1 else (ROOT/'cad/parameters.json').read_text())
N=int(P['quality_segments']); m.set_circular_segments(N)
def fmt(v):
    return json.dumps(v.tolist() if isinstance(v,np.ndarray) else v,separators=(',',':'))
class CSG:
    def __init__(self,solid,code): self.solid,self.code=solid,code
    def __add__(self,o): return CSG(self.solid+o.solid,'union(){'+self.code+o.code+'}')
    def __sub__(self,o): return CSG(self.solid-o.solid,'difference(){'+self.code+o.code+'}')
    def __xor__(self,o): return CSG(self.solid^o.solid,'intersection(){'+self.code+o.code+'}')
    def move(self,p): return CSG(self.solid.translate(p),'translate('+fmt(p)+'){'+self.code+'}')
    def scale(self,p): return CSG(self.solid.scale(p),'scale('+fmt(p)+'){'+self.code+'}')
def box(size,c=(0,0,0)):
    return CSG(m.Manifold.cube(size,True).translate(c),'translate('+fmt(c)+') cube('+fmt(size)+',center=true);')
def cyl(r,h,c=(0,0,0)):
    return CSG(m.Manifold.cylinder(h,r,circular_segments=N,center=True).translate(c),'translate('+fmt(c)+') cylinder(h='+str(h)+',r='+str(r)+',center=true);')
def ell(r,c):
    return CSG(m.Manifold.sphere(1,N).scale(r).translate(c),'translate('+fmt(c)+') scale('+fmt(r)+') sphere(r=1);')
def union(*items):
    return CSG(m.Manifold.batch_boolean([a.solid for a in items],m.OpType.Add),'union(){'+''.join(a.code for a in items)+'}')
def hull(*items):
    return CSG(m.Manifold.compose([a.solid for a in items]).hull(),'hull(){'+''.join(a.code for a in items)+'}')
def rr(w,h,d,r,z,cxy=(0,0)):
    x,y=cxy
    return hull(*[cyl(r,d,(x+sx*(w/2-r),y+sy*(h/2-r),z)) for sx in [-1,1] for sy in [-1,1]])
def slab(z0,z1): return box((200,200,z1-z0),(0,0,(z0+z1)/2))
def slot(length,d,h,c):
    x,y,z=c; off=(length-d)/2
    return hull(cyl(d/2,h,(x-off,y,z)),cyl(d/2,h,(x+off,y,z)))
def depthbox(w,h,z0,z1,cxy=(0,0)):
    return box((w,h,z1-z0),(cxy[0],cxy[1],(z0+z1)/2))

bw,bh,bd,r,w=[P[k] for k in ['body_width','body_height','body_depth','corner_radius','wall']]
fz,fi,fs,rs,ri=[P[k] for k in ['front_face_z','front_inside_z','front_split_z','rear_split_z','rear_inside_z']]
e=P['edge_softening']; tiny=.02
# Chamfered outer edges retain a broad flat printable face; R24 frontal corners.
outer=union(hull(rr(bw-2*e,bh-2*e,tiny,r-e,fz+tiny/2),rr(bw,bh,tiny,r,fi-tiny/2)),
            rr(bw,bh,ri-fi,r,(ri+fi)/2),
            hull(rr(bw,bh,tiny,r,ri+tiny/2),rr(bw-2*e,bh-2*e,tiny,r-e,bd-tiny/2)))
cavity=rr(bw-2*w,bh-2*w,ri-fi,r-w,(ri+fi)/2)
front=(outer^slab(fz,fs))-cavity
back=(outer^slab(rs,bd))-cavity
# Mating shoulders touch axially. Only XY lip clearance is provided.
lc=P['lip_clearance_per_side']; ld=P['lip_depth']; lw=P['lip_wall']
ow,oh,orr=bw-2*w-2*lc,bh-2*w-2*lc,r-w-lc
def lip(z0,z1):
    return rr(ow,oh,z1-z0,orr,(z0+z1)/2)-rr(ow-2*lw,oh-2*lw,z1-z0+1,orr-lw,(z0+z1)/2)
front=front+lip(fs,fs+ld)
back=back+lip(rs-ld,rs)
# Small integral shoulders join the inset lips to their cover walls.
front=front+(rr(bw,bh,.6,r,fs-.3)-rr(ow-2*lw,oh-2*lw,1,orr-lw,fs-.3))
back=back+(rr(bw,bh,.6,r,rs+.3)-rr(ow-2*lw,oh-2*lw,1,orr-lw,rs+.3))
middle=rr(bw,bh,rs-fs,r,(rs+fs)/2)-rr(bw-2*w,bh-2*w,rs-fs+1,r-w,(rs+fs)/2)
# Integral loop is flush to front print plane of middle shell, avoiding a floating ledge.
ly=P['loop_center_y']; lt=P['loop_thickness']; lz=fs+lt/2
neck=rr(16,4,lt,1.8,lz,(0,bh/2))
loop=union(cyl(P['loop_outer_diameter']/2,lt,(0,ly,lz)),neck)
loop=loop-cyl(P['loop_hole_diameter']/2,lt+2,(0,ly,lz))
middle=middle+loop

clear=P['m2_clearance_diameter']; pilot=P['m2_tap_pilot_diameter']
closures=[(sx*P['closure_screw_x'],sy*P['closure_screw_y']) for sx in [-1,1] for sy in [-1,1]]
postend=P['closure_post_end_z']; pstart=P['closure_pilot_start_z']
for x,y in closures:
    # Forward lid owns continuous posts. Rear fasteners pass through rear cover.
    front=front+cyl(3,postend-fi+.1,(x,y,(postend+fi-.1)/2))
    front=front-cyl(pilot/2,postend-pstart+.2,(x,y,(postend+pstart+.2)/2))
    # Relieve the rear registration lip around the long posts.
    back=back-cyl(3.3,postend+1,(x,y,(postend+1)/2))
    back=back+cyl(3.4,ri-postend+.1,(x,y,(ri+postend+.1)/2))
    back=back-cyl(clear/2,bd-postend+2,(x,y,(bd+postend)/2))
    hz=P['rear_head_seat_z']
    back=back-cyl(P['m2_head_recess_diameter']/2,bd-hz+1,(x,y,(bd+hz+1)/2))

# TFT edge support: assumed front PCB plane, no holes through the board.
tpz=P['tft_pcb_front_z_assumed']; tpb=tpz+P['tft_pcb_thickness_assumed']
tx=P['tft_retainer_screw_x']; ty=P['tft_retainer_screw_y']; ey=P['tft_edge_support_y']; ix=P['tft_edge_support_inner_x']
for side in [-1,1]:
    for y in [-ey,ey]:
        front=front+depthbox(4,6,fi-.1,tpz,(side*(ix+2),y))
    for y in [-ty,ty]:
        front=front+cyl(3.1,tpb-fi+.1,(side*tx,y,(tpb+fi-.1)/2))
        front=front-cyl(pilot/2,tpb-fi-.6,(side*tx,y,(tpb+fi+.8)/2))
    # Independent carrier screw pillars provide an unobstructed screwdriver path.
    cp=P['carrier_front_z']
    cx=P['carrier_screw_x']
    front=front+cyl(3.1,cp-fi+.1,(side*cx,0,(cp+fi-.1)/2))
    front=front-cyl(pilot/2,cp-fi-.6,(side*cx,0,(cp+fi+.8)/2))

ww,wh=P['window_width_height']; wc=P['window_center_xy']; wr=P['window_corner_radius']
front=front-rr(ww,wh,fi-fz+2,wr,(fi+fz)/2,wc)
# A shallow reveal outside the through-window makes an editable bezel border.
front=front-rr(ww+1.6,wh+1.6,.35,wr+.8,fz+.125,wc)

def smile(z,backface=False):
    ybase=-2 if backface else 23.5
    rad=2.1 if backface else 1.2
    pts=[(rad*np.cos(a),ybase-.9*np.sin(a),z) for a in np.linspace(0,np.pi,16)]
    return union(*[hull(cyl(.32,.65,a),cyl(.32,.65,b)) for a,b in zip(pts[:-1],pts[1:])])
for side in [-1,1]:
    front=front-ell((1.05,1.85,.48),(side*10,25,fz+.08))
    back=back-ell((1.35,2,.5),(side*9,1,bd-.08))
    back=back-cyl(2.5,.5,(side*16,-3,bd-.15))
front=front-smile(fz+.15)
back=back-smile(bd-.15,True)

parts={}; notes={}; rots={}; colors={}
def add(name,obj,note,rot=(0,0,0),color='lavender'):
    parts[name]=obj; notes[name]=note; rots[name]=rot; colors[name]=color
# Accents seat in glue pockets and remain within the nominal 70 x 78 x 28 envelope.
for side,word in [(-1,'left'),(1,'right')]:
    c=(side*13,-32.2)
    foot=(ell((5.5,4.5,1.2),(c[0],c[1],1.2))^slab(0,1.2))+cyl(1,.4,(0,0,1.4)).scale((5.5,4.5,1)).move((c[0],c[1],0))
    pocket=cyl(1,.65,(0,0,1.5)).scale((5.65,4.65,1)).move((c[0],c[1],0))
    front=front-pocket
    add('07_foot_'+word,foot,'Lavender shallow foot. Flat glue base down; fit into matching pocket using a small amount of adhesive.',(180,0,0))
    cheek=cyl(3,.8,(side*25,-3,1.2))
    front=front-cyl(3.15,.65,(side*25,-3,1.5))
    add('08_cheek_'+word,cheek,'Lavender cheek insert; flat print. Glue in matching recessed front pocket.')

add('01_front_bezel',front,'Cream front shell with PCB edge seats, closure posts and face engraving. Broad front face down; brim recommended. Paint engraved eyes/smile dark.',color='cream')
add('02_middle_shell',middle,'Lavender ring and integral reinforced loop. Print front mating face down: loop begins on bed. Registration lips are on the covers.')
add('03_back_cover',back,'Cream rear shell with four recessed rear screw heads and engraved face. Exterior face down; supports needed below inset perimeter of curved edge only if slicer flags them.',(180,0,0),'cream')

# Removable, relieved sensor carrier with nominal underside lands at four corners.
cp=P['carrier_front_z']; ct=P['carrier_thickness']; cz=cp+ct
carrier=rr(36,26,ct,2,cp+ct/2)-depthbox(28,18,cp-1,cz+1)
carrier=carrier+depthbox(61,6,cp,cz)
# Restore relief through crossbar: no plate under the sensor's central solder area.
carrier=carrier-depthbox(28,18,cp-1,cz+1)
for side in [-1,1]:
    carrier=carrier-cyl(clear/2,ct+2,(side*P['carrier_screw_x'],0,cp+ct/2))
sz=P['sensor_pcb_front_z_assumed']; sb=sz+P['sensor_pcb_thickness_assumed']; csx=P['sensor_clamp_screw_x']
for side in [-1,1]:
    for sy in [-1,1]:
        carrier=carrier+depthbox(3,3,cz-.1,sz,(side*14.5,sy*9.5))
    carrier=carrier+cyl(2.65,sb-cz+.1,(side*csx,0,(sb+cz-.1)/2))
    carrier=carrier-cyl(pilot/2,sb-cp+.2,(side*csx,0,(sb+cp+.2)/2))
    # Side-locating stops are outside the 31 x 21 clearance footprint.
    for sy in [-1,1]:
        carrier=carrier+depthbox(1.2,3,cz-.1,sb,(side*16.2,sy*7))
add('04_sensor_carrier',carrier,'Removable rear carrier: open 28 x 18 underside relief. Four corner lands support the assumed PCB outline; inspect actual solder/component clearance.')
for side,word in [(-1,'left'),(1,'right')]:
    bar=depthbox(6,36,tpb,tpb+1.6,(side*tx,0))
    bar=bar-cyl(3.4,4,(side*P['carrier_screw_x'],0,tpb+.8))
    for y in [-ey,ey]:
        bar=bar+depthbox(tx+2-ix,5,tpb,tpb+1.6,(side*(ix+tx+2)/2,y))
    for y in [-ty,ty]:
        bar=bar-slot(4,clear,4,(side*tx,y,tpb+.8))
    add('05_tft_retainer_'+word,bar,'Adjustable edge retainer, 1.5 mm nominal PCB overlap. Requires clear PCB margins; never clamp display glass. Flat print.')
    clip=depthbox(9,5,sb,sb+1.6,(side*18,0))
    clip=clip-slot(4,clear,4,(side*csx,0,sb+.8))
    add('06_sensor_clamp_'+word,clip,'Adjustable sensor PCB edge clamp; use M2 x 5 nominal tapped-pilot fastener. Confirm edge is free of components. Flat print.')

# Hardware solids are reservations and explicitly assumed layers, not product CAD.
reserves={}
def reserve(name,obj,note): reserves[name]={'object':obj,'note':note}
tw,th=P['tft_pcb_width_height']
reserve('tft_pcb',depthbox(tw,th,tpz,tpb),'Seller PCB outline; thickness and Z seating plane assumed.')
aw,ah=P['tft_lcd_width_height_assumed']
reserve('tft_lcd',depthbox(aw,ah,P['tft_lcd_front_z_assumed'],tpz),'Assumed LCD/module frame 34 x 46; verify this frame and viewing-area offset.')
aw,ah=P['tft_rear_components_width_height_assumed']
reserve('tft_rear_components',depthbox(aw,ah,tpb,P['tft_rear_limit_z_assumed']),'Assumed component zone; excludes assumed clear PCB retention margins.')
aw,ah=P['tft_header_width_height_assumed']
reserve('tft_header',depthbox(aw,ah,tpb,P['tft_rear_limit_z_assumed'],(0,P['tft_header_center_y_assumed'])),'Low-profile header/wire allowance only; tall straight headers may not fit.')
sw,sh=P['sensor_pcb_width_height_assumed']
reserve('sensor_pcb',depthbox(sw,sh,sz,sb),'Seller envelope interpreted as a PCB outline for this prototype only; verify.')
sw,sh=P['sensor_component_width_height_assumed']
reserve('sensor_components',depthbox(sw,sh,sb,sz+P['sensor_module_height_listed']),'Assumed rear component zone, 10 mm total module height; verify edge clamp clear zones.')

def mesh(s):
    a=s.to_mesh64(); return trimesh.Trimesh(vertices=np.asarray(a.vert_properties)[:,:3],faces=np.asarray(a.tri_verts),process=True)
def normalize(a):
    a=trimesh.Trimesh(vertices=np.asarray(a.vertices,dtype=np.float32),faces=a.faces,process=True)
    a.merge_vertices(digits_vertex=6)
    f=a.faces; a.update_faces((f[:,0]!=f[:,1])&(f[:,1]!=f[:,2])&(f[:,0]!=f[:,2])); a.update_faces(a.unique_faces()); a.remove_unreferenced_vertices()
    assert a.is_watertight and a.is_winding_consistent,'STL precision failure'
    return a
for d in ['stl','cad/assembly','cad/hardware_reference_NOT_FOR_PRINT','renders']:(ROOT/d).mkdir(parents=True,exist_ok=True)
validation={'units':'mm','status':'PRINTABLE FIT-CHECK PROTOTYPE; physical hardware fit unverified','coordinate_system':'X right, Y up, Z front-to-back; front is -Z','parts':{},'reserves':{},'part_intersections':[],'hardware_intersections':[]}
assembly=[]
for name,obj in sorted(parts.items()):
    s=obj.solid
    assert len(s.decompose())==1,(name,'disconnected solid',len(s.decompose()))
    a=normalize(mesh(s)); ap=ROOT/'cad/assembly'/f'{name}_assembled.stl';a.export(ap)
    assembly.append(a)
    orient=s.rotate(rots[name]); printmesh=normalize(mesh(orient))
    translation=[0,0,-float(printmesh.bounds[0,2])];printmesh.apply_translation(translation)
    pp=ROOT/'stl'/f'{name}.stl';printmesh.export(pp)
    validation['parts'][name]={'file':str(pp.relative_to(ROOT)),'assembled_bounds':a.bounds.round(4).tolist(),'print_bounds':printmesh.bounds.round(4).tolist(),'dimensions':a.extents.round(4).tolist(),'print_rotation_xyz_deg':list(rots[name]),'print_translation':translation,'watertight':bool(a.is_watertight),'connected_components':1,'volume_mm3':round(a.volume,4),'faces':len(a.faces),'color':colors[name],'notes':notes[name]}
    print(name, 'OK', a.extents.round(2).tolist(),flush=True)
combined=trimesh.util.concatenate(assembly); combined.export(ROOT/'cad/assembly_for_visualization_NOT_FOR_PRINT.stl')
validation['assembly_bounds']=combined.bounds.round(4).tolist();validation['assembly_dimensions']=combined.extents.round(4).tolist()
for (an,a),(bn,b) in combinations(parts.items(),2):
    vol=max(0.,float((a.solid^b.solid).volume()))
    validation['part_intersections'].append({'part_a':an,'part_b':bn,'intersection_mm3':round(vol,6)})
for rn,rd in reserves.items():
    obj=rd['object']; hm=mesh(obj.solid);hm.export(ROOT/'cad/hardware_reference_NOT_FOR_PRINT'/f'{rn}.stl')
    validation['reserves'][rn]={'bounds':hm.bounds.round(4).tolist(),'note':rd['note']}
    for pn,pobj in parts.items():
        v=max(0.,float((obj.solid^pobj.solid).volume()))
        validation['hardware_intersections'].append({'reserve':rn,'part':pn,'intersection_mm3':round(v,6)})
validation['hardware_pair_intersections']=[]
for (an,a),(bn,b) in combinations(reserves.items(),2):
    v=max(0.,float((a['object'].solid^b['object'].solid).volume()))
    validation['hardware_pair_intersections'].append({'a':an,'b':bn,'intersection_mm3':round(v,6)})
(ROOT/'cad/validation.json').write_text(json.dumps(validation,indent=2)+'\n')
bad=[a for key in ['part_intersections','hardware_intersections','hardware_pair_intersections'] for a in validation[key] if a['intersection_mm3']>.01]

# Export native OpenSCAD source from exactly the same CSG tree.
codes=['// Generated native solid CAD. Edit parameters.json + regenerate for parametric changes.\n// Units mm; physical electronics fit remains unverified.\n',f'$fn={N};\n','part="assembly"; // Or an exact part name below; "print_layout" places each part on Z=0.\n']
for name,obj in sorted(parts.items()): codes.append('module part_'+name+'(){'+obj.code+'}\n')
palette={'cream':[.93,.88,.80],'lavender':[.63,.47,.75]}
codes.append('if(part=="assembly"){\n')
for name in sorted(parts):codes.append('color('+fmt(palette[colors[name]])+') part_'+name+'();\n')
codes.append('}\n')
for i,name in enumerate(sorted(parts)):
    spec=validation['parts'][name]
    codes.append('if(part=="'+name+'") translate('+fmt(spec['print_translation'])+') rotate('+fmt(list(rots[name]))+') part_'+name+'();\n')
codes.append('if(part=="print_layout"){\n')
for i,name in enumerate(sorted(parts)):
    spec=validation['parts'][name];xy=[(i%4)*85,(i//4)*95,spec['print_translation'][2]]
    codes.append('translate('+fmt(xy)+') rotate('+fmt(list(rots[name]))+') part_'+name+'();\n')
codes.append('}\n')
# Low-material fit coupons are separate from the assembled product.
coupons={
    '01_window_alignment': (front ^ slab(fz,fi), 'Front-face slice. Compare actual viewing area with 30 x 37 opening; do not force the glass against the frame.'),
    '02_tft_outline_gauge': (rr(tw+7,th+7,2,3,1)-depthbox(tw+1,th+1,-1,3), '39 x 63 through opening: nominal 0.5 mm clearance per side around the listed 38 x 62 PCB.'),
}
fastener=rr(36,12,6,2,3)
for x,d in [(-12,1.5),(-4,1.6),(4,1.7)]:
    fastener=fastener-cyl(d/2,5,(x,0,4))
fastener=fastener-cyl(clear/2,8,(12,0,3))-cyl(P['m2_head_recess_diameter']/2,2,(12,0,5))
coupons['03_fastener_test']=(fastener,'Left to right when long side horizontal: blind pilot diameters 1.5, 1.6, 1.7; then 2.3 clearance with 4.3 head recess. Default pilot is 1.6. Tap M2 threads and test actual screws.')
(ROOT/'fit-check').mkdir(exist_ok=True)
validation['fit_coupons']={}
for name,(obj,note) in coupons.items():
    a=normalize(mesh(obj.solid)); a.apply_translation([0,0,-float(a.bounds[0,2])])
    dest=ROOT/'fit-check'/f'{name}.stl'; a.export(dest)
    validation['fit_coupons'][name]={'file':str(dest.relative_to(ROOT)),'note':note}
    codes.append('module coupon_'+name+'(){'+obj.code+'}\n')
    codes.append('if(part=="coupon_'+name+'") translate([0,0,'+str(-obj.solid.bounding_box()[2])+']) coupon_'+name+'();\n')
(ROOT/'cad/step_counter.scad').write_text(''.join(codes))
(ROOT/'cad/validation.json').write_text(json.dumps(validation,indent=2)+'\n')
if bad:
    print('INTERFERENCES:',json.dumps(bad,indent=2));sys.exit(2)
print('All solid intersection checks passed. Assembly dimensions:',validation['assembly_dimensions'])
