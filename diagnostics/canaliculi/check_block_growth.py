import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'src'); sys.path.insert(0,'.')
from count_lacunae import load_channel
import config
import canaliculi_v1 as can
import exclusion_mask as excl
import segment_lacunae_v2 as seg2
import gap_bridging as gb
from skimage import morphology
from skimage.io import imsave

print("STEP 2 CHECK -- block new connections inside flagged structures")
print("Required: vertical segment gone in the x555_y500 crop; skeleton length OUTSIDE flagged unchanged.\n")
print(f'{"image":22s} {"block":>6s} {"skel_total":>11s} {"in_flagged":>11s} {"OUTSIDE":>11s} {"bridges":>8s}')
out = config.DIAGNOSTICS_DIR / 'round2' / 'step2'; out.mkdir(parents=True, exist_ok=True)

for stem in ("542 WT  2_z06c1-2","542 WT  2_z18c1-2","682_z08c1-2","682_z23c-2","682_z29c1-3","543-2"):
    p = Path(f'data/WT/{stem}.tif')
    display, ch = load_channel(p)
    _d2, labels, kept, _t = seg2.segment_image(p)
    lac_mask, lac_id = can.build_lacuna_maps(labels, kept)
    flagged,_o = excl.flagged_structures(ch)
    res = {}
    for block in (False, True):
        ng = flagged if block else None
        cand, t_lo = can.canaliculi_candidate_mask(ch, lac_mask, "tophat", "hysteresis", ng)
        sk = morphology.skeletonize(cand)
        pre = can.preprocess_channel(ch, "tophat")
        forb = lac_mask | (flagged if block else np.zeros_like(flagged))
        br = gb.find_bridges(sk, pre, t_lo, forb)
        if br:
            cand = gb.apply_bridges(cand, br); sk = morphology.skeletonize(cand)
        res[block] = (sk, len(br))
        tot = int(sk.sum()); inf = int((sk & flagged).sum())
        print(f'{stem[:22]:22s} {str(block):>6s} {tot:11d} {inf:11d} {tot-inf:11d} {len(br):8d}')
    a, b = res[False][0], res[True][0]
    outside_a = int((a & ~flagged).sum()); outside_b = int((b & ~flagged).sum())
    verdict = "UNCHANGED" if outside_a == outside_b else f"CHANGED by {outside_b-outside_a}"
    print(f'{"":22s} -> outside-flagged skeleton: {verdict}\n')
    if stem == "542 WT  2_z06c1-2":
        r0,c0 = 500-128, 555-128
        panels=[]
        for block in (False, True):
            sk = res[block][0]
            crop = (sk[r0:r0+256, c0:c0+256]*255).astype(np.uint8)
            panels.append(np.stack([crop]*3,-1))
        fl = (flagged[r0:r0+256, c0:c0+256]*120).astype(np.uint8)
        panels.append(np.stack([fl]*3,-1))
        sep = np.full((256,4,3),128,np.uint8)
        imsave(out/'542_z06_x555_y500_block_off_vs_on.png',
               np.hstack([panels[0],sep,panels[1],sep,panels[2]]), check_contrast=False)
        print(f"  saved {out}/542_z06_x555_y500_block_off_vs_on.png")
        print("  panels: block OFF | block ON | flagged region\n")
