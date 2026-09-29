import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0,'src'); sys.path.insert(0,'.')
from count_lacunae import load_channel
import canaliculi_v1 as can, exclusion_mask as excl, segment_lacunae_v2 as seg2, gap_bridging as gb
from skimage import morphology
from scipy import ndimage as ndi

RING = 30
rows_out = []
print("Per interior lacuna: roots vs LOCAL canaliculi-mask density and LOCAL raw signal")
print("(ring = 30px band just outside the lacuna body; both normalised to the image)")
print(f'{"image":22s} {"n_int":>5s} {"<3 roots":>8s} {"med roots":>9s}')
for p in sorted(Path('data/WT').glob('*.tif')):
    display, ch = load_channel(p)
    _d2, labels, kept, _t = seg2.segment_image(p)
    lac_mask, lac_id = can.build_lacuna_maps(labels, kept)
    flagged,_o = excl.flagged_structures(ch)
    cand, t_lo = can.canaliculi_candidate_mask(ch, lac_mask, can.PREPROCESS_MODE, can.THRESHOLD_MODE, flagged)
    sk = morphology.skeletonize(cand)
    pre = can.preprocess_channel(ch, can.PREPROCESS_MODE)
    br = gb.find_bridges(sk, pre, t_lo, lac_mask | flagged)
    if br: sk = morphology.skeletonize(gb.apply_bridges(cand, br))
    dist = ndi.distance_transform_edt(lac_mask == 0)
    G,_s = can.build_network_graph(sk); can.clean_network_graph(G, dist)
    cell_ids = list(range(1, len(kept)+1))
    can.attach_lacunae(G, dist, can.nearest_lacuna_map(lac_id)[1], cell_ids)
    img_mask_density = float(cand[~lac_mask].mean())
    img_med_raw = float(np.median(ch[~lac_mask]))
    nlow = 0; roots_all=[]
    for lid,(reg,ob) in enumerate(kept, start=1):
        if ob: continue
        roots = len(can.cell_root_lengths(G, lid))
        roots_all.append(roots)
        body = lac_id == lid
        ring = (ndi.distance_transform_edt(~body) <= RING) & ~lac_mask
        md = float(cand[ring].mean()) if ring.any() else 0.0
        raw = float(np.median(ch[ring])) if ring.any() else 0.0
        rows_out.append((p.stem, lid, roots, md/img_mask_density, raw/img_med_raw))
        if roots < 3: nlow += 1
    print(f'{p.stem[:22]:22s} {len(roots_all):5d} {nlow:8d} {np.median(roots_all):9.1f}')

arr = np.array([(r[2], r[3], r[4]) for r in rows_out])
low = arr[arr[:,0] < 3]; hi = arr[arr[:,0] >= 3]
print(f"\nPOOLED interior lacunae n={len(arr)}:  with <3 roots: {len(low)} ({100*len(low)/len(arr):.1f}%)")
print(f'{"group":14s} {"n":>4s} {"local mask density /img":>24s} {"local raw /img median":>23s}')
for name, g in (("<3 roots", low), (">=3 roots", hi)):
    if len(g)==0: print(f'{name:14s} {0:4d}  (none)'); continue
    print(f'{name:14s} {len(g):4d} {g[:,1].mean():24.3f} {g[:,2].mean():23.3f}')
if len(low):
    print(f"\n  lacunae with <3 roots, individually:")
    for r in rows_out:
        if r[2] < 3:
            print(f"    {r[0][:22]:22s} id={r[1]:3d} roots={r[2]} local_mask={r[3]:.3f}x local_raw={r[4]:.3f}x")
print(f"\ncorrelation roots vs local mask density: {np.corrcoef(arr[:,0], arr[:,1])[0,1]:+.3f}")
print(f"correlation roots vs local raw signal   : {np.corrcoef(arr[:,0], arr[:,2])[0,1]:+.3f}")
