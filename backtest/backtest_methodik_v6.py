#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backtest_methodik_v6.py  —  OUT-OF-SAMPLE-Validierung der Gate-0-Tier-Regel
Teil des Projekts TRADING - LEVEL UP (6. Iteration der Backtest-Reihe v1-v6).

Die v5-Regel (Tier A = harter NDX-Block / Tier B = KEIN Regime-Block) wurde nur
IN-SAMPLE (2021-26, kuratiertes Universum) gefunden -> Ueberanpassung moeglich.
v6 testet sie out-of-sample auf ZWEI unabhaengigen Achsen:

  ACHSE 1 — ZWEI ZEITFENSTER getrennt ausgewertet:
     IN-SAMPLE  : 2021-06 .. 2023-12   (enthaelt 2022er Tech-Baer)
     OUT-SAMPLE : 2024-01 .. 2026-05   (Bull + 2025er Rotation)
     Haelt die Regel in BEIDEN Fenstern unabhaengig?

  ACHSE 2 — FRISCHES, GEHALTENES Diversifizierer-Set:
     20 Namen, die NICHT im v5-Universum waren (VMC/MLM/NEM/COP/EOG/LMT/GD/...).
     Zeigt der Beweis-Test (Tier-B bei rotem Nasdaq besser) auch hier?

VERDIKT je Fenster (automatisch):
  C1 (Tier B): Beweis-Test  Exp(NDX rot) > Exp(NDX gruen)  -> NDX-Block waere falsch.
  C2 (Tier A): Exp(ndx-block) >= Exp(off)                  -> Block fuer Tech ok.
  Beide PASS in IN und OUT (+ frisches Set bestaetigt C1) = Regel out-of-sample robust.

