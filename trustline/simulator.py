"""Closed-loop kinematic bicycle, grayscale rendering and actuator lag.

Ground truth is used by the renderer/metrics, never supplied to Controller.
Noise is indexed by elapsed time to make disturbances shared across methods.
"""
from dataclasses import dataclass
import math
import numpy as np
from .vision import FORWARD,LATERAL,W,H,extract
from .native import Controller

DT=.02
TRACKS={'s_bend':(.60,.72,.16,1.65),'tight':(.48,1.10,.13,2.25),'sweep':(.85,.48,.16,1.1)}
SCENARIOS=('clean','shadow','dropout','distractor','mixed')
@dataclass
class Vehicle:
    x:float=0
    y:float=0
    yaw:float=0
    speed:float=.6
    steer:float=0

def center(x,track):
    a,b,c,d=TRACKS[track]
    return a*np.sin(b*x)+c*np.sin(d*x)
def slope(x,track):
    a,b,c,d=TRACKS[track]
    return a*b*np.cos(b*x)+c*d*np.cos(d*x)
def noise_at(t,seed):
    return np.random.default_rng(seed*1000003+int(round(t/DT)))

def render(v,track,scenario,t,seed):
    s=FORWARD[:,None];l=LATERAL
    wx=v.x+math.cos(v.yaw)*s-math.sin(v.yaw)*l
    wy=v.y+math.sin(v.yaw)*s+math.cos(v.yaw)*l
    distance=(wy-center(wx,track))/np.sqrt(1+slope(wx,track)**2)
    gray=np.where(abs(distance)<.22,220.,115.)
    gray=np.where(abs(abs(distance)-.22)<.012,24.,gray)
    rng=noise_at(t,seed)
    if scenario in ('shadow','mixed'):
        band=np.abs(np.mod(wx-3.1+1.3,2.6)-1.3)<.30
        gray=np.where(band,gray*.28,gray)
    if scenario in ('dropout','mixed'):
        # Physical short gaps in the track borders; never full hidden oracle.
        missing=(np.mod(wx+seed*.08,3.1)>.9)&(np.mod(wx+seed*.08,3.1)<1.08)
        gray=np.where(missing,210.,gray)
        # Deterministic camera outage lasting 80 ms every 2 seconds.
        if .8<(t%2)<.88:gray[:]=165
    if scenario in ('distractor','mixed'):
        # Thin false marking on the track; pairing has no ground truth hint.
        bad=(np.abs(distance-.06*np.sin(4*wx))<.009)&(np.mod(wx,2.8)>.5)&(np.mod(wx,2.8)<1.1)
        gray=np.where(bad,18.,gray)
    gray+=rng.normal(0,2 if scenario=='clean' else 6,gray.shape)
    gray*=.88+.10*np.sin(t*.7+seed)
    return np.clip(gray,0,255).astype(np.uint8)

def advance(v,cmd):
    # 90ms servo response plus 3 rad/s rate limit. Shared plant, all methods.
    v.steer+=float(np.clip((cmd.steering-v.steer)*DT/.09,-3*DT,3*DT))
    accel=np.clip((cmd.speed-v.speed)/.18,-2.,1.5)
    v.speed=max(0,v.speed+float(accel)*DT)
    v.x+=v.speed*math.cos(v.yaw)*DT
    v.y+=v.speed*math.sin(v.yaw)*DT
    v.yaw+=v.speed/.26*math.tan(v.steer)*DT

def run(track='s_bend',scenario='mixed',seed=11,method='trustline',record=False,max_time=30):
    ctl=Controller(method);rng=np.random.default_rng(seed)
    v=Vehicle(y=float(rng.uniform(-.03,.03)),yaw=float(math.atan(slope(0,track))+rng.uniform(-.025,.025)))
    history=[];errors=[];turns=[];velocities=[];laststeer=0;lastprogress=0;stall=0;status='timeout'
    for step in range(int(max_time/DT)):
        t=step*DT;frame=render(v,track,scenario,t,seed);points=extract(frame)
        cmd=ctl.step(points,v.speed,DT)
        error=float((v.y-center(v.x,track))/math.sqrt(1+slope(v.x,track)**2))
        errors.append(error);turns.append(abs(v.steer-laststeer));velocities.append(v.speed);laststeer=v.steer
        if record:
            history.append((t,v.x,v.y,v.yaw,v.speed,error,cmd.lookahead,cmd.confidence,cmd.sigma_k,cmd.steering,frame.copy(),points))
        # Body half-width 6cm + center error must fit inside 22cm half-track.
        if abs(error)>.16:status='off_track';break
        if v.x>=12:status='finished';break
        stall=stall+DT if v.x-lastprogress<.0002 else 0
        lastprogress=v.x
        if stall>2:status='stalled';break
        advance(v,cmd)
    metrics={'track':track,'scenario':scenario,'seed':seed,'method':method,'status':status,
             'time_s':round(t,3),'progress_x_m':round(v.x,4),'rmse_m':float(np.sqrt(np.mean(np.square(errors)))),
             'max_error_m':float(np.max(np.abs(errors))),'steer_total_variation_rad':float(sum(turns)),
             'mean_speed_m_s':float(np.mean(velocities))}
    return metrics,history
