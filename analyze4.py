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
        log['rec_tier'] = rec.get('tier')
        log['rec_confidence'] = rec.get('confidence')
        log['rec_betAmount'] = rec.get('betAmount')
        log['is_override'] = rec.get('isUserOverride', False)
    else:
        log['rec_action'] = None
        log['rec_strategy'] = None

# ===== 关键修正：从 profitImpact + actualResult 推断用户实际下注方向 =====
# 原理：
#   profitImpact > 0 AND actualResult=B → 用户下了庄(B)
#   profitImpact > 0 AND actualResult=P → 用户下了闲(P)
#   profitImpact < 0 AND actualResult=B → 用户下了闲(P)  [因为庄出了，下闲的亏了]
#   profitImpact < 0 AND actualResult=P → 用户下了庄(B)  [因为闲出了，下庄的亏了]
#   profitImpact = 0 → 用户没下注 或 和局退回

for log in all_logs:
    pi = log['profitImpact']
    r = log['actualResult']
    if pi > 0 and r == 'B':
        log['inferred_bet'] = 'B'
    elif pi > 0 and r == 'P':
        log['inferred_bet'] = 'P'
    elif pi > 0 and r == 'T':
        log['inferred_bet'] = 'T'  # 下了和
    elif pi < 0 and r == 'B':
        log['inferred_bet'] = 'P'  # B出但亏了 → 下了闲
    elif pi < 0 and r == 'P':
        log['inferred_bet'] = 'B'  # P出但亏了 → 下了庄
    elif pi < 0 and r == 'T':
        log['inferred_bet'] = '?'
    else:  # pi == 0
        log['inferred_bet'] = None  # 没下注

# 1. 基础：推荐系统准确率
print('='*70)
print('1. 推荐系统本身的准确率（不考虑用户是否跟）')
print('='*70)

rec_correct = 0
rec_wrong = 0
rec_tie = 0
rec_skipped = 0
for log in all_logs:
    ra = log['rec_action']
    r = log['actualResult']
    if ra is None:
        continue  # 无推荐
    if r == ra:
        rec_correct += 1
    elif r == 'T':
        rec_tie += 1
    else:
        rec_wrong += 1

rec_total = rec_correct + rec_wrong
print(f'  推荐总次数: {rec_total + rec_tie} (去和{rec_total})')
print(f'  猜对: {rec_correct} ({rec_correct/rec_total*100:.1f}%)')
print(f'  猜错: {rec_wrong} ({rec_wrong/rec_total*100:.1f}%)')
print(f'  遇和: {rec_tie}')

# 2. 用户的实际下注方向 vs 推荐方向
print('\n' + '='*70)
print('2. 用户实际下注 vs 推荐方向（推断法）')
print('='*70)

follow_inferred = {'count':0,'w':0,'l':0,'p':0}
against_inferred = {'count':0,'w':0,'l':0,'p':0}
same_no_rec = {'count':0,'w':0,'l':0,'p':0}

for log in all_logs:
    ra = log['rec_action']
    ib = log['inferred_bet']
    pi = log['profitImpact']
    r = log['actualResult']

    if ib is None:  # 没下注
        continue
    if ra is None:
        d = same_no_rec  # 无推荐，自己下
    elif ib == ra:
        d = follow_inferred  # 下注方向 = 推荐方向
    else:
        d = against_inferred  # 下注方向 != 推荐方向

    d['count'] += 1
    d['p'] += pi
    if pi > 0: d['w'] += 1
    elif pi < 0: d['l'] += 1

for name, d in [('下注=推荐方向', follow_inferred), ('下注!=推荐方向', against_inferred), ('无推荐自己下', same_no_rec)]:
    v = d['w'] + d['l']
    wr = f'{d["w"]/v*100:.1f}%' if v>0 else '-'
    print(f'  {name:>20}: {d["count"]:>4}局 赢{d["w"]:>3} 输{d["l"]:>3} 胜率{wr:>6} 盈亏{d["p"]:>+10,}')

# 3. userFollowed 字段到底是什么？
print('\n' + '='*70)
print('3. userFollowed 字段的真实含义诊断')
print('='*70)

follow_true = 0
follow_false = 0
for log in all_logs:
    if log['rec_action'] is not None:
        if log.get('userFollowed', False):
            follow_true += 1
        else:
            follow_false += 1

