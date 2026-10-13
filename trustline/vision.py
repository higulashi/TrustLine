"""Scanline border pairing. Only measured pixels enter the controller.

The renderer's ground lookup is a synthetic calibrated projection, not an
MT9V034 lens model. Real frames require measured per-row ground calibration.
"""
import numpy as np
W,H=188,120
ROWS=np.linspace(112,10,12,dtype=int)
FORWARD=.18+1.15*((H-1-np.arange(H))/(H-1))**1.5
HALF_SPAN=.12+.65*FORWARD
LATERAL=(np.arange(W)-(W-1)/2)[None,:]/((W-1)/2)*HALF_SPAN[:,None]

def extract_reference(frame):
    if frame.shape!=(H,W):
        raise ValueError('expected a 120x188 grayscale frame')
    points=[]
    for row in ROWS:
        line=frame[row].astype(float)
        # Relative darkness withstands mild brightness changes; deep shadows
        # can still create missing or false pairs and are benchmarked honestly.
        mask=line < min(100,np.percentile(line,85)*.46)
        pad=np.r_[False,mask,False].astype(int)
        starts=np.flatnonzero(np.diff(pad)==1);ends=np.flatnonzero(np.diff(pad)==-1)
        centers=[(a+b-1)/2 for a,b in zip(starts,ends) if 1<=b-a<=14]
        best=None
        for i,a in enumerate(centers):
            for b in centers[i+1:]:
                width=(b-a)/((W-1)/2)*HALF_SPAN[row]
                expected=.44
                if .30<width<.63:
                    score=abs(width-expected)
                    if best is None or score<best[0]:
                        center=((a+b)/2-(W-1)/2)/((W-1)/2)*HALF_SPAN[row]
                        best=(score,center,max(.1,1-score/.22))
        if best is not None:
            points.append((float(FORWARD[row]),best[1],best[2]))
    return points

def extract(frame):
    from .native import extract_native
    return extract_native(frame)

def from_opencv(path):
    """Read a saved real frame; calibration still has to be replaced first."""
    import cv2
    image=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
    if image is None:raise ValueError('cannot read image')
    if image.shape!=(H,W):raise ValueError('capture at 188x120; do not silently resize calibration')
    return image
