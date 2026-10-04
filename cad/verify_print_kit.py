"""Independent saved-mesh checks. Run after generate_model.py. Units mm."""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import numpy as np
import trimesh
import manifold3d as m

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/'cad/validation.json').read_text())
results={'status':'Digital geometry verified; physical hardware fit not tested', 'files':{}, 'intersection_checks':[], 'fastener_engagement_mm':{'rear_M2x10':7.2,'TFT_M2x5':3.4,'carrier_M2x6':4.0,'sensor_M2x5':3.4}}
def load(path, on_bed=False):
    a=trimesh.load(path,force='mesh')
    record={'watertight':bool(a.is_watertight),'winding_consistent':bool(a.is_winding_consistent),
            'connected_components':len(a.split(only_watertight=False)),
            'finite_vertices':bool(np.isfinite(a.vertices).all()),'volume_mm3':float(a.volume),
            'dimensions_mm':a.extents.round(4).tolist(),'minimum_z_mm':float(a.bounds[0,2]),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    assert record['watertight'] and record['winding_consistent'] and record['connected_components']==1 and record['finite_vertices'] and a.volume>0,(path,record)
    if on_bed: assert abs(a.bounds[0,2])<1e-5,(path,'not on bed')
    results['files'][str(path.relative_to(ROOT))]=record
    s=m.Manifold(m.Mesh64(np.asarray(a.vertices,dtype=np.float64), np.asarray(a.faces,dtype=np.uint64)))
    assert s.status()==m.Error.NoError,(path,s.status())
    return s

for group in ['parts','fit_coupons']:
    for name,part in spec[group].items(): load(ROOT/part['file'],on_bed=True)
assembly={p.stem:load(p) for p in sorted((ROOT/'cad/assembly').glob('*.stl'))}
hardware={p.stem:load(p) for p in sorted((ROOT/'cad/hardware_reference_NOT_FOR_PRINT').glob('*.stl'))}
def check(a,sa,b,sb):
    volume=max(0.,float((sa^sb).volume()))
    results['intersection_checks'].append({'a':a,'b':b,'overlap_mm3':round(volume,6)})
    assert volume<.01,(a,b,volume)
for (a,sa),(b,sb) in combinations(assembly.items(),2):check(a,sa,b,sb)
for a,sa in assembly.items():
    for b,sb in hardware.items():check(a,sa,b,sb)
for (a,sa),(b,sb) in combinations(hardware.items(),2):check(a,sa,b,sb)
# Actual assembled bounds must match the approved nominal envelope.
bounds=np.array([s.bounding_box() for s in assembly.values()])
dimensions=bounds[:,3:].max(0)-bounds[:,:3].min(0)
assert np.allclose(dimensions,[70,88,28],atol=.01),dimensions
results['assembly_dimensions_mm']=dimensions.round(4).tolist()
# Verify representative screw-head clearance against every solid except the
# surface it seats on. Screw shaft/thread engagement is intentional interference.
heads=[]
for x in [-27.5,27.5]:
    for y in [-23,23]:heads.append((f'closure_head_{x}_{y}',x,y,26))
for x in [-22.5,22.5]:
    for y in [-12,12]:heads.append((f'tft_head_{x}_{y}',x,y,10.8))
for x in [-28,28]:heads.append((f'carrier_head_{x}',x,0,14.3))
for x in [-19.5,19.5]:heads.append((f'sensor_head_{x}',x,0,18.0))
for name,x,y,z in heads:
    head=m.Manifold.cylinder(1.6,1.9,circular_segments=64).translate((x,y,z))
    for pn,ps in assembly.items():check(name,head,pn,ps)
    for hn,hs in hardware.items():check(name,head,hn,hs)
results['screw_head_assumption']='M2 pan head: maximum 3.8 mm diameter x 1.6 mm height; confirm hardware.'
(ROOT/'cad/export-verification.json').write_text(json.dumps(results,indent=2)+'\n')
print(f"PASS: {len(results['files'])} saved meshes; {len(results['intersection_checks'])} intersection checks; overall {dimensions.round(3).tolist()} mm.")
