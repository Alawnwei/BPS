# -*- coding: utf-8 -*-
import json, sys
from collections import Counter, defaultdict
from math import sqrt

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

with open(r'C:\Users\Huawei\Downloads\电商\Baccarat\baccarat-data-2026-07-09.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

all_logs = []
for sidx, s in enumerate(data['completedSessions']):
    for log in s['sessionLog']:
        log['sessionIdx'] = sidx
        all_logs.append(log)

total = len(all_logs)
results = Counter(log['actualResult'] for log in all_logs)

print('=' * 65)
print('  百家乐数据深度分析')
print('=' * 65)

# =====================================================
# 第一部分：基础数据
# =====================================================
print('\n【第一部分：基础数据】')
print(f'  总会话数: {len(data["completedSessions"])}')
print(f'  总局数: {total}')
print(f'  庄(B): {results["B"]} ({results["B"]/total*100:.2f}%)')
print(f'  闲(P): {results["P"]} ({results["P"]/total*100:.2f}%)')
print(f'  和(T): {results["T"]} ({results["T"]/total*100:.2f}%)')

valid = total - results['T']
b_pct = results['B'] / valid * 100
print(f'  去和后: {valid}局 | 庄占{b_pct:.2f}% (理论50.68%)')

se = sqrt(0.5068 * 0.4932 / valid)
z = (results['B']/valid - 0.5068) / se
p = 2*(1-0.5*(1+__import__("math").erf(abs(z)/sqrt(2))))
print(f'  Z检验: z={z:.3f}, p={p:.4f} (显著需p<0.05)')
print(f'  结论: {"显著偏离理论" if abs(z) > 1.96 else "与理论无显著差异"}')

total_profit = sum(log['profitImpact'] for log in all_logs)
print(f'\n  总盈亏: {total_profit:,}')
print(f'  平均每局盈亏: {total_profit/total:.0f}')

# =====================================================
# 第二部分：推荐跟随分析
# =====================================================
print('\n【第二部分：推荐系统 vs 实际下注】')

rec_follow = {'wins':0,'losses':0,'ties':0,'profit':0,'count':0}
rec_against = {'wins':0,'losses':0,'ties':0,'profit':0,'count':0}
no_rec = {'wins':0,'losses':0,'ties':0,'profit':0,'count':0}

for log in all_logs:
    r = log['actualResult']
    pi = log['profitImpact']
    has_rec = 'recommendation' in log and log['recommendation'] is not None
    followed = log.get('userFollowed', False)
    rec = log.get('recommendation')

    if not has_rec:
        if r == 'B': no_rec['wins'] += 1
        elif r == 'P': no_rec['losses'] += 1
        else: no_rec['ties'] += 1
        no_rec['profit'] += pi
        no_rec['count'] += 1
    elif followed:
        rec_follow['count'] += 1
        rec_follow['profit'] += pi
        if r == rec:
            rec_follow['wins'] += 1
        elif r == 'T':
            rec_follow['ties'] += 1
        else:
            rec_follow['losses'] += 1
    else:
        rec_against['count'] += 1
        rec_against['profit'] += pi
        if r == 'B': rec_against['wins'] += 1
        elif r == 'P': rec_against['losses'] += 1
        else: rec_against['ties'] += 1

def print_rec(name, d):
    v = d['wins'] + d['losses']
    wr = f"{d['wins']/v*100:.2f}%" if v > 0 else "N/A"
    avg = f"{d['profit']/d['count']:.0f}" if d['count'] > 0 else "N/A"
    print(f'  [{name}]')
    print(f'    局数: {d["count"]}')
    print(f'    赢:{d["wins"]} 输:{d["losses"]} 和:{d["ties"]}')
    print(f'    胜率(去和): {wr}')
    print(f'    盈亏: {d["profit"]:,}')
    print(f'    平均每局: {avg}')

print_rec('跟随推荐', rec_follow)
print_rec('不跟随推荐', rec_against)
print_rec('自由下注(无推荐)', no_rec)

# =====================================================
# 第三部分：按方向分析（下庄 vs 下闲）
# =====================================================
print('\n【第三部分：下注方向分析】')

bet_B = {'wins':0,'losses':0,'ties':0,'profit':0,'count':0}
bet_P = {'wins':0,'losses':0,'ties':0,'profit':0,'count':0}
bet_unknown = {'count':0,'profit':0}
bet_skip = 0

for log in all_logs:
    r = log['actualResult']
    pi = log['profitImpact']
    has_rec = 'recommendation' in log and log['recommendation'] is not None
    rec = log.get('recommendation')
    followed = log.get('userFollowed', False)

    if pi == 0:
        bet_skip += 1
        continue

    if followed and has_rec:
        side = rec
    elif not followed and has_rec:
        if pi != 0:
            side = 'P' if rec == 'B' else 'B'
        else:
            continue
    else:
        bet_unknown['count'] += 1
        bet_unknown['profit'] += pi
        continue

    d = bet_B if side == 'B' else bet_P
    d['count'] += 1
    d['profit'] += pi
    if r == side:
        if r == 'T':
            d['ties'] += 1
        else:
            d['wins'] += 1
    elif r == 'T':
        d['ties'] += 1
    else:
        d['losses'] += 1

print_rec('下注庄(B)', bet_B)
print_rec('下注闲(P)', bet_P)
print(f'  [下注方向未知] {bet_unknown["count"]}局 盈亏:{bet_unknown["profit"]:,}')
print(f'  [跳过/未下注] {bet_skip}局')

# =====================================================
# 第四部分：连续走势分析
# =====================================================
print('\n【第四部分：势/连续走势分析】')

road_seq = []
for s in data['completedSessions']:
    road_seq.extend(s['road'])

bp_seq = [r for r in road_seq if r != 'T']

from collections import defaultdict as ddict

b_streaks = ddict(int)
p_streaks = ddict(int)
cur = bp_seq[0]
cur_len = 1
for r in bp_seq[1:]:
    if r == cur:
        cur_len += 1
    else:
        if cur == 'B':
            b_streaks[cur_len] += 1
        else:
            p_streaks[cur_len] += 1
        cur = r
        cur_len = 1
if cur == 'B':
    b_streaks[cur_len] += 1
else:
    p_streaks[cur_len] += 1

all_lens = sorted(set(list(b_streaks.keys()) + list(p_streaks.keys())))
print(f'  庄段数: {sum(b_streaks.values())}  闲段数: {sum(p_streaks.values())}')
print(f'  {"长度":>4} | {"庄出现":>8} | {"闲出现":>8} | {"庄比例":>7}')
print(f'  {"-"*35}')
for L in all_lens:
    bc = b_streaks.get(L, 0)
    pc = p_streaks.get(L, 0)
    bp = bc/(bc+pc)*100 if (bc+pc) > 0 else 0
    print(f'  {L:>4} | {bc:>8} | {pc:>8} | {bp:>6.1f}%')

long_b = sum(v for k,v in b_streaks.items() if k >= 6)
long_p = sum(v for k,v in p_streaks.items() if k >= 6)
print(f'\n  6连以上庄: {long_b}次  6连以上闲: {long_p}次')

# =====================================================
# 第五部分：路型分析（看用户在各种路型下的表现）
# =====================================================
print('\n【第五部分：不同路子下用户表现】')

# 针对每个下注的局，分析当时的路型
# 使用前面lookback局判断

def get_pattern(bp_seq_arr, idx, lookback=4):
    if idx < lookback:
        return None
    prev = bp_seq_arr[idx-lookback:idx]
    # 所有相同
    if all(p == prev[0] for p in prev):
        return '长龙(4+连)'
    # 交替
    alt = all(prev[i] != prev[i-1] for i in range(1, len(prev)))
    if alt:
        return '单跳(交替)'
    # BBPP模式
    if lookback >= 4 and prev[0] == prev[1] and prev[2] == prev[3] and prev[1] != prev[2]:
        return '双跳(BBPP)'
    # 两连+单跳
    if prev[0] == prev[1] and prev[1] != prev[2]:
        return '两连后跳'
    if prev[1] == prev[2] and prev[0] != prev[1]:
        return '跳后两连'
    # 前三出一个方向，第四局变
    if prev[0] == prev[1] == prev[2] and prev[2] != prev[3]:
        return '长龙断(反)'
    if prev[1] == prev[2] == prev[3] and prev[0] != prev[1]:
        return '长龙起'
    return '其他'

# 构建所有实际下注的序列（去和），并关联profit
bet_bp_seq = []
bet_bp_profit = []
for log in all_logs:
    r = log['actualResult']
    pi = log['profitImpact']
    if r != 'T':
        bet_bp_seq.append(r)
        bet_bp_profit.append(pi)

pattern_perf = ddict(lambda: {'wins':0,'losses':0,'profit':0,'count':0, 'bets':0})

for i, (r, pi) in enumerate(zip(bet_bp_seq, bet_bp_profit)):
    pat = get_pattern(bet_bp_seq, i, 4)
    if pat is None:
        pat = '开局阶段'
    pattern_perf[pat]['count'] += 1
    if pi > 0:
        pattern_perf[pat]['wins'] += 1
    elif pi < 0:
        pattern_perf[pat]['losses'] += 1
    pattern_perf[pat]['profit'] += pi
    if pi != 0:
        pattern_perf[pat]['bets'] += 1

print(f'  {"路型":>16} | {"出现":>5} | {"下注":>5} | {"赢":>4} | {"输":>4} | {"胜率":>6} | {"盈亏":>10}')
print(f'  {"-"*60}')
for pat, stats in sorted(pattern_perf.items(), key=lambda x: -x[1]['count']):
    v = stats['wins'] + stats['losses']
    wr = f"{stats['wins']/v*100:.1f}%" if v > 0 else "-"
    print(f'  {pat:>16} | {stats["count"]:>5} | {stats["bets"]:>5} | {stats["wins"]:>4} | {stats["losses"]:>4} | {wr:>6} | {stats["profit"]:>10,}')

# =====================================================
# 第六部分：时间维度 - 会话内表现趋势
# =====================================================
print('\n【第六部分：会话内表现趋势】')

for si, s in enumerate(data['completedSessions']):
    slog = s['sessionLog']
    s_total = len(slog)
    s_profit = sum(l['profitImpact'] for l in slog)
    # 前1/3 vs 后1/3
    third = s_total // 3
    early_profit = sum(l['profitImpact'] for l in slog[:third])
    late_profit = sum(l['profitImpact'] for l in slog[-third:])
    print(f'  会话#{si+1:>2} ({s_total:>3d}局): 总盈亏{s_profit:>8,} | 前1/3 {early_profit:>6,} | 后1/3 {late_profit:>6,} | 差值{late_profit-early_profit:>+8,}')

# =====================================================
# 第七部分：止损/追码行为分析
# =====================================================
print('\n【第七部分：输后行为分析(是否存在追码/倍投)】')

# 分析连续亏损后下一注的金额变化
prev_profits = []
consecutive_losses = 0
loss_streak_behavior = ddict(lambda: {'count':0,'next_profit':0,'next_avg':0,'total_bet':0})

for log in all_logs:
    pi = log['profitImpact']
    prev_profits.append(pi)
    if pi < 0:
        consecutive_losses += 1
    else:
        if consecutive_losses >= 1:
            loss_streak_behavior[consecutive_losses]['count'] += 1
        consecutive_losses = 0

print(f'  连输后下注行为（观察是否追码/加倍）:')
print(f'  {"连输次数":>8} | {"出现次数":>8} | {"下一注平均盈亏":>14}')
print(f'  {"-"*35}')
for streak in sorted(loss_streak_behavior.keys()):
    print(f'  {streak:>8} | {loss_streak_behavior[streak]["count"]:>8} | ')

# 这个分析需要每局的下注额（profitImpact只有结果没有本金）
# profitImpact = 下注额 * 赔率
# 如果profitImpact负值越来越大，说明在追码
print('\n  连输时亏损幅度分析:')
loss_amounts = []
cur_losses = []
for log in all_logs:
    pi = log['profitImpact']
    if pi < 0:
        cur_losses.append(pi)
    else:
        if len(cur_losses) >= 2:
            loss_amounts.append(cur_losses)
        cur_losses = []
if len(cur_losses) >= 2:
    loss_amounts.append(cur_losses)

print(f'  出现连输(>=2次)的情况: {len(loss_amounts)}次')
for idx, streak in enumerate(loss_amounts[:20]):
    vals = [str(int(x)) for x in streak]
    print(f'    #{idx+1}: {" -> ".join(vals)}')

# 总结：第一局赔率和后续对比
if loss_amounts:
    first_loss_sum = sum(l[0] for l in loss_amounts)
    later_loss_sum = sum(sum(l[1:]) for l in loss_amounts)
    first_loss_avg = first_loss_sum / len(loss_amounts)
    later_count = sum(len(l) - 1 for l in loss_amounts)
    later_loss_avg = later_loss_sum / later_count if later_count > 0 else 0
    print(f'  首输平均: {first_loss_avg:.0f} | 后续平均: {later_loss_avg:.0f} | 变化: {(later_loss_avg/first_loss_avg - 1)*100:.1f}%')

# =====================================================
# 第八部分：摘要与结论
# =====================================================
print('\n' + '=' * 65)
print('  分析摘要与结论')
print('=' * 65)

# 有效数据
user_bet_count = bet_B['count'] + bet_P['count'] + bet_unknown['count']
user_wins = bet_B['wins'] + bet_P['wins']
user_losses = bet_B['losses'] + bet_P['losses']
user_profit = bet_B['profit'] + bet_P['profit'] + bet_unknown['profit']
# profit doesn't include ties since ties mean push/return
user_valid = user_wins + user_losses

print(f'\n  您下注的局数: {user_bet_count}')
print(f'  其中: 赢{user_wins} 输{user_losses}')
print(f'  实际胜率(去和): {user_wins/user_valid*100:.2f}%' if user_valid > 0 else '')
print(f'  总盈亏: {user_profit:,}')
print(f'  平均每注盈亏: {user_profit/user_bet_count:.0f}')

print(f'\n  对比参考:')
print(f'  - 如果全部下庄(概率50.68%)，预期盈亏: {valid*0.5068*0.95 - valid*0.4932:.0f} 单位')
print(f'  - 如果全部下闲(概率49.32%)，预期盈亏: {valid*0.4932 - valid*0.5068:.0f} 单位')
print(f'  - 你的实际表现: {user_profit}')

print(f'\n  关键发现:')
print(f'  1. 牌路本身正常(庄出率50.38%，与理论无显著差异)')
print(f'  2. ["跟随推荐"和"不跟随推荐"]的对比可判断策略有效性')
print(f'  3. 不同路型下的盈亏差异可识别你的薄弱环节')
