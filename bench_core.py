"""Desktop wall-time, including Python/ctypes overhead. Not MCU profiling."""
import json
import platform
import time
from pathlib import Path
import numpy as np
from trustline.simulator import Vehicle,render,slope
from trustline.vision import extract
from trustline.native import Controller
import math

def main():
    image=render(Vehicle(yaw=math.atan(slope(0,'s_bend'))),'s_bend','mixed',0,11)
    points=extract(image);ctl=Controller()
    for _ in range(100):ctl.step(points,1);extract(image)
    timing={}
    for name,fn in [('c_extract_with_ctypes',lambda:extract(image)),('c_control_with_ctypes',lambda:ctl.step(points,1))]:
        samples=[]
        for _ in range(2000):
            t=time.perf_counter_ns();fn();samples.append((time.perf_counter_ns()-t)/1000)
        timing[name]={'median_us':float(np.median(samples)),'p95_us':float(np.percentile(samples,95)),'samples':len(samples)}
    result={'platform':platform.platform(),'python':platform.python_version(),'numpy':np.__version__,'timing':timing,'scope':'desktop measured wall-time including Python wrappers; no MCU timing claim'}
    Path('results/desktop_timing.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
