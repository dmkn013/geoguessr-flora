"""使用率の観測から次の小バッチ枚数を保守的に提案する。トークン数ではない。"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def recommend(used5, weekly, hours5, hours_week, observations, idle_hours=1):
    if weekly >= 80 or used5 >= 85:
        return {'images': 0, 'reason': '利用率基準により新規判定保留'}
    if used5 >= 70:
        return {'images': 0, 'reason': '通常予算70%到達。保存・検証に余裕を残す'}
    samples = [o for o in observations if o.get('complete', 0) > 0 and
               0 < o.get('end5', 0) - o.get('start5', 0) < 70 and o.get('minutes', 0) > 0][-20:]
    if not samples:
        return {'images': 1 if used5 >= 65 or weekly >= 78 else 4,
                'reason': '初期計測。小バッチ後に必ず使用率を再取得'}
    costs = sorted((o['end5'] - o['start5']) / o['complete'] for o in samples)
    times = sorted(o['minutes'] / o['complete'] for o in samples)
    # 直近20回の90パーセンタイルに25%を上乗せ。共有枠の他作業も除外せず安全側へ。
    cost = costs[math.ceil(len(costs) * .9) - 1] * 1.25
    minutes = times[math.ceil(len(times) * .9) - 1] * 1.25
    weekly_samples = [o for o in samples if 'start_weekly' in o and 'end_weekly' in o
                      and 0 < o['end_weekly'] - o['start_weekly'] < 80]
    # 期限優先。残量を将来の時間枠へ均等配分せず、今の残量から小バッチを計画する。
    # 4枚ごとに実使用率を読み直し、20分の判定＋5分の保存検証以内で反復する。
    allowance5 = 70 - used5
    allowance_week = 80 - weekly
    # 両窓の%は分母が違う。週間窓はその窓の実測差分で独立に計算する。
    # 整数%の差分0は欠測として直近の正の差分を使い、無消費とはみなさない。
    # 全て0/未観測ならweek_countを1に制限して校正を続ける。
    week_costs = sorted((o['end_weekly'] - o['start_weekly']) / o['complete']
                        for o in weekly_samples)
    week_cost = week_costs[math.ceil(len(week_costs) * .9) - 1] * 1.25 if week_costs else None
    week_count = math.floor(allowance_week / week_cost) if week_cost else 1
    count = min(4, math.floor(allowance5 / cost), week_count, math.floor(20 / minutes))
    return {'images': max(0, count), 'usage_points_per_image': round(cost, 4),
            'weekly_points_per_image': round(week_cost, 4) if week_cost else None,
            'minutes_per_image': round(minutes, 3), 'usage_points_this_run': round(allowance5, 3),
            'weekly_points_this_run': round(allowance_week, 3),
            'reason': '5時間30%余力・週間20%余力を残し最大4枚。時間配分・繰越待機なし。完了後に再計画'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log', type=Path, required=True, help='自分のアカウント専用JSONL')
    sub = p.add_subparsers(dest='command', required=True)
    plan = sub.add_parser('plan')
    for flag in ['used5', 'weekly', 'hours5', 'hours-week']:
        plan.add_argument('--' + flag, type=float, required=True)
    report = sub.add_parser('report')
    for flag in ['start5', 'end5', 'start-weekly', 'end-weekly', 'minutes']:
        report.add_argument('--' + flag, type=float, required=True)
    report.add_argument('--complete', type=int, required=True)
    args = p.parse_args()
    if args.command == 'report':
        values = vars(args).copy()
        values.pop('log'); values.pop('command')
        values['recorded_at'] = datetime.now(timezone.utc).isoformat()
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open('a', encoding='utf-8') as f:
            f.write(json.dumps(values, ensure_ascii=False) + '\n')
        print('アカウント使用率の観測を保存。差分をこの作業だけの消費とは断定しません')
    else:
        values = [json.loads(s) for s in args.log.read_text(encoding='utf-8').splitlines() if s.strip()] if args.log.exists() else []
        completed = [v for v in values if v.get('complete', 0) > 0 and v.get('recorded_at')]
        idle = 1
        if completed:
            last = max(datetime.fromisoformat(v['recorded_at']) for v in completed)
            idle = max(1, (datetime.now(timezone.utc) - last).total_seconds() / 3600)
        print(json.dumps(recommend(args.used5, args.weekly, args.hours5, args.hours_week, values, idle_hours=idle), ensure_ascii=False))


if __name__ == '__main__':
    main()
