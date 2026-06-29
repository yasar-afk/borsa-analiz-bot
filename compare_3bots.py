# -*- coding: utf-8 -*-
"""compare_3bots.py — V5 vs V6.5 vs V7 Karşılaştırma"""
import pandas as pd
import numpy as np
import os, sys, glob
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r"C:\Users\52tuz\Desktop\deneme borsa\data\historical_100d_15m_all"
INITIAL_CAPITAL = 10000.0
LEVERAGE = 5
COMMISSION = 0.00063

def calc_atr(df, p=14):
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift(1)).abs()
    lc = (df['low'] - df['close'].shift(1)).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(p).mean()

def run_v5(df):
    df = df.copy().sort_values('datetime').reset_index(drop=True)
    df['sh'] = df['high'].shift(1).rolling(100).max()
    df['sl'] = df['low'].shift(1).rolling(100).min()
    df['ema'] = df['close'].ewm(span=180, adjust=False).mean()
    df['atr'] = calc_atr(df)
    cap = INITIAL_CAPITAL; pos = None; trades = []
    lbi, lbl, lbi2, lbh = -1, 0.0, -1, 0.0
    c,h,l,o = df['close'].values, df['high'].values, df['low'].values, df['open'].values
    sh_v,sl_v,ema_v,atr_v = df['sh'].values, df['sl'].values, df['ema'].values, df['atr'].values
    for i in range(200, len(df)):
        if pd.isna(ema_v[i]) or pd.isna(atr_v[i]) or atr_v[i]==0: continue
        cr = h[i]-l[i]
        if cr==0: continue
        if pos:
            hit_sl = (pos['t']=='LONG' and l[i]<=pos['sl']) or (pos['t']=='SHORT' and h[i]>=pos['sl'])
            hit_tp = (pos['t']=='LONG' and h[i]>=pos['tp']) or (pos['t']=='SHORT' and l[i]<=pos['tp'])
            if hit_sl or hit_tp:
                ep = pos['sl'] if hit_sl else pos['tp']
                pp = (ep-pos['e'])/pos['e'] if pos['t']=='LONG' else (pos['e']-ep)/pos['e']
                pnl = pp*pos['sz']*LEVERAGE - pos['sz']*COMMISSION*LEVERAGE*2
                cap += pnl; trades.append({'pnl':pnl,'w':pnl>0}); pos = None
        if pos: continue
        if l[i]<sl_v[i] and c[i]>sl_v[i]:
            if cr>0 and ((min(c[i],o[i])-l[i])/cr>=0.35 or (c[i]>o[i] and c[i-1]<o[i-1])):
                lbi=i; lbl=l[i]; lbi2=-1
        if h[i]>sh_v[i] and c[i]<sh_v[i]:
            if cr>0 and ((h[i]-max(c[i],o[i]))/cr>=0.35 or (c[i]<o[i] and c[i-1]>o[i-1])):
                lbi2=i; lbh=h[i]; lbi=-1
        if lbi!=-1 and i-lbi<=7 and c[i]>max(c[i-1],c[i-2],c[i-3]) and c[i]>ema_v[i]:
            sl2=lbl-atr_v[i]*0.6; risk=c[i]-sl2
            if risk>0:
                tp=c[i]+5.5*risk; sz=(cap*0.02)/(risk/c[i]*LEVERAGE)
                if sz>0 and sz*LEVERAGE<=cap: pos={'t':'LONG','e':c[i],'sl':sl2,'tp':tp,'sz':sz}; lbi=-1
        elif lbi2!=-1 and i-lbi2<=7 and c[i]<min(c[i-1],c[i-2],c[i-3]) and c[i]<ema_v[i]:
            sl2=lbh+atr_v[i]*0.6; risk=sl2-c[i]
            if risk>0:
                tp=c[i]-5.5*risk; sz=(cap*0.02)/(risk/c[i]*LEVERAGE)
                if sz>0 and sz*LEVERAGE<=cap: pos={'t':'SHORT','e':c[i],'sl':sl2,'tp':tp,'sz':sz}; lbi2=-1
    if pos:
        ep=c[-1]; pp=(ep-pos['e'])/pos['e'] if pos['t']=='LONG' else (pos['e']-ep)/pos['e']
        pnl=pp*pos['sz']*LEVERAGE-pos['sz']*COMMISSION*LEVERAGE*2; cap+=pnl; trades.append({'pnl':pnl,'w':pnl>0})
    return trades, cap

