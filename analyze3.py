# -*- coding: utf-8 -*-
import json
from collections import Counter, defaultdict

with open('baccarat-data-2026-07-09.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

all_logs = []
for sidx, s in enumerate(data['completedSessions']):
    for log in s['sessionLog']:
        log['sessionIdx'] = sidx
        all_logs.append(log)

# Parse recommendation
for log in all_logs:
    rec = log.get('recommendation')
    if rec and isinstance(rec, dict):
        log['rec_action'] = rec.get('action')
        log['rec_strategy'] = rec.get('strategy')
        log['rec_confidence'] = rec.get('confidence')
        log['rec_tier'] = rec.get('tier')
        log['rec_betAmount'] = rec.get('betAmount')
        log['is_custom'] = rec.get('isCustom', False)
        log['is_override'] = rec.get('isUserOverride', False)
    else:
        log['rec_action'] = None
        log['rec_strategy'] = None

total = len(all_logs)
results = Counter(log['actualResult'] for log in all_logs)
total_profit = sum(log['profitImpact'] for log in all_logs)

print('=' * 70)
print('百家乐数据深度分析')
print('=' * 70)

# 0. Basic
print(f'\n基础数据: 总{total}局 B{results["B"]} P{results["P"]} T{results["T"]}')
print(f'总盈亏: {total_profit:,}')
actions = Counter(log['rec_action'] for log in all_logs if log['rec_action'])
print(f'推荐方向: B={actions["B"]} P={actions["P"]}')

# 1. Follow vs Not
print('\n' + '=' * 70)
print('1. 推荐跟随 vs 不跟 对比')
print('=' * 70)

follow = {'count':0,'w':0,'l':0,'t':0,'p':0}
nofollow = {'count':0,'w':0,'l':0,'t':0,'p':0}
norec = {'count':0,'w':0,'l':0,'t':0,'p':0}

for log in all_logs:
    pi = log['profitImpact']
    followed = log.get('userFollowed', False)
    has_rec = log['rec_action'] is not None
    d = norec if not has_rec else (follow if followed else nofollow)
    d['count'] += 1
    d['p'] += pi
    if pi > 0: d['w'] += 1
    elif pi < 0: d['l'] += 1
    else: d['t'] += 1

for name, d in [('跟随推荐', follow), ('不跟推荐', nofollow), ('自由下注(无推荐)', norec)]:
    v = d['w'] + d['l']
    wr = f'{d["w"]/v*100:.1f}%' if v>0 else '-'
    avg = d['p']/d['count'] if d['count']>0 else 0
    print(f'\n  {name}:')
    print(f'    局数: {d["count"]:>4}, 赢{d["w"]:>3} 输{d["l"]:>3} 和{d["t"]:>2}')
    print(f'    胜率: {wr}, 总盈亏: {d["p"]:>+10,}, 平均: {avg:>+.0f}')

# 2. Strategy
print('\n' + '=' * 70)
print('2. 各策略表现')
print('=' * 70)
sstat = defaultdict(lambda: {'c':0,'w':0,'l':0,'t':0,'p':0,'fc':0,'fp':0})
for log in all_logs:
    strat = log.get('rec_strategy')
    if not strat: continue
    pi = log['profitImpact']
    s = sstat[strat]
    s['c'] += 1
    s['p'] += pi
    if pi > 0: s['w'] += 1
    elif pi < 0: s['l'] += 1
    else: s['t'] += 1
    if log.get('userFollowed', False):
        s['fc'] += 1
        s['fp'] += pi

print(f'  {"策略":>20} | {"局":>4} | {"赢":>3} | {"输":>3} | {"胜率":>5} | {"盈亏":>10} | {"跟":>3} | {"跟盈亏":>10}')
print('  ' + '-' * 75)
for strat, s in sorted(sstat.items(), key=lambda x: -x[1]['c']):
    v = s['w'] + s['l']
    wr = f'{s["w"]/v*100:.0f}%' if v>0 else '-'
    print(f'  {strat:>20} | {s["c"]:>4} | {s["w"]:>3} | {s["l"]:>3} | {wr:>5} | {s["p"]:>+10,} | {s["fc"]:>3} | {s["fp"]:>+10,}')

# 3. Tier
print('\n' + '=' * 70)
print('3. 层级分析')
print('=' * 70)
tstat = defaultdict(lambda: {'c':0,'w':0,'l':0,'t':0,'p':0})
for log in all_logs:
    tier = log.get('rec_tier', '无')
    pi = log['profitImpact']
    s = tstat[tier]
    s['c'] += 1
    s['p'] += pi
    if pi > 0: s['w'] += 1
    elif pi < 0: s['l'] += 1
    else: s['t'] += 1

for tier, s in sorted(tstat.items(), key=lambda x: -x[1]['c']):
    v = s['w'] + s['l']
    wr = f'{s["w"]/v*100:.1f}%' if v>0 else '-'
    avg = s['p']/s['c'] if s['c']>0 else 0
    print(f'  {tier:>16}: {s["c"]:>4}局 赢{s["w"]:>3} 输{s["l"]:>3} 胜率{wr:>5} 盈亏{s["p"]:>+10,} 均{avg:>+.0f}')

# 4. Confidence
print('\n' + '=' * 70)
print('4. 信心度分析')
print('=' * 70)
cstat = defaultdict(lambda: {'c':0,'w':0,'l':0,'t':0,'p':0,'tb':0})
for log in all_logs:
    conf = log.get('rec_confidence', '无')
    pi = log['profitImpact']
    ba = log.get('rec_betAmount', 0) or 0
    s = cstat[conf]
    s['c'] += 1; s['p'] += pi; s['tb'] += abs(ba)
    if pi > 0: s['w'] += 1
    elif pi < 0: s['l'] += 1
    else: s['t'] += 1

order = ['低', '中', '中-高', '高', '极高', '无']
for conf in order:
    if conf in cstat:
        s = cstat[conf]
        v = s['w'] + s['l']
        wr = f'{s["w"]/v*100:.1f}%' if v>0 else '-'
        ab = s['tb']/s['c'] if s['c']>0 else 0
        print(f'  {conf:>6}: {s["c"]:>4}局 赢{s["w"]:>3} 输{s["l"]:>3} 胜率{wr:>5} 盈亏{s["p"]:>+10,} 均注{ab:>8.0f}')

# 5. Session details (high stakes)
print('\n' + '=' * 70)
print('5. 高额会话注码趋势(会话18-24)')
print('=' * 70)
for si, s in enumerate(data['completedSessions']):
    if si < 17: continue
    slog = s['sessionLog']
    sp = sum(l['profitImpact'] for l in slog)
    print(f'\n  会话#{si+1} (总{sp:+,}):')
    for ci in range(0, len(slog), 10):
        chunk = slog[ci:min(ci+10, len(slog))]
        cp = sum(l['profitImpact'] for l in chunk)
        bets = [abs(l['profitImpact']) for l in chunk if l['profitImpact'] != 0]
        ba = sum(bets)/len(bets) if bets else 0
        cw = sum(1 for l in chunk if l['profitImpact'] > 0)
        cl = sum(1 for l in chunk if l['profitImpact'] < 0)
        print(f'    第{ci+1:>2}-{min(ci+10, len(slog)):>2}局: 均注{ba:>10.0f} | {cw}赢{cl}输 | {cp:>+10,}')

# 6. Summary of key findings
print('\n' + '=' * 70)
print('核心发现')
print('=' * 70)

# Total bets placed
total_bets = sum(1 for l in all_logs if l['profitImpact'] != 0)
total_skipped = sum(1 for l in all_logs if l['profitImpact'] == 0)
print(f'\n下注局: {total_bets}, 跳过: {total_skipped}')

# Win/loss
total_wins = sum(1 for l in all_logs if l['profitImpact'] > 0)
total_losses = sum(1 for l in all_logs if l['profitImpact'] < 0)
total_ties_bet = sum(1 for l in all_logs if l['profitImpact'] == 0)
print(f'赢:{total_wins} 输:{total_losses} 和/跳:{total_ties_bet}')
wr_all = total_wins/(total_wins+total_losses)*100 if (total_wins+total_losses) > 0 else 0
print(f'整体胜率(去和): {wr_all:.1f}%')

# How many times user overrode
override_count = sum(1 for l in all_logs if l.get('is_override', False) and l.get('rec_action'))
print(f'\n用户手动覆盖推荐: {override_count}次')

# Follow rate (when there IS a recommendation)
rec_total = sum(1 for l in all_logs if l['rec_action'] is not None)
rec_followed = sum(1 for l in all_logs if l['rec_action'] is not None and l.get('userFollowed', False))
print(f'\n有推荐的局: {rec_total}, 其中跟随: {rec_followed} ({rec_followed/rec_total*100:.1f}%)' if rec_total > 0 else '')

# Scared to follow? - analysis of override patterns
overrides = [l for l in all_logs if l.get('is_override', False) and l['rec_action']]
override_actions = Counter(l['rec_action'] for l in overrides)
print(f'\n自定义覆盖的局: {len(overrides)}')
print(f'  覆盖时推荐方向: B={override_actions["B"]} P={override_actions["P"]}')
if overrides:
    ov_profit = sum(l['profitImpact'] for l in overrides)
    ov_wins = sum(1 for l in overrides if l['profitImpact'] > 0)
    ov_losses = sum(1 for l in overrides if l['profitImpact'] < 0)
    print(f'  覆盖后盈亏: {ov_profit:+,}, 赢{ov_wins}输{ov_losses}')
