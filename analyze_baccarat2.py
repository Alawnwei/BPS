# -*- coding: utf-8 -*-
import json, sys
from collections import Counter, defaultdict

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

with open(r'C:\Users\Huawei\Downloads\电商\Baccarat\baccarat-data-2026-07-09.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

all_logs = []
for sidx, s in enumerate(data['completedSessions']):
    for log in s['sessionLog']:
        log['sessionIdx'] = sidx
        all_logs.append(log)

# 先诊断数据字段
print("=== 字段诊断 ===")
rec_vals = Counter()
rec_not_null = 0
rec_null = 0
for log in all_logs:
    if 'recommendation' in log:
        rec_vals[str(log['recommendation'])] += 1
        if log['recommendation'] is not None:
            rec_not_null += 1
        else:
            rec_null += 1
    else:
        rec_vals['KEY_NOT_FOUND'] += 1

for k, v in rec_vals.most_common():
    print(f'  recommendation={k}: {v}次')
print(f'  有推荐: {rec_not_null}, 无推荐: {rec_null}')

# 看推荐的分布和实际结果的关系
print('\n=== 推荐 vs 实际结果 ===')
rec_result = defaultdict(Counter)
for log in all_logs:
    rec = log.get('recommendation')
    r = log['actualResult']
    rec_result[str(rec)][r] += 1

for rec_val, result_counter in sorted(rec_result.items()):
    print(f'  推荐={rec_val}: ', dict(result_counter))

# 看userFollowed的分布
print('\n=== userFollowed 分布 ===')
followed_vals = Counter()
for log in all_logs:
    followed_vals[log.get('userFollowed', 'KEY_NOT_FOUND')] += 1
for k, v in followed_vals.most_common():
    print(f'  userFollowed={k}: {v}次')

# 看profitImpact的范围
print('\n=== profitImpact 统计 ===')
pi_vals = [log['profitImpact'] for log in all_logs]
pi_pos = sum(1 for p in pi_vals if p > 0)
pi_neg = sum(1 for p in pi_vals if p < 0)
pi_zero = sum(1 for p in pi_vals if p == 0)
print(f'  正盈亏: {pi_pos}次, 负盈亏: {pi_neg}次, 零: {pi_zero}次')
print(f'  最小值: {min(pi_vals):,}, 最大值: {max(pi_vals):,}')
print(f'  正数平均值: {sum(p for p in pi_vals if p>0)/pi_pos:.0f}' if pi_pos > 0 else '')
print(f'  负数平均值: {sum(p for p in pi_vals if p<0)/pi_neg:.0f}' if pi_neg > 0 else '')

# 看看是否推荐系统在猜庄还是闲
print('\n=== 推荐方向统计 ===')
rec_b = sum(1 for log in all_logs if log.get('recommendation') == 'B')
rec_p = sum(1 for log in all_logs if log.get('recommendation') == 'P')
print(f'  推荐庄(B): {rec_b}次')
print(f'  推荐闲(P): {rec_p}次')

# 准确率分析
print('\n=== 推荐准确率 ===')
rec_correct = 0
rec_wrong = 0
rec_tie = 0
for log in all_logs:
    rec = log.get('recommendation')
    if rec is not None:
        r = log['actualResult']
        if r == rec:
            rec_correct += 1
        elif r == 'T':
            rec_tie += 1
        else:
            rec_wrong += 1
rec_total = rec_correct + rec_wrong
print(f'  推荐总次数: {rec_total}')
print(f'  猜对: {rec_correct} ({rec_correct/rec_total*100:.1f}%)' if rec_total > 0 else '')
print(f'  猜错: {rec_wrong} ({rec_wrong/rec_total*100:.1f}%)' if rec_total > 0 else '')
print(f'  遇到和: {rec_tie}')

# 如果用户跟随推荐，实际盈亏
print('\n=== 跟随推荐 vs 不跟随的盈亏分析 ===')
for log in all_logs:
    rec = log.get('recommendation')
    pi = log['profitImpact']
    followed = log.get('userFollowed', False)
    log['bet_side'] = None

    if followed and rec is not None:
        log['bet_side'] = rec  # 用户跟推荐下注
    elif not followed and rec is not None:
        # 不跟 - 可能下了对面或没下
        if pi != 0:
            # 下了，推测是反向
            log['bet_side'] = 'P' if rec == 'B' else 'B'

follow_profit = sum(log['profitImpact'] for log in all_logs if log.get('userFollowed', False) and log.get('recommendation') is not None)
nofollow_profit = sum(log['profitImpact'] for log in all_logs if not log.get('userFollowed', False) and log.get('recommendation') is not None and log['profitImpact'] != 0)
norec_profit = sum(log['profitImpact'] for log in all_logs if log.get('recommendation') is None and log['profitImpact'] != 0)

nofollow_count = sum(1 for log in all_logs if not log.get('userFollowed', False) and log.get('recommendation') is not None and log['profitImpact'] != 0)
follow_count = sum(1 for log in all_logs if log.get('userFollowed', False) and log.get('recommendation') is not None)
norec_count = sum(1 for log in all_logs if log.get('recommendation') is None and log['profitImpact'] != 0)

print(f'  跟随推荐: {follow_count}局, 总盈亏 {follow_profit:>+10,}')
print(f'  逆反推荐: {nofollow_count}局, 总盈亏 {nofollow_profit:>+10,}')
print(f'  自由下注: {norec_count}局, 总盈亏 {norec_profit:>+10,}')

# 再看看按下注方向的实际盈亏
print('\n=== 按下注方向的实际盈亏 ===')
bet_b_profit = 0
bet_b_count = 0
bet_p_profit = 0
bet_p_count = 0
bet_b_wins = 0
bet_b_losses = 0
bet_p_wins = 0
bet_p_losses = 0

for log in all_logs:
    pi = log['profitImpact']
    r = log['actualResult']
    if pi == 0:
        continue

    # 从profitImpact和actualResult推断下注方向
    # 如果userFollowed且推荐=B → 下庄
    # 如果结果B且盈利 → 下庄; 结果P且盈利 → 下闲
    # 如果结果B且亏损 → 下闲; 结果P且亏损 → 下庄
    rec = log.get('recommendation')
    followed = log.get('userFollowed', False)

    if followed and rec is not None:
        # 明确知道下注方向
        if rec == 'B':
            bet_b_count += 1
            bet_b_profit += pi
            if pi > 0: bet_b_wins += 1
            elif pi < 0: bet_b_losses += 1
        else:
            bet_p_count += 1
            bet_p_profit += pi
            if pi > 0: bet_p_wins += 1
            elif pi < 0: bet_p_losses += 1
    elif not followed and rec is not None:
        # 反向推测
        bet_side = 'P' if rec == 'B' else 'B'
        if bet_side == 'B':
            bet_b_count += 1
            bet_b_profit += pi
            if pi > 0: bet_b_wins += 1
            elif pi < 0: bet_b_losses += 1
        else:
            bet_p_count += 1
            bet_p_profit += pi
            if pi > 0: bet_p_wins += 1
            elif pi < 0: bet_p_losses += 1
    else:
        # 无推荐 - 从结果和盈亏推断
        if (r == 'B' and pi > 0) or (r == 'P' and pi < 0):
            # 下了庄
            bet_b_count += 1
            bet_b_profit += pi
            if pi > 0: bet_b_wins += 1
            elif pi < 0: bet_b_losses += 1
        elif (r == 'P' and pi > 0) or (r == 'B' and pi < 0):
            # 下了闲
            bet_p_count += 1
            bet_p_profit += pi
            if pi > 0: bet_p_wins += 1
            elif pi < 0: bet_p_losses += 1
        else:
            # T
            pass

bv = bet_b_wins + bet_b_losses
pv = bet_p_wins + bet_p_losses
print(f'  下庄(B): {bet_b_count}局 | 赢{bet_b_wins}输{bet_b_losses} | 胜率{bet_b_wins/bv*100:.1f}% | 盈亏{bet_b_profit:>+10,}' if bv > 0 else '')
print(f'  下闲(P): {bet_p_count}局 | 赢{bet_p_wins}输{bet_p_losses} | 胜率{bet_p_wins/pv*100:.1f}% | 盈亏{bet_p_profit:>+10,}' if pv > 0 else '')
print(f'  合计: {bet_b_count+bet_p_count}局 | 总盈亏{bet_b_profit+bet_p_profit:>+10,}')

# 会话19-24的详细分析（大额阶段）
print('\n=== 大额阶段详细分析 (会话 18-24) ===')
for si, s in enumerate(data['completedSessions']):
    if si < 17:
        continue
    slog = s['sessionLog']
    s_id = s['id'] % 10000
    road = s['road']

    # 每局下注额的分布
    bet_amounts = [abs(l['profitImpact']) for l in slog if l['profitImpact'] != 0]
    if bet_amounts:
        avg_bet = sum(bet_amounts) / len(bet_amounts)
        max_bet = max(bet_amounts)
        total = sum(l['profitImpact'] for l in slog)
        b_count = road.count('B')
        p_count = road.count('P')
        t_count = road.count('T')
        print(f'\n  会话#{si+1} (ID:{s_id}, {len(road)}局)')
        print(f'    牌路: B{b_count} P{p_count} T{t_count}')
        print(f'    总盈亏: {total:>+10,}')
        print(f'    平均下注: {avg_bet:>10,.0f} | 最大单注: {max_bet:>10,}')
        # 下注大小的变化趋势
        if len(bet_amounts) > 10:
            first_half = sum(bet_amounts[:len(bet_amounts)//2]) / (len(bet_amounts)//2)
            last_half = sum(bet_amounts[len(bet_amounts)//2:]) / (len(bet_amounts) - len(bet_amounts)//2)
            print(f'    前半均注: {first_half:>10,.0f} | 后半均注: {last_half:>10,.0f}')

# 统计分析：跟推荐 vs 不跟推荐的胜率
print('\n=== 补：推荐跟随 vs 逆反 胜率 ===')
follow_wins = 0
follow_losses = 0
for log in all_logs:
    if log.get('userFollowed', False) and log.get('recommendation') is not None:
        pi = log['profitImpact']
        if pi > 0: follow_wins += 1
        elif pi < 0: follow_losses += 1
total_f = follow_wins + follow_losses
print(f'  跟随推荐: 赢{follow_wins} 输{follow_losses} | 胜率{follow_wins/total_f*100:.1f}%' if total_f > 0 else '')

nofollow_wins = 0
nofollow_losses = 0
for log in all_logs:
    if log.get('recommendation') is not None and not log.get('userFollowed', False) and log['profitImpact'] != 0:
        pi = log['profitImpact']
        if pi > 0: nofollow_wins += 1
        elif pi < 0: nofollow_losses += 1
total_nf = nofollow_wins + nofollow_losses
print(f'  逆反推荐: 赢{nofollow_wins} 输{nofollow_losses} | 胜率{nofollow_wins/total_nf*100:.1f}%' if total_nf > 0 else '')

nore_wins = 0
nore_losses = 0
for log in all_logs:
    if log.get('recommendation') is None and log['profitImpact'] != 0:
        pi = log['profitImpact']
        if pi > 0: nore_wins += 1
        elif pi < 0: nore_losses += 1
total_nr = nore_wins + nore_losses
print(f'  自由下注: 赢{nore_wins} 输{nore_losses} | 胜率{nore_wins/total_nr*100:.1f}%' if total_nr > 0 else '')
