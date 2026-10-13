"""Generate a local GIF from the actual C-controlled closed-loop run."""
from pathlib import Path
import csv
import json
import math
import argparse
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from trustline.simulator import run,center
from trustline.vision import HALF_SPAN,W,H

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=11);ap.add_argument('--scenario',default='mixed');ap.add_argument('--prefix',default='demo');ap.add_argument('--method',default='no_risk');args=ap.parse_args()
    dest=Path('assets');dest.mkdir(exist_ok=True)
    metrics,h=run('s_bend',args.scenario,args.seed,args.method,record=True)
    font=ImageFont.load_default(size=17);small=ImageFont.load_default(size=13)
    frames=[]
    for i in range(0,len(h),8):
        t,x,y,yaw,v,e,L,q,sig,steer,gray,points=h[i]
        canvas=Image.new('RGB',(960,560),'#0b1220');d=ImageDraw.Draw(canvas)
        d.text((24,16),f'TrustLine | observed-horizon smart-car control | {args.method}',font=font,fill='#e8efff')
        d.text((24,43),'Synthetic grayscale images -> scanlines -> portable C controller -> bicycle plant',font=small,fill='#93a5c3')
        camera=Image.fromarray(gray).convert('RGB').resize((376,240))
        canvas.paste(camera,(24,96));d=ImageDraw.Draw(canvas)
        for s,l,quality in points:
            from trustline.vision import FORWARD
            row=int(np.argmin(abs(FORWARD-s)));px=((l/HALF_SPAN[row])*(W-1)/2+(W-1)/2)*2+24
            py=row*2+96
            d.ellipse((px-3,py-3,px+3,py+3),fill='#40eab2')
        d.text((24,348),'Green: measured border-pair centers',font=small,fill='#40eab2')
        # Local world overview. Curve is ground truth for display only.
        panel=Image.new('RGB',(476,240),'#0b1220');pd=ImageDraw.Draw(panel)
        def world(xx,yy):return ((xx-(x-1))*115,194-(yy-y)*115)
        xs=np.linspace(x-1,x+3,150);left=[];right=[]
        for xx in xs:
            yy=float(center(xx,'s_bend'));left.append(world(xx,yy+.22));right.append(world(xx,yy-.22))
        pd.polygon(left+right[::-1],fill='#24344e')
        pd.line(left,fill='#cbd5e1',width=2);pd.line(right,fill='#cbd5e1',width=2)
        trajectory=[world(r[1],r[2]) for r in h[max(0,i-250):i+1]]
        if len(trajectory)>1:pd.line(trajectory,fill='#40eab2',width=3)
        car=world(x,y);tip=world(x+.17*math.cos(yaw),y+.17*math.sin(yaw))
        pd.ellipse((car[0]-6,car[1]-6,car[0]+6,car[1]+6),fill='#ffce73');pd.line([car,tip],fill='#ffce73',width=4)
        canvas.paste(panel,(460,96))
        d.text((460,348),'World view (ground truth shown only for evaluation)',font=small,fill='#93a5c3')
        stats=[f'Time: {t:.2f} s    Speed: {v:.2f} m/s',f'Cross-track error: {e*100:.1f} cm',f'Lookahead: {L:.2f} m    Confidence proxy: {q:.2f}',f'Curvature uncertainty proxy: {sig:.3f} 1/m',f'Steering command: {math.degrees(steer):.1f} deg']
        for j,line in enumerate(stats):d.text((24,392+j*26),line,font=font,fill='#e8efff')
        d.text((620,462),f'Seed {args.seed} | {args.scenario} | {metrics["status"]}',font=small,fill='#ffce73')
        d.text((620,488),'C99 core | no heap | 12 scanlines',font=small,fill='#40eab2')
        d.text((620,512),'Simulation only; no real-car claim',font=small,fill='#93a5c3')
        frames.append(canvas)
    frames[0].save(dest/f'{args.prefix}.gif',save_all=True,append_images=frames[1:],duration=160,loop=0)
    frames[len(frames)//2].save(dest/f'{args.prefix}_preview.png')
    (dest/f'{args.prefix}_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    with (dest/f'{args.prefix}_trace.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['time_s','x_m','y_m','yaw_rad','speed_m_s','error_m','lookahead_m','confidence_proxy','sigma_k_proxy','steering_rad'])
        writer.writerows(r[:10] for r in h)
    print(metrics)
if __name__=='__main__':main()
