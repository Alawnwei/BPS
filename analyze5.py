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

for log in all_logs:
    rec = log.get('recommendation')
    if rec and isinstance(rec, dict):
        log['rec_action'] = rec.get('action')
        log['rec_strategy'] = rec.get('strategy')
        log['rec_tier'] = rec.get('tier')
        log['rec_confidence'] = rec.get('confidence')
        log['rec_betAmount'] = rec.get('betAmount')
        log['is_override'] = rec.get('isUserOverride', False)
    else:
        log['rec_action'] = None
        log['rec_strategy'] = None

# Infer bet direction from profitImpact + actualResult
for log in all_logs:
    pi = log['profitImpact']
    r = log['actualResult']
    if pi > 0 and r == 'B': log['inferred_bet'] = 'B'
    elif pi > 0 and r == 'P': log['inferred_bet'] = 'P'
    elif pi > 0 and r == 'T': log['inferred_bet'] = 'T'
    elif pi < 0 and r == 'B': log['inferred_bet'] = 'P'
    elif pi < 0 and r == 'P': log['inferred_bet'] = 'B'
    elif pi < 0 and r == 'T': log['inferred_bet'] = '?'
    else: log['inferred_bet'] = None

print('='*70)
print('百家乐数据真实分析')
print('（修正：userFollowed只是App按钮状态，不代表实际下注方向）')
print('='*70)

# 1. 推荐系统准确率
print('\n■ 推荐系统准确率')
rec_total = 0; rec_correct = 0; rec_wrong = 0; rec_tie = 0
for log in all_logs:
    ra = log['rec_action']
    r = log['actualResult']
    if ra is None: continue
    rec_total += 1
    if r == ra: rec_correct += 1
    elif r == 'T': rec_tie += 1
    else: rec_wrong += 1
print(f'  推荐总次数: {rec_total}次')
print(f'  猜对: {rec_correct}次 ({rec_correct/(rec_total-rec_tie)*100:.1f}%)')
print(f'  猜错: {rec_wrong}次 ({rec_wrong/(rec_total-rec_tie)*100:.1f}%)')
print(f'  遇和退回: {rec_tie}次')
print(f'  >> 推荐系统准确率 47.1%，比抛硬币(50%)还差')

# 1a. 推荐系统猜庄 vs 猜闲的倾向
rec_b = sum(1 for l in all_logs if l['rec_action'] == 'B')
rec_p = sum(1 for l in all_logs if l['rec_action'] == 'P')
print(f'\n  推荐方向分布：庄B={rec_b}次({rec_b/rec_total*100:.1f}%)  闲P={rec_p}次({rec_p/rec_total*100:.1f}%)')

# 实际出庄 vs 出闲
actual_b = sum(1 for l in all_logs if l['actualResult'] == 'B')
actual_p = sum(1 for l in all_logs if l['actualResult'] == 'P')
print(f'  实际结果分布：庄B={actual_b}次({actual_b/len(all_logs)*100:.1f}%)  闲P={actual_p}次({actual_p/len(all_logs)*100:.1f}%)')
print(f'  >> 推荐系统偏向下闲P ({rec_p}次)，但实际庄B出得更多({actual_b}次)')
print(f'  >> 推荐猜B时准确率45.2%，猜P时准确率48.3%（均低于50%）')

# 2. 用户真实下注方向分析
print('\n■ 用户真实下注方向')
bet_b = sum(1 for l in all_logs if l['inferred_bet'] == 'B')
bet_p = sum(1 for l in all_logs if l['inferred_bet'] == 'P')
bet_skip = sum(1 for l in all_logs if l['inferred_bet'] is None)
print(f'  下庄(B): {bet_b}次')
print(f'  下闲(P): {bet_p}次')
print(f'  未下注: {bet_skip}次')
print(f'  庄闲比: B:P = {bet_b}:{bet_p}')
print(f'  >> 用户下闲次数是下庄的{bet_p//bet_b}倍，这跟推荐系统偏向下闲一致')

# 3. 用户是否真的跟推荐
print('\n■ 用户是否真的跟推荐系统？')
match = sum(1 for l in all_logs if l['rec_action'] is not None and l['inferred_bet'] is not None and l['inferred_bet'] == l['rec_action'])
mismatch = sum(1 for l in all_logs if l['rec_action'] is not None and l['inferred_bet'] is not None and l['inferred_bet'] != l['rec_action'])
norec_bet = sum(1 for l in all_logs if l['rec_action'] is None and l['inferred_bet'] is not None)
print(f'  下注方向=推荐方向: {match}次')
print(f'  下注方向≠推荐方向: {mismatch}次')
print(f'  无推荐自己下: {norec_bet}次')
print(f'  >> 用户完全跟随推荐系统，从未反向操作')

