import argparse
import csv
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from trustline.simulator import run,TRACKS,SCENARIOS

METHODS=('fixed','regulated','trustline','no_risk','no_visibility','matched_policy')
def task(args):
    return run(*args)[0]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');ap.add_argument('--dev',action='store_true');ap.add_argument('--out',default='results');ap.add_argument('--workers',type=int,default=1);ap.add_argument('--seed-start',type=int,default=101);args=ap.parse_args()
    dest=Path(args.out);dest.mkdir(exist_ok=True,parents=True)
    rows=[]
    # 11-13 are development seeds; 101-108 are held-out reported seeds.
    seeds=[11] if args.quick or args.dev else list(range(args.seed_start,args.seed_start+8))
    tracks=['s_bend'] if args.quick else list(TRACKS)
    from trustline.native import build
    build() # build before processes launch, avoiding compiler races
    jobs=[(track,scenario,seed,method) for track in tracks for scenario in SCENARIOS for seed in seeds for method in METHODS]
    if args.workers>1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for i,metrics in enumerate(pool.map(task,jobs)):
                rows.append(metrics)
                if (i+1)%20==0:print(f'{i+1}/{len(jobs)} runs',flush=True)
    else:
        for i,job in enumerate(jobs):
            rows.append(task(job))
            if (i+1)%5==0:print(f'{i+1}/{len(jobs)} runs',flush=True)
    with (dest/'runs.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,rows[0].keys());writer.writeheader();writer.writerows(rows)
    summary={}
    for method in METHODS:
        sub=[r for r in rows if r['method']==method];finished=[r for r in sub if r['status']=='finished']
        summary[method]={'runs':len(sub),'finished':len(finished),'completion_rate':len(finished)/len(sub),
                         'mean_finish_time_s':sum(r['time_s'] for r in finished)/len(finished) if finished else None,
                         'mean_rmse_m_all':sum(r['rmse_m'] for r in sub)/len(sub)}
    (dest/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (dest/'protocol.json').write_text(json.dumps({'seeds':seeds,'tracks':tracks,'scenarios':SCENARIOS,'methods':METHODS,'dt_s':.02,'limit_s':30,'finish_x_m':12,'offtrack_error_m':.16,'test_type':'synthetic grayscale closed-loop kinematic bicycle'},indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
