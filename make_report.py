"""Report every evaluation run; do not treat early-failure RMSE as success."""
import csv
import hashlib
import json
import platform
import statistics
import argparse
from pathlib import Path
from collections import Counter
from PIL import Image,ImageDraw,ImageFont
from run_benchmark import METHODS
from trustline.simulator import TRACKS,SCENARIOS

def mean(values):return statistics.mean(values) if values else None
def fmt(v,n=3):return '-' if v is None else f'{v:.{n}f}'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',default='results/confirmation');args=ap.parse_args()
    root=Path(__file__).resolve().parent
    folder=root/args.input
    rows=list(csv.DictReader((folder/'runs.csv').open(encoding='utf-8')))
    seeds=sorted({int(r['seed']) for r in rows})
    keyed={(r['track'],r['scenario'],r['seed'],r['method']):r for r in rows}
    lines=['# 计算机模拟实验报告','',
           '本报告由 `python make_report.py` 从逐次实验 CSV 自动生成。完整方法使用真实 C99 图像扫描和控制核心。',
           '', '## 协议', '',
           f'本表使用种子 {seeds[0]}–{seeds[-1]}：3 种解析曲线赛道 × 5 种环境 × 8 个种子 × 6 种方法 = 720 次闭环运行。开发调参使用种子 11。种子101–108用于初步评估；据其结果提出简化版优先假设，再使用201–208独立确认。两阶段之间未调整控制器或模拟器参数。预检时修正过阴影生成错误，两个正式阶段均使用修正后的模拟器。',
           '', '车辆运动学自行车模型，轴距 0.26m，控制步长 20ms；含 90ms 舵机一阶响应、3rad/s 转向变化上限、加速/制动限制。图像 188×120，前向映射为合成标定。起始横向位置与朝向有随机扰动。',
           '', '终点为世界坐标 x≥12m，并非绕赛道一圈。横向误差采用解析中心线法线的一阶近似；误差绝对值 >0.16m 计作出界。停滞超过 2s 计作 stalled，30s 内未到终点计作 timeout。停车不是完赛。',
           '', '噪声按种子和经过时间生成；阴影、缺失边线和干扰线在世界坐标中固定。不同方法到达某个位置的时间不同，接受相同的空间环境与同一时间索引的随机噪声机制。',
           '', '## 方法', '',
           '- fixed：固定 0.6125m 前瞻、1.4m/s 目标速度。',
           '- regulated：速度相关前瞻 + 曲率限速；不是完整 Nav2 RPP。',
           '- trustline：转向敏感度候选前瞻 + 外推惩罚 + 观测范围与可信度限速。',
           '- no_risk：去掉候选代价中的不确定性项；保留外推惩罚和限速。',
           '- no_visibility：保留候选前瞻，去掉观测范围与可信度的额外限速。',
           '- matched_policy：固定前瞻，采用与完整方法相同的额外限速、可信度缩放和丢线速度策略。它匹配策略，不保证实际速度序列相同。',
           '', '所有方法共享图像提取、稳健拟合、执行器模型、舵机限幅与丢线超时。',
           '', '## 总体结果', '',
           '| 方法 | 完赛/120 | 出界 | 停滞 | 超时 | 完赛率 | 完赛者平均耗时/s |',
           '|---|---:|---:|---:|---:|---:|---:|']
    summary={}
    for m in METHODS:
        sub=[r for r in rows if r['method']==m];counts=Counter(r['status'] for r in sub)
        times=[float(r['time_s']) for r in sub if r['status']=='finished']
        summary[m]={'status_counts':dict(counts),'completion_rate':counts['finished']/len(sub),'mean_finish_time_s':mean(times)}
        lines.append(f'| {m} | {counts["finished"]}/{len(sub)} | {counts["off_track"]} | {counts["stalled"]} | {counts["timeout"]} | {counts["finished"]/len(sub):.1%} | {fmt(mean(times))} |')
    lines+=['','不同方法的完赛集合不同，上表耗时不能直接用于“快了多少”的结论。失败运行的误差序列较短，也不能用较低 RMSE 证明性能。下面只在两种方法都完赛的同场景同种子上比较。',
            '', '## 配对比较：共同完赛的运行', '',
            '| 比较对象 | 配对数 | TrustLine耗时/s | 对象耗时/s | TrustLine RMSE/cm | 对象RMSE/cm | TrustLine转向总变化/rad | 对象转向总变化/rad |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
    for m in METHODS:
        if m=='trustline':continue
        pairs=[]
        for r in rows:
            if r['method']!='trustline' or r['status']!='finished':continue
            other=keyed[(r['track'],r['scenario'],r['seed'],m)]
            if other['status']=='finished':pairs.append((r,other))
        values=[]
        for field,mult in (('time_s',1),('rmse_m',100),('steer_total_variation_rad',1)):
            values.extend([fmt(mean([float(a[field])*mult for a,b in pairs])),fmt(mean([float(b[field])*mult for a,b in pairs]))])
        lines.append(f'| {m} | {len(pairs)} | '+' | '.join(values)+' |')
    lines+=['','## 场景完赛数（各方法每场景8次）','',
            '| 赛道/环境 | '+' | '.join(METHODS)+' |',
            '|---|'+'---:|'*len(METHODS)]
    grid=[]
    for track in TRACKS:
        for scenario in SCENARIOS:
            nums=[sum(r['status']=='finished' for r in rows if r['method']==m and r['track']==track and r['scenario']==scenario) for m in METHODS]
            lines.append(f'| {track}/{scenario} | '+' | '.join(map(str,nums))+' |')
            grid.append((f'{track}/{scenario}',nums))
    lines+=['','## 解释边界','',
            '- 两阶段整体完赛率：完整方法均为60.0%；Lite（no_risk）第一阶段62.5%、第二阶段59.2%。不确定性代价项的领先关系在确认阶段反转，当前证据不足以证明其稳定独立收益。Lite更简单，但也不能宣称其性能更好。',
            '- 当前结果仅支持这组模拟条件的描述，不证明真实比赛中领先，也不证明方法普遍优于其它控制器。',
            '- matched_policy 和 no_risk 是检验前瞻设计独立价值的关键。若它们表现相近或更好，应如实承认；不能把减速收益全部归功于不确定性项。',
            '- 深阴影、连续误配与急弯可令模型得到一致但错误的路径，残差代理无法可靠识别这种情况。仓库保留失败示例。',
            '- 图像不是物理相机仿真；没有轮胎侧滑、机械间隙、真实曝光、镜头畸变、坡道、十字或环岛。',
            '- 8 个种子是初步重复实验，不代表充分统计证据；赛道和场景是人为指定，未进行大规模独立赛道测试。',
            '', '## 复现', '',
            '```bash', 'python -m unittest discover -s tests -v',
            'python run_benchmark.py --workers 8 --seed-start 101 --out results/evaluation',
            'python run_benchmark.py --workers 8 --seed-start 201 --out results/confirmation',
            'python make_report.py', '```','',
            f'本报告逐次结果见 `{args.input}/runs.csv`；参数协议见同目录 `protocol.json`；代码哈希和运行环境见 `manifest.json`。开发目录记录旧模拟器/旧版本结果，不能和最终评估混用。']
    (root/'docs/EXPERIMENTS.zh-CN.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (folder/'outcomes.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    hashes={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('core','trustline') for p in (root/folder).glob('*') if p.is_file()}
    manifest={'python':platform.python_version(),'platform':platform.platform(),'source_sha256':hashes,'evaluation_runs':len(rows),'notes':'CPU desktop simulation; no target-board timing or real-car validation'}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    im=Image.new('RGB',(1100,700),'#0b1220');d=ImageDraw.Draw(im);font=ImageFont.load_default(size=16);small=ImageFont.load_default(size=14)
    d.text((22,18),f'TrustLine | confirmation seeds {seeds[0]}-{seeds[-1]} | completions out of 8 per cell',font=font,fill='#e8efff')
    d.text((22,48),'Synthetic camera/vehicle model. Stops count as failures. All evaluation seeds included.',font=small,fill='#a1aec5')
    for j,m in enumerate(METHODS):d.text((245+j*137,83),m,font=small,fill='#e8efff')
    for i,(name,nums) in enumerate(grid):
        y=117+i*35;d.text((22,y+5),name,font=small,fill='#e8efff')
        for j,n in enumerate(nums):
            x=240+j*137;color=(int(125-85*n/8),int(47+110*n/8),int(55+62*n/8))
            d.rounded_rectangle((x,y,x+125,y+29),radius=4,fill=color)
            d.text((x+52,y+5),f'{n}/8',font=small,fill='white')
    d.text((22,659),'Raw CSV, paired comparisons and failure analyses are included in the repository.',font=small,fill='#a1aec5')
    im.save(root/'assets/evaluation.png')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
