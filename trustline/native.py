"""Compile once; simulations call the actual C implementation through ctypes."""
import ctypes as C
from pathlib import Path
import os
import shutil
import subprocess
import sys
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]
class Point(C.Structure):
    _fields_ = [(x,C.c_float) for x in ('s','y','quality')]
class State(C.Structure):
    _fields_ = [(x,C.c_float) for x in ('previous_k','blind_time')]+[('has_track',C.c_int)]
class Command(C.Structure):
    _fields_ = [(x,C.c_float) for x in ('steering','speed','lookahead','confidence','sigma_k','curvature')] + [('mode',C.c_int)]
MODES = {'fixed':0,'regulated':1,'trustline':2,'no_risk':3,'no_visibility':4,'matched_policy':5}

def build():
    dest = ROOT/'build'/('trustline.dll' if os.name=='nt' else 'libtrustline.so')
    dest.parent.mkdir(exist_ok=True)
    if dest.exists() and dest.stat().st_mtime > max((ROOT/'core'/f).stat().st_mtime for f in ('trustline.c','trustline.h')):
        return dest
    zig = os.environ.get('TRUSTLINE_ZIG') or shutil.which('zig')
    if not zig:
        try:
            import ziglang
            zig = str(Path(next(iter(ziglang.__path__)))/('zig.exe' if os.name=='nt' else 'zig'))
        except ImportError:
            pass
    cc = [zig,'cc'] if zig else [os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc') or 'clang']
    subprocess.run(cc+['-std=c99','-O2','-Wall','-Wextra','-Werror','-shared',str(ROOT/'core'/'trustline.c'),'-o',str(dest)]+([] if os.name=='nt' else ['-fPIC','-lm']),check=True)
    return dest

class Controller:
    def __init__(self,mode='trustline'):
        self.lib=C.CDLL(str(build()))
        self.lib.tl_init.argtypes=[C.POINTER(State)]
        self.lib.tl_step.argtypes=[C.POINTER(State),C.POINTER(Point),C.c_int,C.c_float,C.c_float,C.c_int]
        self.lib.tl_step.restype=Command
        self.state=State();self.lib.tl_init(C.byref(self.state));self.mode=MODES[mode]
    def step(self,points,speed,dt=.02):
        if len(points)>16:
            raise ValueError('C core accepts at most 16 points')
        arr=(Point*len(points))(*(Point(*p) for p in points))
        return self.lib.tl_step(C.byref(self.state),arr,len(points),speed,dt,self.mode)

@lru_cache(maxsize=1)
def extractor_lib():
    lib=C.CDLL(str(build()))
    lib.tl_extract.argtypes=[C.POINTER(C.c_ubyte),C.c_int,C.POINTER(Point)]
    lib.tl_extract.restype=C.c_int
    return lib

def extract_native(frame):
    if frame.shape!=(120,188) or str(frame.dtype)!='uint8' or not frame.flags['C_CONTIGUOUS']:
        raise ValueError('expected contiguous uint8 120x188 grayscale')
    out=(Point*16)()
    n=extractor_lib().tl_extract(frame.ctypes.data_as(C.POINTER(C.c_ubyte)),188,out)
    return [(out[i].s,out[i].y,out[i].quality) for i in range(n)]