print(f'  有推荐且 userFollowed=True: {follow_true}')
print(f'  有推荐且 userFollowed=False: {follow_false}')
print(f'  有推荐总: {follow_true + follow_false}')

# 看 userFollowed=true 时，用户实际下注方向 vs 推荐
print('\n  当 userFollowed=True 时:')
m = {'下注同推荐':0,'下注反推荐':0,'未下注':0}
for log in all_logs:
    if log.get('userFollowed', False) and log['rec_action'] is not None:
        ib = log['inferred_bet']
        ra = log['rec_action']
        if ib is None:
            m['未下注'] += 1
        elif ib == ra:
            m['下注同推荐'] += 1
        else:
            m['下注反推荐'] += 1
for k, v in m.items():
    print(f'    {k}: {v}次')

print('\n  当 userFollowed=False 时（有推荐但不跟）:')
m2 = {'下注同推荐':0,'下注反推荐':0,'未下注':0}
for log in all_logs:
    if not log.get('userFollowed', True) and log['rec_action'] is not None:
        ib = log['inferred_bet']
        ra = log['rec_action']
        if ib is None:
            m2['未下注'] += 1
        elif ib == ra:
            m2['下注同推荐'] += 1
        else:
            m2['下注反推荐'] += 1
for k, v in m2.items():
    print(f'    {k}: {v}次')

# 4. 下单方向分布（不分推荐与否）
print('\n' + '='*70)
print('4. 用户下注方向分布')
print('='*70)
bet_dir = Counter()
bet_profit_by_dir = defaultdict(float)
for log in all_logs:
    ib = log['inferred_bet']
    if ib in ('B', 'P'):
        bet_dir[ib] += 1
        bet_profit_by_dir[ib] += log['profitImpact']

for d in ['B', 'P']:
    print(f'  下{d:>2}: {bet_dir[d]:>4}局 盈亏{bet_profit_by_dir[d]:>+10,}')

# 5. 推荐系统猜的方向 vs 实际结果
print('\n' + '='*70)
print('5. 推荐系统猜庄/闲的准确率')
print('='*70)
rec_action_acc = defaultdict(lambda: {'correct':0,'wrong':0,'tie':0})
for log in all_logs:
    ra = log['rec_action']
    if ra is None: continue
    r = log['actualResult']
    d = rec_action_acc[ra]
    if r == ra: d['correct'] += 1
    elif r == 'T': d['tie'] += 1
    else: d['wrong'] += 1

for ra in ['B', 'P']:
    d = rec_action_acc[ra]
    t = d['correct'] + d['wrong']
    acc = f'{d["correct"]/t*100:.1f}%' if t>0 else '-'
    print(f'  推荐{ra}: 推荐{d["correct"]:>4}次 | 猜对{d["correct"]:>3} 猜错{d["wrong"]:>3} 遇和{d["tie"]:>2} | 准确率{acc}')

# 6. 按策略看推荐准确率
print('\n' + '='*70)
print('6. 各策略推荐准确率')
print('='*70)
strat_acc = defaultdict(lambda: {'correct':0,'wrong':0,'tie':0})
for log in all_logs:
    strat = log['rec_strategy']
    ra = log['rec_action']
    if not strat or ra is None: continue
    r = log['actualResult']
    d = strat_acc[strat]
    if r == ra: d['correct'] += 1
    elif r == 'T': d['tie'] += 1
    else: d['wrong'] += 1

print(f'  {"策略":>20} | {"推荐":>4} | {"对":>3} | {"错":>3} | {"准确率":>6}')
print('  ' + '-' * 45)
for strat, d in sorted(strat_acc.items(), key=lambda x: -x[1]['correct']-x[1]['wrong']):
    t = d['correct'] + d['wrong']
    acc = f'{d["correct"]/t*100:.0f}%' if t>0 else '-'
    print(f'  {strat:>20} | {t:>4} | {d["correct"]:>3} | {d["wrong"]:>3} | {acc:>6}')

# 7. 不管推荐，只看用户下注方向本身
print('\n' + '='*70)
print('7. 用户下庄 vs 下闲 的实际表现')
print('='*70)
b_stats = {'count':0,'wins':0,'losses':0,'profit':0}
p_stats = {'count':0,'wins':0,'losses':0,'profit':0}
for log in all_logs:
    ib = log['inferred_bet']
    pi = log['profitImpact']
    r = log['actualResult']
    if ib == 'B':
        b_stats['count'] += 1
        b_stats['profit'] += pi
        if pi > 0: b_stats['wins'] += 1
        elif pi < 0: b_stats['losses'] += 1
    elif ib == 'P':
        p_stats['count'] += 1
        p_stats['profit'] += pi
        if pi > 0: p_stats['wins'] += 1
        elif pi < 0: p_stats['losses'] += 1