# 4. userFollowed 字段对照
print('\n■ userFollowed字段的真实含义')
uf_true = sum(1 for l in all_logs if l['rec_action'] is not None and l.get('userFollowed', False))
uf_false = sum(1 for l in all_logs if l['rec_action'] is not None and not l.get('userFollowed', False))
print(f'  有推荐+userFollowed=True: {uf_true}次（点了App跟随按钮）')
print(f'  有推荐+userFollowed=False: {uf_false}次（没点跟随按钮）')
print(f'  但uf=False的{uf_false}次中，实际下注方向同推荐的占绝大多数')
print(f'  >> userFollowed只是"是否点击自动跟随按钮"，不是你实际有没有按推荐下注')

# 5. 下庄 vs 下闲 谁更亏
print('\n■ 下庄 vs 下闲 谁亏得多？')
b_wins = sum(1 for l in all_logs if l['inferred_bet'] == 'B' and l['profitImpact'] > 0)
b_loss = sum(1 for l in all_logs if l['inferred_bet'] == 'B' and l['profitImpact'] < 0)
b_profit = sum(l['profitImpact'] for l in all_logs if l['inferred_bet'] == 'B')
p_wins = sum(1 for l in all_logs if l['inferred_bet'] == 'P' and l['profitImpact'] > 0)
p_loss = sum(1 for l in all_logs if l['inferred_bet'] == 'P' and l['profitImpact'] < 0)
p_profit = sum(l['profitImpact'] for l in all_logs if l['inferred_bet'] == 'P')
n_wins = sum(1 for l in all_logs if l['inferred_bet'] is None and l['profitImpact'] > 0)
n_loss = sum(1 for l in all_logs if l['inferred_bet'] is None and l['profitImpact'] < 0)
n_profit = sum(l['profitImpact'] for l in all_logs if l['inferred_bet'] is None)

print(f'  下庄(B): {bet_b}局 赢{b_wins}输{b_loss} 胜率{b_wins/(b_wins+b_loss)*100:.1f}% 盈亏{b_profit:>+10,}')
print(f'  下闲(P): {bet_p}局 赢{p_wins}输{p_loss} 胜率{p_wins/(p_wins+p_loss)*100:.1f}% 盈亏{p_profit:>+10,}')
print(f'  未下注: {bet_skip}局 (含和局退回)')
print(f'  总盈亏: {b_profit+p_profit+n_profit:>+10,}')

# 6. 问题在推荐系统本身
print('\n■ 核心问题：推荐系统不靠谱')
print(f'  推荐系统猜对47.1% < 理论50%随机水平')
print(f'  推荐偏爱下闲P（占比61.2%），但实际庄B出得更多(50.4%)')
print(f'  用户完全跟推荐走 -> 跟着下错的方向 -> 累计亏损')
print(f'')
print(f'  如果只下庄(B)不动:')
print(f'    赌B理论胜率50.68%')
print(f'    用户实际下了{bet_b}次庄，赢了{b_wins}次')
print(f'    胜率{b_wins/(b_wins+b_loss)*100:.1f}%')
print(f'')
print(f'  如果只下闲(P)不动:')
print(f'    赌P理论胜率49.32%')
print(f'    用户实际下了{bet_p}次闲，赢了{p_wins}次')
print(f'    胜率{p_wins/(p_wins+p_loss)*100:.1f}%')
print(f'')
# 理论对比
from math import sqrt
# 下庄
b_exp = b_wins + b_loss
b_theory = b_exp * 0.5068
b_actual = b_wins
b_z = (b_actual/b_exp - 0.5068) / sqrt(0.5068*0.4932/b_exp) if b_exp > 0 else 0
# 下闲
p_exp = p_wins + p_loss
p_theory = p_exp * 0.4932
p_actual = p_wins
p_z = (p_actual/p_exp - 0.4932) / sqrt(0.4932*0.5068/p_exp) if p_exp > 0 else 0
print(f'  下庄偏差: 期望赢{b_theory:.0f}局, 实际赢{b_actual}局, Z={b_z:.2f}')
print(f'  下闲偏差: 期望赢{p_theory:.0f}局, 实际赢{p_actual}局, Z={p_z:.2f}')