Modell/Exit identisch zu v5. Caveat Survivorship bleibt -> RELATIV/Bedingungs-
Vergleich zaehlt, nicht Absolutwerte.
"""

import yfinance as yf
import pandas as pd
import numpy as np

# ------------------------------------------------------------------ UNIVERSEN
DRIVER = {
    # ---- Tier A (Tech/AI -> QQQ) ----
    "PANW":"QQQ","AMD":"QQQ","VRT":"QQQ","NBIS":"QQQ","MU":"QQQ","ANET":"QQQ",
    "CGNX":"QQQ","AMAT":"QQQ","AVGO":"QQQ","QCOM":"QQQ","DELL":"QQQ","RKLB":"QQQ",
    "CRWD":"QQQ","PLTR":"QQQ","SMCI":"QQQ","FIX":"QQQ","NVDA":"QQQ","INTC":"QQQ","MRVL":"QQQ","ON":"QQQ",
    # ---- Tier B v5 (Diversifizierer, IN-SAMPLE-Set) ----
    "NUE":"XLB","STLD":"XLB","AA":"XLB","CRS":"XLB","ATI":"XLB","FCX":"XLB","CLF":"XLB",
    "BKR":"XLE","MPC":"XLE","VLO":"XLE","SLB":"XLE","DVN":"XLE",
    "ILMN":"XLV","MRNA":"XLV","MOG-A":"XLI","ETN":"XLI","GOOGL":"XLC",
}
# Frisches, GEHALTENES Tier-B-Set (NICHT in v5) — Achse 2
EXTRA_B = {
    "VMC":"XLB","MLM":"XLB","NEM":"XLB","SCCO":"XLB","RS":"XLB",
    "COP":"XLE","EOG":"XLE","OXY":"XLE","PSX":"XLE","HAL":"XLE",
    "VRTX":"XLV","REGN":"XLV","GILD":"XLV","ISRG":"XLV",
    "LMT":"XLI","GD":"XLI","NOC":"XLI","CAT":"XLI","DE":"XLI","PH":"XLI",
}
ALL = dict(DRIVER); ALL.update(EXTRA_B)
ETFS = sorted(set(ALL.values()) | {"QQQ","SPY"})

START, END, BENCH = "2021-01-01", "2026-05-29", "SPY"
EMA_W, BRK, VOLX, ATRN, RSN = 150, 20, 1.5, 14, 50
WIN_IS  = (pd.Timestamp("2021-06-01"), pd.Timestamp("2023-12-31"))
WIN_OOS = (pd.Timestamp("2024-01-01"), pd.Timestamp("2026-05-29"))

def tier_of(tk): return "A" if ALL[tk] == "QQQ" else "B"

BASE = dict(start_eq=10000.0, risk_pct=0.025, max_pos=5, leverage=5.0,   # start_eq = Beispielwert
            stop_atr=1.75, trail_atr=3.0, partial_tp=False,
            fin_rate=0.06, cost_pct=0.005, slippage=True, frictions=True, spx_max_loss=0.015)

# ------------------------------------------------------------------ DATEN
def flat(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df
def atr(d,n):
    tr=pd.concat([d.High-d.Low,(d.High-d.Close.shift()).abs(),(d.Low-d.Close.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(n).mean()
def ema_reg(c): return c.ewm(span=10).mean() > c.ewm(span=20).mean()

print("Lade Marktdaten (yfinance) ...")
bench_close = flat(yf.download(BENCH,start=START,end=END,progress=False,auto_adjust=True)).Close
REG_ETF={}
for etf in ETFS:
    REG_ETF[etf]=ema_reg(flat(yf.download(etf,start=START,end=END,progress=False,auto_adjust=True)).Close)
spy=flat(yf.download("SPY",start=START,end=END,progress=False,auto_adjust=True))
spy_ok=(spy.Close>spy.Close.ewm(span=20).mean())|(spy.Close.pct_change()>-BASE["spx_max_loss"])

FRAMES={}
for tk in ALL:
    try: d=flat(yf.download(tk,start=START,end=END,progress=False,auto_adjust=True)).dropna()
    except Exception: d=pd.DataFrame()
    if len(d)<EMA_W+RSN+5:
        print(f"  (uebersprungen: {tk})"); continue
    d["EMA"]=d.Close.ewm(span=EMA_W).mean(); d["SLOPE"]=d.EMA.diff(10); d["ATR"]=atr(d,ATRN)
    d["HHprev"]=d.Close.rolling(BRK).max().shift(1); d["VAVG"]=d.Volume.rolling(50).mean()
    rs=d.Close/bench_close.reindex(d.index).ffill(); d["RS"]=rs/rs.rolling(RSN).mean()
    d["SIG"]=((d.Close>d.EMA)&(d.SLOPE>0)&(d.RS>1)&(d.Close>=d.HHprev)&(d.Volume>VOLX*d.VAVG)&(d.ATR>0))
    rn=REG_ETF["QQQ"].reindex(d.index).ffill().fillna(False)
    rd=REG_ETF[ALL[tk]].reindex(d.index).ffill().fillna(False)
    sx=spy_ok.reindex(d.index).ffill().fillna(True)
    d["REG_NDX"]=rn
    d["REG_SECTOR"]= rd if tier_of(tk)=="A" else (rd & sx)
    FRAMES[tk]=d
print(f"  {len(FRAMES)} Ticker geladen.\n")
CAL=sorted(set().union(*[set(d.index) for d in FRAMES.values()]))

# ------------------------------------------------------------------ SIM
def regime_factor(mode,x):
    if mode=="off": return 1.0
    nok=bool(x.REG_NDX); sok=bool(x.REG_SECTOR)
    return {"ndx-block":1.0 if nok else None,"ndx-half":1.0 if nok else 0.5,
            "sektor-block":1.0 if sok else None,"sektor-half":1.0 if sok else 0.5}.get(mode,1.0)
def mtm(pos,date):
    d=FRAMES[pos["tk"]]
    if date not in d.index: return pos["capital"]*pos["rem"]
    px=d.loc[date].Close
    return pos["capital"]*pos["rem"]+(px-pos["entry"])/pos["entry"]*pos["notional"]*pos["rem"]
def try_open(tk,entry,av,date,risk,p,cash,ndx_green):
    ist=entry-p["stop_atr"]*av; sdp=(entry-ist)/entry
    if sdp<=0 or sdp>=1.0/p["leverage"]: return None,cash
    notional=risk/sdp; capital=notional/p["leverage"]
    if capital>cash:
        if cash<=1: return None,cash
        sc=cash/capital; capital*=sc; notional*=sc
    cash-=capital
    if p["frictions"]: cash-=p["cost_pct"]*capital
    return dict(tk=tk,entry=entry,init_stop=ist,stop=ist,notional=notional,capital=capital,
                rem=1.0,tp=False,ko_px=entry*(1-1/p["leverage"]),stop_dist_pct=sdp,
                tier=tier_of(tk),ndx_green=ndx_green),cash

def run(universe,mode,p,window):
    lo,hi=window; subcal=[d for d in CAL if lo<=d<=hi]
    cash,peak,maxdd=p["start_eq"],p["start_eq"],0.0; opens=[]; closed=[]; n_ko=0; eq=[]
    for date in subcal:
        eqs=cash+sum(mtm(po,date) for po in opens)
        still=[]
        for pos in opens:
            d=FRAMES[pos["tk"]]
            if date not in d.index: still.append(pos); continue
            x=d.loc[date]; ex=None; ko=False
            if x.Low<=pos["ko_px"]: ko=True
            else:
                pos["stop"]=max(pos["stop"],x.Close-p["trail_atr"]*x.ATR)
                if p["slippage"] and x.Open<=pos["stop"]: ex=x.Open
                elif x.Low<=pos["stop"]: ex=pos["stop"]
                elif x.Close<x.EMA: ex=x.Close
            if p["frictions"]: cash-=pos["notional"]*pos["rem"]*(1-1/p["leverage"])*p["fin_rate"]/365.0
            r=(x.Close-pos["entry"])/(pos["entry"]-pos["init_stop"])
            if ex is None and not ko and p["partial_tp"] and not pos["tp"] and r>=3.0:
                fr=1/3; cash+=pos["capital"]*fr+(x.Close-pos["entry"])/pos["entry"]*pos["notional"]*fr
                pos["rem"]-=fr; pos["tp"]=True; pos["stop"]=max(pos["stop"],pos["entry"])
            if ko:
                closed.append((pos["tier"],-1.0/(p["leverage"]*pos["stop_dist_pct"]),pos["ndx_green"])); n_ko+=1
            elif ex is not None:
                cash+=pos["capital"]*pos["rem"]+(ex-pos["entry"])/pos["entry"]*pos["notional"]*pos["rem"]
                if p["frictions"]: cash-=p["cost_pct"]*pos["capital"]
                closed.append((pos["tier"],(ex-pos["entry"])/(pos["entry"]-pos["init_stop"]),pos["ndx_green"]))
            else: still.append(pos)
        opens=still; held={po["tk"] for po in opens}
        for tk in universe:
            if len(opens)>=p["max_pos"]: break
            d=FRAMES.get(tk)
            if d is None or date not in d.index or tk in held: continue
            x=d.loc[date]
            if not bool(x.SIG): continue
            fac=regime_factor(mode,x)
            if fac is None: continue
            pos,cash=try_open(tk,x.Close,x.ATR,date,p["risk_pct"]*eqs*fac,p,cash,bool(x.REG_NDX))
            if pos is not None: opens.append(pos); held.add(tk)
        equity=cash+sum(mtm(po,date) for po in opens)
        peak=max(peak,equity); maxdd=max(maxdd,(peak-equity)/peak) if peak>0 else maxdd; eq.append(equity)
    return dict(final=eq[-1] if eq else p["start_eq"],maxdd=maxdd,n_ko=n_ko,closed=closed)
def st(rows):
    R=[r for _,r,_ in rows]; w=[r for r in R if r>0]
    return dict(n=len(R),wr=(len(w)/len(R) if R else 0),exp=(float(np.mean(R)) if R else 0),sumR=float(np.sum(R)) if R else 0)

UNI_A=[t for t in DRIVER if tier_of(t)=="A" and t in FRAMES]
UNI_B=[t for t in DRIVER if tier_of(t)=="B" and t in FRAMES]
UNI_BX=[t for t in EXTRA_B if t in FRAMES]
MODES=["off","ndx-block","ndx-half","sektor-block","sektor-half"]

def proof(universe,p,window):
    c=run(universe,"off",p,window)["closed"]
    g=[r for r in c if r[2]]; rd=[r for r in c if not r[2]]
    return st(g),st(rd)

def window_report(name,window):
    print("\n"+"#"*120); print(f"### FENSTER {name}: {window[0].date()} .. {window[1].date()}"); print("#"*120)
    print(" Tier B isoliert (5 Modi):")
    for m in MODES:
        r=run(UNI_B,m,BASE,window); s=st(r["closed"])
        print(f"   {m:<13}| End:{r['final']:>9,.0f}E DD:{r['maxdd']*100:>4.1f}% KO:{r['n_ko']:>2} | n{s['n']:>3} WR{s['wr']*100:>4.0f}% Exp{s['exp']:>+5.2f}R sumR{s['sumR']:>+6.1f}")
    print(" Tier A isoliert (Kontrolle):")
    a_off=a_blk=None
    for m in MODES:
        r=run(UNI_A,m,BASE,window); s=st(r["closed"])
        if m=="off": a_off=s
        if m=="ndx-block": a_blk=s
        print(f"   {m:<13}| End:{r['final']:>9,.0f}E DD:{r['maxdd']*100:>4.1f}% KO:{r['n_ko']:>2} | n{s['n']:>3} WR{s['wr']*100:>4.0f}% Exp{s['exp']:>+5.2f}R sumR{s['sumR']:>+6.1f}")
    g,rd=proof(UNI_B,BASE,window)
    print(f" BEWEIS-TEST Tier B (OFF): NDX gruen Exp{g['exp']:>+5.2f}R (n{g['n']}) | NDX ROT Exp{rd['exp']:>+5.2f}R (n{rd['n']}) sumR{rd['sumR']:>+5.1f}")
    c1 = rd['exp'] > g['exp']
    c2 = a_blk['exp'] >= a_off['exp']
    print(f" VERDIKT {name}: C1 TierB(rot>gruen)={'PASS' if c1 else 'FAIL'} | C2 TierA(block>=off)={'PASS' if c2 else 'FAIL'}"
          f"  ==> {'REGEL HAELT' if (c1 and c2) else 'PRUEFEN'}")
    return c1,c2

if __name__=="__main__":
    print("="*120); print("OUT-OF-SAMPLE-VALIDIERUNG GATE-0-TIER-REGEL  (v5: TierA-Block / TierB-kein-Block)")
    print(f"  Universum: {len(UNI_A)} Tier A | {len(UNI_B)} Tier B (v5) | {len(UNI_BX)} Tier B FRISCH (gehalten)")
    print("="*120)

    is_res  = window_report("IN-SAMPLE",  WIN_IS)
    oos_res = window_report("OUT-OF-SAMPLE", WIN_OOS)

    # ACHSE 2 — frisches Tier-B-Set, Beweis-Test in beiden Fenstern
    print("\n"+"#"*120); print("### ACHSE 2 — FRISCHES Tier-B-Set (nicht in v5): Beweis-Test"); print("#"*120)
    for nm,win in [("IN-SAMPLE",WIN_IS),("OUT-OF-SAMPLE",WIN_OOS)]:
        g,rd=proof(UNI_BX,BASE,win)
        ok = rd['exp']>g['exp']
        print(f"  {nm:<13}: NDX gruen Exp{g['exp']:>+5.2f}R (n{g['n']}) | NDX ROT Exp{rd['exp']:>+5.2f}R (n{rd['n']}) "
              f"sumR{rd['sumR']:>+5.1f}  -> {'PASS' if ok else 'FAIL'}")

    print("\n"+"="*120)
    print("GESAMT-VERDIKT:")
    print(f"  IN-SAMPLE   C1/C2 = {is_res}")
    print(f"  OUT-SAMPLE  C1/C2 = {oos_res}")
    print("  Regel ist OUT-OF-SAMPLE robust, wenn beide Fenster C1+C2 PASS UND das frische Set C1 bestaetigt.")
    print("  Bei FAIL in OOS: Tier-Regel NICHT locken -> Konfidenz senken, Block-Schaerfe/halbe-Pos neu abwaegen.")
    print("  Caveat: Survivorship-Bias bleibt -> Bedingungs-/Relativ-Vergleich zaehlt, nicht Absolut-Endwerte.")
