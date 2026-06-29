# -*- coding: utf-8 -*-
"""backtest_100coins.py — 100 Coin × 100 Gün × $10,000 Backtest"""
import pandas as pd
import numpy as np
import os, sys, glob
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r"C:\Users\52tuz\Desktop\deneme borsa\data\historical_100d_15m_all"
INITIAL_CAPITAL = 10000.0
LEVERAGE = 5
COMMISSION_RATE = 0.00063
RISK_PER_TRADE = 0.01

def calc_atr(df, p=14):
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift(1)).abs()
    lc = (df['low'] - df['close'].shift(1)).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(p).mean()

def run_bt(df, sym):
    df = df.copy()
    df['dt'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('dt').reset_index(drop=True)
    df['sh'] = df['high'].shift(1).rolling(100).max()
    df['sl'] = df['low'].shift(1).rolling(100).min()
    df['ema'] = df['close'].ewm(span=180, adjust=False).mean()
    df['atr'] = calc_atr(df)
    df['vol20'] = df['close'].pct_change(20).abs() * 100

    cap = INITIAL_CAPITAL
    pos = None
    trades = []
    max_cap = INITIAL_CAPITAL
    max_dd = 0
    start = 200
    lbi, lbl = -1, 0.0
    lbi2, lbh = -1, 0.0

    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    o = df['open'].values
    sh = df['sh'].values
    sl_v = df['sl'].values
    ema = df['ema'].values
    atr = df['atr'].values
    vol = df['vol20'].values

    for i in range(start, len(df)):
        if pd.isna(ema[i]) or pd.isna(atr[i]) or atr[i]==0: continue
        cr = h[i]-l[i]
        if cr == 0: continue
        if pd.isna(vol[i]) or vol[i] < 0.3: continue

        if pos:
            hit_sl = hit_tp = False
            if pos['t']=='LONG':
                if l[i]<=pos['sl']: hit_sl=True
                elif h[i]>=pos['tp']: hit_tp=True
            else:
                if h[i]>=pos['sl']: hit_sl=True
                elif l[i]<=pos['tp']: hit_tp=True
            if hit_sl or hit_tp:
                ep = pos['sl'] if hit_sl else pos['tp']
                pp = (ep-pos['e'])/pos['e'] if pos['t']=='LONG' else (pos['e']-ep)/pos['e']
                pnl = pp*pos['sz']*LEVERAGE - pos['sz']*COMMISSION_RATE*LEVERAGE*2
                cap += pnl
                trades.append({'pnl': pnl, 'w': pnl>0})
                pos = None

        if pos:
            if cap>max_cap: max_cap=cap
            dd=(max_cap-cap)/max_cap*100
            if dd>max_dd: max_dd=dd
            continue

        if l[i]<sl_v[i] and c[i]>sl_v[i]:
            lw=min(c[i],o[i])-l[i]
            if cr>0 and (lw/cr>=0.35 or (c[i]>o[i] and c[i-1]<o[i-1])):
                lbi=i; lbl=l[i]; lbi2=-1
        if h[i]>sh[i] and c[i]<sh[i]:
            uw=h[i]-max(c[i],o[i])
            if cr>0 and (uw/cr>=0.35 or (c[i]<o[i] and c[i-1]>o[i-1])):
                lbi2=i; lbh=h[i]; lbi=-1

        if lbi!=-1 and i-lbi<=7:
            if c[i]>max(c[i-1],c[i-2],c[i-3]) and c[i]>ema[i]:
                sl2=lbl-atr[i]*0.6
                risk=c[i]-sl2
                if risk>0:
                    tp=c[i]+5.5*risk
                    sz=(cap*RISK_PER_TRADE)/(risk/c[i]*LEVERAGE)
                    if sz>0 and sz*LEVERAGE<=cap:
                        pos={'t':'LONG','e':c[i],'sl':sl2,'tp':tp,'sz':sz}
                        lbi=-1
        elif lbi2!=-1 and i-lbi2<=7:
            if c[i]<min(c[i-1],c[i-2],c[i-3]) and c[i]<ema[i]:
                sl2=lbh+atr[i]*0.6
                risk=sl2-c[i]
                if risk>0:
                    tp=c[i]-5.5*risk
                    sz=(cap*RISK_PER_TRADE)/(risk/c[i]*LEVERAGE)
                    if sz>0 and sz*LEVERAGE<=cap:
                        pos={'t':'SHORT','e':c[i],'sl':sl2,'tp':tp,'sz':sz}
                        lbi2=-1

        if cap>max_cap: max_cap=cap
        dd=(max_cap-cap)/max_cap*100
        if dd>max_dd: max_dd=dd

    if pos:
        ep=c[-1]
        pp=(ep-pos['e'])/pos['e'] if pos['t']=='LONG' else (pos['e']-ep)/pos['e']
        pnl=pp*pos['sz']*LEVERAGE-pos['sz']*COMMISSION_RATE*LEVERAGE*2
        cap+=pnl
        trades.append({'pnl':pnl,'w':pnl>0})

    return trades, cap, max_dd

print("=" * 70)
print("  100 COIN x 100 GUN x $10,000 BACKTEST")
print("  V5 Price Action | 5x Kaldirc | %1 Risk/Trade")
print("=" * 70)

csvs = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
all_trades = []
results = []

for idx, path in enumerate(csvs):
    sym = os.path.basename(path).replace("_15m_100d.csv", "")
    df = pd.read_csv(path)
    trades, cap, dd = run_bt(df, sym)
    pnl = sum(x['pnl'] for x in trades)
    wins = len([x for x in trades if x['w']])
    wr = wins/len(trades)*100 if trades else 0
    all_trades.extend(trades)
    results.append({'sym': sym, 'trades': len(trades), 'wr': wr, 'pnl': pnl, 'dd': dd})
    if (idx+1) % 20 == 0:
        print(f"  [{idx+1:3d}/{len(csvs)}] {sym:20s} {len(trades):3d}m %{wr:.0f} ${pnl:+8.0f}")

n = len(all_trades)
w = len([x for x in all_trades if x['w']])
l = n - w
pnl = sum(x['pnl'] for x in all_trades)
wr = w/n*100 if n else 0

print()
print("=" * 70)
print(f"  Toplam: {n} islem, %{wr:.1f} win ({w}W/{l}L)")
print(f"  PnL: ${pnl:+,.0f}, Final: ${INITIAL_CAPITAL+pnl:,.0f}, ROI: %{pnl/INITIAL_CAPITAL*100:+.1f}")

profitable = [r for r in results if r['pnl'] > 0]
print(f"  Kârli: {len(profitable)}/{len(results)} coin")

print()
print("  EN IYI 10:")
for r in sorted(results, key=lambda x: x['pnl'], reverse=True)[:10]:
    print(f"    {r['sym']:20s} {r['trades']:3d}m %{r['wr']:.0f} ${r['pnl']:+10.0f}")

print()
print("  EN KOTU 10:")
for r in sorted(results, key=lambda x: x['pnl'])[:10]:
    print(f"    {r['sym']:20s} {r['trades']:3d}m %{r['wr']:.0f} ${r['pnl']:+10.0f}")