def run_v65(df):
    df = df.copy().sort_values('datetime').reset_index(drop=True)
    df['bb_mid'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_up'] = df['bb_mid'] + 2*bb_std
    df['bb_low'] = df['bb_mid'] - 2*bb_std
    delta = df['close'].diff()
    gain = delta.where(delta>0, 0).rolling(14).mean()
    loss = (-delta.where(delta<0, 0)).rolling(14).mean()
    rs = gain/loss
    df['rsi'] = 100 - (100/(1+rs))
    df['atr'] = calc_atr(df)
    cap = INITIAL_CAPITAL; trades = []
    c,h,l = df['close'].values, df['high'].values, df['low'].values
    bb_up,bb_low,rsi,atr_v = df['bb_up'].values, df['bb_low'].values, df['rsi'].values, df['atr'].values
    pos = None
    for i in range(50, len(df)):
        if pd.isna(bb_up[i]) or pd.isna(rsi[i]) or pd.isna(atr_v[i]): continue
        if pos:
            hit_sl = (pos['t']=='LONG' and l[i]<=pos['sl']) or (pos['t']=='SHORT' and h[i]>=pos['sl'])
            hit_tp = (pos['t']=='LONG' and h[i]>=pos['tp']) or (pos['t']=='SHORT' and l[i]<=pos['tp'])
            if hit_sl or hit_tp:
                ep = pos['sl'] if hit_sl else pos['tp']
                pp = (ep-pos['e'])/pos['e'] if pos['t']=='LONG' else (pos['e']-ep)/pos['e']
                pnl = pp*pos['sz']*LEVERAGE - pos['sz']*COMMISSION*LEVERAGE*2
                cap += pnl; trades.append({'pnl':pnl,'w':pnl>0}); pos = None
        if pos: continue
        if rsi[i]<30 and c[i]<bb_low[i]:
            sl=c[i]-2*atr_v[i]; tp=c[i]+3*atr_v[i]; risk=c[i]-sl
            if risk>0:
                sz=(cap*0.02)/(risk/c[i]*LEVERAGE)
                if sz>0 and sz*LEVERAGE<=cap: pos={'t':'LONG','e':c[i],'sl':sl,'tp':tp,'sz':sz}
        elif rsi[i]>70 and c[i]>bb_up[i]:
            sl=c[i]+2*atr_v[i]; tp=c[i]-3*atr_v[i]; risk=sl-c[i]
            if risk>0:
                sz=(cap*0.02)/(risk/c[i]*LEVERAGE)
                if sz>0 and sz*LEVERAGE<=cap: pos={'t':'SHORT','e':c[i],'sl':sl,'tp':tp,'sz':sz}
    if pos:
        ep=c[-1]; pp=(ep-pos['e'])/pos['e'] if pos['t']=='LONG' else (pos['e']-ep)/pos['e']
        pnl=pp*pos['sz']*LEVERAGE-pos['sz']*COMMISSION*LEVERAGE*2; cap+=pnl; trades.append({'pnl':pnl,'w':pnl>0})
    return trades, cap

def run_v7(df):
    df = df.copy().sort_values('datetime').reset_index(drop=True)
    df['sh'] = df['high'].shift(1).rolling(100).max()
    df['sl'] = df['low'].shift(1).rolling(100).min()
    df['ema'] = df['close'].ewm(span=180, adjust=False).mean()
    df['atr'] = calc_atr(df)
    df['vol_ma'] = df['volume'].rolling(50).mean()
    df['vr'] = df['volume'] / df['vol_ma']
    df['vol20'] = df['close'].pct_change(20).abs() * 100
    cap = INITIAL_CAPITAL; pos = None; trades = []
    lbi, lbl, lbi2, lbh = -1, 0.0, -1, 0.0
    c,h,l,o = df['close'].values, df['high'].values, df['low'].values, df['open'].values
    sh_v,sl_v,ema_v,atr_v = df['sh'].values, df['sl'].values, df['ema'].values, df['atr'].values
    vr_v,vol_v = df['vr'].values, df['vol20'].values
    for i in range(200, len(df)):
        if pd.isna(ema_v[i]) or pd.isna(atr_v[i]) or atr_v[i]==0: continue
        cr = h[i]-l[i]
        if cr==0: continue
        if pd.isna(vol_v[i]) or vol_v[i]<0.3: continue
        if pos:
            hit_sl = (pos['t']=='LONG' and l[i]<=pos['sl']) or (pos['t']=='SHORT' and h[i]>=pos['sl'])
            hit_tp = (pos['t']=='LONG' and h[i]>=pos['tp']) or (pos['t']=='SHORT' and l[i]<=pos['tp'])
            if hit_sl or hit_tp:
                ep = pos['sl'] if hit_sl else pos['tp']
                pp = (ep-pos['e'])/pos['e'] if pos['t']=='LONG' else (pos['e']-ep)/pos['e']
                pnl = pp*pos['sz']*LEVERAGE - pos['sz']*COMMISSION*LEVERAGE*2
                cap += pnl; trades.append({'pnl':pnl,'w':pnl>0}); pos = None
        if pos: continue
        if l[i]<sl_v[i] and c[i]>sl_v[i]:
            if cr>0 and ((min(c[i],o[i])-l[i])/cr>=0.35 or (c[i]>o[i] and c[i-1]<o[i-1])):
                lbi=i; lbl=l[i]; lbi2=-1
        if h[i]>sh_v[i] and c[i]<sh_v[i]:
            if cr>0 and ((h[i]-max(c[i],o[i]))/cr>=0.35 or (c[i]<o[i] and c[i-1]>o[i-1])):
                lbi2=i; lbh=h[i]; lbi=-1
        if lbi!=-1 and i-lbi<=7 and c[i]>max(c[i-1],c[i-2],c[i-3]) and c[i]>ema_v[i]:
            vr = vr_v[i] if not pd.isna(vr_v[i]) else 1.0
            if vr < 0.5: continue
            sl2=lbl-atr_v[i]*0.6; risk=c[i]-sl2
            if risk>0:
                tp=c[i]+5.5*risk; sz=(cap*0.01)/(risk/c[i]*LEVERAGE)
                if sz>0 and sz*LEVERAGE<=cap: pos={'t':'LONG','e':c[i],'sl':sl2,'tp':tp,'sz':sz}; lbi=-1
        elif lbi2!=-1 and i-lbi2<=7 and c[i]<min(c[i-1],c[i-2],c[i-3]) and c[i]<ema_v[i]:
            vr = vr_v[i] if not pd.isna(vr_v[i]) else 1.0
            if vr < 0.5: continue
            sl2=lbh+atr_v[i]*0.6; risk=sl2-c[i]
            if risk>0:
                tp=c[i]-5.5*risk; sz=(cap*0.01)/(risk/c[i]*LEVERAGE)
                if sz>0 and sz*LEVERAGE<=cap: pos={'t':'SHORT','e':c[i],'sl':sl2,'tp':tp,'sz':sz}; lbi2=-1
    if pos:
        ep=c[-1]; pp=(ep-pos['e'])/pos['e'] if pos['t']=='LONG' else (pos['e']-ep)/pos['e']
        pnl=pp*pos['sz']*LEVERAGE-pos['sz']*COMMISSION*LEVERAGE*2; cap+=pnl; trades.append({'pnl':pnl,'w':pnl>0})
    return trades, cap

# ─── ANA KARŞILAŞTIRMA ──────────────────────────────────────
print("=" * 75)
print("  3 BOT KARSILASTIRMASI — 100 COIN x 100 GUN x $10,000")
print("=" * 75)

csvs = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
v5_all, v65_all, v7_all = [], [], []
v5_res, v65_res, v7_res = [], [], []

for path in csvs:
    sym = os.path.basename(path).replace("_15m_100d.csv", "")
    df = pd.read_csv(path)
    t5, c5 = run_v5(df)
    t65, c65 = run_v65(df)
    t7, c7 = run_v7(df)
    v5_all.extend(t5); v65_all.extend(t65); v7_all.extend(t7)
    v5_res.append({'sym':sym,'pnl':sum(x['pnl'] for x in t5),'n':len(t5)})
    v65_res.append({'sym':sym,'pnl':sum(x['pnl'] for x in t65),'n':len(t65)})
    v7_res.append({'sym':sym,'pnl':sum(x['pnl'] for x in t7),'n':len(t7)})

def stats(trades):
    n=len(trades); w=len([x for x in trades if x['w']]); l=n-w
    pnl=sum(x['pnl'] for x in trades); wr=w/n*100 if n else 0
    return n, w, l, wr, pnl

s5=stats(v5_all); s65=stats(v65_all); s7=stats(v7_all)

print()
print("  Metrik               V5              V6.5            V7")
print("  " + "-" * 60)
print("  Islem Sayisi         %-14d %-14d %-14d" % (s5[0], s65[0], s7[0]))
print("  Win Rate             %%%-13.1f %%%-13.1f %%%-13.1f" % (s5[3], s65[3], s7[3]))
print("  Toplam PnL           $%-13.0f $%-13.0f $%-13.0f" % (s5[4], s65[4], s7[4]))
print("  Final Sermaye        $%-13.0f $%-13.0f $%-13.0f" % (INITIAL_CAPITAL+s5[4], INITIAL_CAPITAL+s65[4], INITIAL_CAPITAL+s7[4]))
print("  ROI                  %%%-13.1f %%%-13.1f %%%-13.1f" % (s5[4]/INITIAL_CAPITAL*100, s65[4]/INITIAL_CAPITAL*100, s7[4]/INITIAL_CAPITAL*100))

p5=len([r for r in v5_res if r['pnl']>0])
p65=len([r for r in v65_res if r['pnl']>0])
p7=len([r for r in v7_res if r['pnl']>0])
print("  Karli Coin           %-14s %-14s %-14s" % (str(p5)+"/100", str(p65)+"/100", str(p7)+"/100"))

print()
print("=" * 75)
winner = "V7" if s7[4] > s5[4] and s7[4] > s65[4] else ("V6.5" if s65[4] > s5[4] else "V5")
print("  KAZANAN: %s" % winner)
print("  V5:   $10,000 -> $%s  (%%%s)" % ("{:,.0f}".format(INITIAL_CAPITAL+s5[4]), "{:+.1f}".format(s5[4]/INITIAL_CAPITAL*100)))
print("  V6.5: $10,000 -> $%s  (%%%s)" % ("{:,.0f}".format(INITIAL_CAPITAL+s65[4]), "{:+.1f}".format(s65[4]/INITIAL_CAPITAL*100)))
print("  V7:   $10,000 -> $%s  (%%%s)" % ("{:,.0f}".format(INITIAL_CAPITAL+s7[4]), "{:+.1f}".format(s7[4]/INITIAL_CAPITAL*100)))
print("=" * 75)