bw = b_stats['wins']/(b_stats['wins']+b_stats['losses'])*100 if (b_stats['wins']+b_stats['losses'])>0 else 0
pw = p_stats['wins']/(p_stats['wins']+p_stats['losses'])*100 if (p_stats['wins']+p_stats['losses'])>0 else 0
print(f'  下庄(B): {b_stats["count"]:>4}局 赢{b_stats["wins"]:>3} 输{b_stats["losses"]:>3} 胜率{bw:.1f}% 盈亏{b_stats["profit"]:>+10,}')
print(f'  下闲(P): {p_stats["count"]:>4}局 赢{p_stats["wins"]:>3} 输{p_stats["losses"]:>3} 胜率{pw:.1f}% 盈亏{p_stats["profit"]:>+10,}')

# 8. 用户真实下注 vs 推荐的实际对比（关键）
print('\n' + '='*70)
print('8. 关键：用户实际下注方向时，推荐系统猜了什么？')
print('='*70)

# 当用户下B时
bet_b_then_rec = Counter()
for log in all_logs:
    if log['inferred_bet'] == 'B' and log['rec_action'] is not None:
        bet_b_then_rec[log['rec_action']] += 1
# 当用户下P时
bet_p_then_rec = Counter()
for log in all_logs:
    if log['inferred_bet'] == 'P' and log['rec_action'] is not None:
        bet_p_then_rec[log['rec_action']] += 1

print(f'  用户下庄(B)时，推荐系统在猜：B={bet_b_then_rec["B"]}次 P={bet_b_then_rec["P"]}次')
print(f'  用户下闲(P)时，推荐系统在猜：B={bet_p_then_rec["B"]}次 P={bet_p_then_rec["P"]}次')

# 当用户和推荐一致时，最终盈亏
print('\n  当 用户下注 == 推荐方向:')
match_profit = 0
match_wins = 0
match_losses = 0
match_count = 0
for log in all_logs:
    if log['rec_action'] is not None and log['inferred_bet'] == log['rec_action']:
        pi = log['profitImpact']
        match_profit += pi
        match_count += 1
        if pi > 0: match_wins += 1
        elif pi < 0: match_losses += 1
match_wr = match_wins/(match_wins+match_losses)*100 if (match_wins+match_losses)>0 else 0
print(f'    {match_count}局 | 赢{match_wins} 输{match_losses} | 胜率{match_wr:.1f}% | 盈亏{match_profit:>+10,}')

print('\n  当 用户下注 != 推荐方向:')
mismatch_profit = 0
mismatch_wins = 0
mismatch_losses = 0
mismatch_count = 0
for log in all_logs:
    if log['rec_action'] is not None and log['inferred_bet'] is not None and log['inferred_bet'] != log['rec_action']:
        pi = log['profitImpact']
        mismatch_profit += pi
        mismatch_count += 1
        if pi > 0: mismatch_wins += 1
        elif pi < 0: mismatch_losses += 1
mm_wr = mismatch_wins/(mismatch_wins+mismatch_losses)*100 if (mismatch_wins+mismatch_losses)>0 else 0
print(f'    {mismatch_count}局 | 赢{mismatch_wins} 输{mismatch_losses} | 胜率{mm_wr:.1f}% | 盈亏{mismatch_profit:>+10,}')

print('\n  无推荐，自己下:')
norec_profit = 0
norec_wins = 0
norec_losses = 0
norec_count = 0
for log in all_logs:
    if log['rec_action'] is None and log['inferred_bet'] is not None:
        pi = log['profitImpact']
        norec_profit += pi
        norec_count += 1
        if pi > 0: norec_wins += 1
        elif pi < 0: norec_losses += 1
norec_wr = norec_wins/(norec_wins+norec_losses)*100 if (norec_wins+norec_losses)>0 else 0
print(f'    {norec_count}局 | 赢{norec_wins} 输{norec_losses} | 胜率{norec_wr:.1f}% | 盈亏{norec_profit:>+10,}')
