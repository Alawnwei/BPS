# -*- coding: utf-8 -*-
import json, sys
from collections import defaultdict
from math import sqrt, ceil, erf

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

with open('baccarat-data-2026-07-09.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

all_logs = []
for s in data['completedSessions']:
    for log in s['sessionLog']:
        rec = log.get('recommendation')
        if rec and isinstance(rec, dict):
            log['rec_action'] = rec.get('action')
            log['rec_strategy'] = rec.get('strategy')
        else:
            log['rec_action'] = None
            log['rec_strategy'] = None
        all_logs.append(log)

# Collect stats per strategy
ss = defaultdict(lambda: {'correct':0, 'wrong':0, 'tie':0})
for log in all_logs:
    strat = log.get('rec_strategy')
    ra = log['rec_action']
    r = log['actualResult']
    if not strat or ra is None: continue
    d = ss[strat]
    if r == ra: d['correct'] += 1
    elif r == 'T': d['tie'] += 1
    else: d['wrong'] += 1

BASELINE = 0.50
Z = 1.96

results = []
for strat, d in ss.items():
    n = d['correct'] + d['wrong']
    if n == 0: continue
    win_rate = d['correct'] / n
    se = sqrt(BASELINE * (1 - BASELINE) / n)
    z_score = (win_rate - BASELINE) / se
    p_value = 2 * (1 - 0.5 * (1 + erf(abs(z_score) / sqrt(2))))

    effect_size = abs(win_rate - BASELINE)
    if effect_size > 0.001:
        needed_n = ceil(Z**2 * 0.5 * 0.5 / (effect_size ** 2))
        remaining = max(0, needed_n - n)
        pct_complete = min(100, n / needed_n * 100)
    else:
        needed_n = float('inf')
        remaining = float('inf')
        pct_complete = 0

    if p_value < 0.05:
        if win_rate > BASELINE:
            conclusion = "已证实有效"
        else:
            conclusion = "比随机差(反向有效)"
    elif p_value < 0.20:
        conclusion = "有趋势未证实"
    else:
        conclusion = "数据不足"

    bias = "偏庄" if win_rate > BASELINE else "偏闲"

    results.append({
        'name': strat, 'n': n, 'ties': d['tie'],
        'correct': d['correct'], 'wrong': d['wrong'],
        'win_rate': win_rate * 100, 'z_score': z_score,
        'p_value': p_value, 'needed_n': needed_n,
        'remaining': remaining, 'pct_complete': pct_complete,
        'conclusion': conclusion, 'bias': bias
    })

results.sort(key=lambda x: x['p_value'])

print('=' * 100)
print('各策略统计显著度 & 所需数据量评估')
print('=' * 100)
print(f'  理论基准: 50% (抛硬币)')
print(f'  置信水平: 95% (p<0.05 认为显著)')
print()

header = f"{'策略':>18} | {'局数':>5} | {'对':>4} | {'错':>4} | {'胜率':>6} | {'p值':>8} | {'结论':>16} | {'还差':>6} | {'完成度':>6}"
print(header)
print('-' * len(header))

for r in results:
    p_str = f"{r['p_value']:.4f}" if r['p_value'] >= 0.0001 else "<0.0001"
    if r['remaining'] == float('inf'):
        rem = '  N/A'
        pct = '  N/A'
    else:
        rem = f"{r['remaining']:>5}局"
        pct = f"{r['pct_complete']:.0f}%"

    row = f"{r['name']:>18} | {r['n']:>5} | {r['correct']:>4} | {r['wrong']:>4} | {r['win_rate']:>5.1f}% | {p_str:>8} | {r['conclusion']:>16} | {rem:>6} | {pct:>6}"
    print(row)

print()
print('=' * 100)
print('解读')
print('=' * 100)
print('''
已证实有效     - 胜率显著高于50%，策略可信任
比随机差       - 胜率显著低于50%，反着用可能更好
有趋势未证实   - 已出现偏离但样本不够，需继续积累
数据不足       - 偏差太小或局数太少，无法判断
''')

# 需要更多数据的策略
print()
print('+' + '=' * 60 + '+')
print('| 最有希望但还差一点数据的策略')
print('+' + '=' * 60 + '+')
promising = [r for r in results if r['p_value'] > 0.05 and r['p_value'] < 0.30 and r['win_rate'] > 50]
promising.sort(key=lambda x: x['p_value'])
if promising:
    for r in promising:
        print(f'  {r["name"]:>16}: {r["n"]}局 胜率{r["win_rate"]:.1f}% p={r["p_value"]:.4f} 还需约{r["remaining"]}局即可证实')
else:
    print('  暂无')

print()
print('+' + '=' * 60 + '+')
print('| 已有足够数据的结论')
print('+' + '=' * 60 + '+')
confirmed = [r for r in results if r['p_value'] < 0.05]
if confirmed:
    for r in confirmed:
        mark = '优于随机' if r['win_rate'] > 50 else '差于随机'
        print(f'  {r["name"]:>16}: {r["n"]}局 胜率{r["win_rate"]:.1f}% - {mark}')
else:
    print('  暂无策略达到统计显著 (p<0.05)')

print()
print('+' + '=' * 60 + '+')
print('| 按当前速度，还需多久？')
print('+' + '=' * 60 + '+')
# Assuming ~100 rounds/day
for r in results:
    if r['remaining'] != float('inf') and r['remaining'] > 0 and r['remaining'] < 5000:
        days = ceil(r['remaining'] / 100)
        weeks = ceil(days / 7)
        print(f'  {r["name"]:>16}: 还需约{r["remaining"]}局 ≈ {days}天 / {weeks}周')
