#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
WATCHLIST-SCANNER für TRADING - LEVEL UP
========================================
Ein Lauf -> eine Markdown-Tabelle für ALLE Pipeline-Werte. Ersetzt das
Einzel-Screenshotten der Charts. Claude liest danach die erzeugte Datei.

Berechnet je Wert (Tageschart, sofern nicht anders vermerkt):
  - EMA10 / EMA20 / EMA50 / SMA200            -> Stage-2-Stack (Tag)
  - EMA30 Wochenchart                          -> Stage-2 (Woche, Weinstein)
  - RSL27 (Levy = Close / SMA27)               -> Relative Stärke (~stock3 RSL)
  - VOLA  (annualisierte Stdev 30T)            -> Vola-Tier (~stock3 VOLA)
  - MOM14 (Close - Close[-14])                 -> Momentum
  - Vol%  (heutiges Vol / Ø Vol 28T)           -> Vol-Gate #8b (≥100/90-100/<90)
  - AbstHH (Abstand zum 52W-Hoch in %)         -> Überdehnung / Pullback-Reserve
  - dEMA10 (Abstand Close->EMA10 in %)         -> Chase-Warnung (hoch = gestreckt)
Plus Gate-0 (NDX EMA10 vs EMA20), VIX-Regime, Fear&Greed (CNN-Aktien + Crypto),
Sektor-Heatmap (11 SPDR-ETFs = Finviz-Ersatz) und ATR-Überhitzung der offenen Positionen.

WICHTIG (Methodik-Treue):
  - RSL27 + VOLA sind NAHE Äquivalente zu stock3, aber NICHT bit-identisch
    (stock3-Eigenparametrisierung). Für exakte Schwellen bleibt der stock3-
    Screener die Referenz. Werte hier zur Vorselektion / zum Quer-Scan.
  - Vol% des LETZTEN Balkens ist intraday unvollständig -> Vol-Gate erst nach
    US-Close aussagekräftig (Spalte zeigt Warnung wenn Lauf < 22:00 Wien).

Voraussetzung (einmalig):
  python -m pip install yfinance pandas numpy --break-system-packages
Ausführen (nativ auf Windows):
  python watchlist_scanner.py
Ergebnis: Konsole + Datei  daily_data\scan_<YYYYMMDD>.md
"""

import os
import sys
import json
import urllib.request
from datetime import datetime, timezone, timedelta

import yfinance as yf
import pandas as pd
import numpy as np

# ----------------------------------------------------------------------
#  KONFIGURATION  —  bei Bestands-/Pipeline-Änderung HIER anpassen
#  Format:  "Anzeigename": ("yf-Ticker", "Stufe", "Cluster")
#
#  HINWEIS (Public-Repo): Dies ist eine neutrale BEISPIEL-Konfiguration.
#  Im Live-Betrieb stehen hier die eigenen Positionen und die
#  3-Stufen-Pipeline (Stufe 3 = Order-bereit, 2 = Watch mit Kursalarm,
#  1 = Beobachtung). Vor dem ersten Lauf eigene Werte eintragen.
# ----------------------------------------------------------------------
POSITIONS = {
    "NVDA (NVIDIA)":        "NVDA",     # Beispiel-Position
    "CAT (Caterpillar)":    "CAT",      # Beispiel-Position
}

PIPELINE = {
    # --- Stufe 3 Order-bereit (max 2-3) ---
    "Arista Networks":    ("ANET",  "3", "AI-Networking"),
    # --- Stufe 2 Watch (max 5, Kursalarm gesetzt) ---
    "Vertiv":             ("VRT",   "2", "AI-Power"),
    "Palo Alto":          ("PANW",  "2", "Cyber"),
    # --- Stufe 1 Beobachtung (unbegrenzt) ---
    "Micron":             ("MU",    "1", "AI-Memory"),
    "Deere":              ("DE",    "1", "Industrials"),
    "LVMH":               ("MC.PA", "1", "Consumer"),
}

INDEX_TICKER = "^NDX"   # Nasdaq-100 für Gate-0
VIX_TICKER   = "^VIX"   # CBOE Volatility Index — Angst-/Vola-Regime

# SPDR-Sektor-ETFs = Finviz-Heatmap-Ersatz (Sektor-Rotation aus erlaubter Quelle)
SEKTOR_ETFS = {
    "Technology":       "XLK",
    "Communication":    "XLC",
    "Consumer Discr.":  "XLY",
    "Financials":       "XLF",
    "Industrials":      "XLI",
    "Materials":        "XLB",
    "Energy":           "XLE",
    "Health Care":      "XLV",
    "Consumer Staples": "XLP",
    "Utilities":        "XLU",
    "Real Estate":      "XLRE",
}


# ----------------------------------------------------------------------
#  Indikator-Helfer
# ----------------------------------------------------------------------
def ema(series: pd.Series, span: int) -> float:
    return series.ewm(span=span, adjust=False).mean().iloc[-1]


def ema_series(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, length: int) -> float:
    return series.rolling(length).mean().iloc[-1]


def atr(df: pd.DataFrame, length: int = 14) -> float:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(length).mean().iloc[-1]


def fetch(ticker: str, period="1y", interval="1d") -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval,
                     auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()


def analyze(ticker: str) -> dict:
    """Berechnet alle Kennzahlen für einen Wert. Wirft bei Fehler Exception."""
    d = fetch(ticker, period="1y", interval="1d")
    if len(d) < 60:
        raise ValueError("zu wenig Tagesdaten")
    close = d["Close"]
    last = close.iloc[-1]

    e10, e20, e50 = ema(close, 10), ema(close, 20), ema(close, 50)
    s200 = sma(close, 200) if len(close) >= 200 else float("nan")

    # Stage-2 Tag: gestapelt + über SMA200
    if e10 > e20 > e50 and (np.isnan(s200) or last > s200):
        stage_d = "✅"
    elif e10 > e20 and last > e50:
        stage_d = "⚠️"
    else:
        stage_d = "❌"

    # Stage-2 Woche: Close > EMA30W und EMA30W steigend
    try:
        w = fetch(ticker, period="2y", interval="1wk")
        e30w = ema_series(w["Close"], 30)
        rising = e30w.iloc[-1] > e30w.iloc[-5]
        stage_w = "✅" if (w["Close"].iloc[-1] > e30w.iloc[-1] and rising) else "⚠️/❌"
    except Exception:
        stage_w = "?"

    # RSL27 (Levy) = Close / SMA(Close,27)
    rsl = last / sma(close, 27) if len(close) >= 27 else float("nan")

    # VOLA = annualisierte Stdev der Tagesrenditen über 30T
    rets = close.pct_change().dropna()
    vola = rets.tail(30).std() * np.sqrt(252) if len(rets) >= 30 else float("nan")

    # MOM14 absolut
    mom = last - close.iloc[-15] if len(close) >= 15 else float("nan")

    # Vol% = heutiges Volumen / Ø Volumen 28T
    vol = d["Volume"]
    vol_pct = vol.iloc[-1] / vol.rolling(28).mean().iloc[-1] * 100 if len(vol) >= 28 else float("nan")

    # Abstand 52W-Hoch
    hh = d["High"].rolling(min(252, len(d))).max().iloc[-1]
    abst_hh = (last - hh) / hh * 100

    # Abstand Close -> EMA10 (Chase-Warnung)
    d_ema10 = (last - e10) / e10 * 100

    return dict(close=last, e10=e10, e20=e20, e50=e50, s200=s200,
                stage_d=stage_d, stage_w=stage_w, rsl=rsl, vola=vola,
                mom=mom, vol_pct=vol_pct, abst_hh=abst_hh, d_ema10=d_ema10)


# ----------------------------------------------------------------------
#  Markt-Regime: Sektor-ETFs, VIX, Fear & Greed  (Finviz-Ersatz + Sentiment)
# ----------------------------------------------------------------------
def sector_perf():
    """1D + 5D % je SPDR-Sektor-ETF, sortiert nach 1D% absteigend."""
    rows = []
    for name, tk in SEKTOR_ETFS.items():
        try:
            c = fetch(tk, period="1mo")["Close"]
            chg1d = (c.iloc[-1] / c.iloc[-2] - 1) * 100
            chg5d = (c.iloc[-1] / c.iloc[-6] - 1) * 100 if len(c) >= 6 else float("nan")
            rows.append((name, tk, chg1d, chg5d))
        except Exception:
            rows.append((name, tk, float("nan"), float("nan")))
    rows.sort(key=lambda r: (r[2] if not np.isnan(r[2]) else -999), reverse=True)
    return rows


def vix_read():
    """VIX-Level + 1D-Änderung + Regime-Einordnung."""
    c = fetch(VIX_TICKER, period="3mo")["Close"]
    last = c.iloc[-1]
    chg = (last / c.iloc[-2] - 1) * 100
    if last < 15:   reg = "niedrig (Komplacency)"
    elif last < 20: reg = "normal"
    elif last < 30: reg = "erhöht (Stress)"
    else:           reg = "hoch (Panik/Risk-Off)"
    return last, chg, reg


def _http_json(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fear_greed():
    """CNN-Aktien-F&G + Crypto-F&G (alternative.me). Jede Quelle fehlertolerant."""
    res = {}
    try:
        j = _http_json("https://production.dataviz.cnn.io/index/fearandgreed/graphdata")
        fg = j.get("fear_and_greed", {})
        res["cnn"] = (round(float(fg.get("score")), 0), fg.get("rating"))
    except Exception:
        res["cnn"] = None
    try:
        j = _http_json("https://api.alternative.me/fng/?limit=1")
        d0 = j["data"][0]
        res["crypto"] = (int(d0["value"]), d0["value_classification"])
    except Exception:
        res["crypto"] = None
    return res


# ----------------------------------------------------------------------
#  Hauptlauf
# ----------------------------------------------------------------------
def main():
    wien = timezone(timedelta(hours=2))  # CEST (Sommer)
    now = datetime.now(wien)
    stamp = now.strftime("%Y%m%d")
    intraday_warn = now.hour < 22  # vor US-Close = Vol-Balken unvollständig

    lines = []
    md_pre = []   # Gate-0 + Warnungen für den Datei-Kopf
    def out(s=""):
        print(s)
        lines.append(s)

    out("=" * 100)
    out(f"  WATCHLIST-SCANNER  —  {now.strftime('%d.%m.%Y %H:%M')} Wien")
    out("=" * 100)

    # --- Gate-0 ---
    try:
        ndx = fetch(INDEX_TICKER)
        e10, e20 = ema(ndx["Close"], 10), ema(ndx["Close"], 20)
        last = ndx["Close"].iloc[-1]
        delta = e10 - e20
        regime = "🟢 GRÜN (EMA10>EMA20) — Swing-Entries erlaubt" if e10 > e20 \
                 else "🔴 ROT (EMA10<EMA20) — KEIN Neueinstieg"
        out(f"\n[GATE-0]  Nasdaq-100 Close={last:,.1f}  EMA10={e10:,.1f}  EMA20={e20:,.1f}  "
            f"Δ={delta:+,.1f}  ->  {regime}")
        md_pre.append(f"**Gate-0:** NDX Close={last:,.1f} · EMA10={e10:,.1f} EMA20={e20:,.1f} "
                      f"Δ={delta:+,.1f} → {regime}")
    except Exception as ex:
        out(f"\n[GATE-0]  Fehler: {ex}")
        md_pre.append(f"**Gate-0:** Fehler: {ex}")

    if intraday_warn:
        out("\n⚠️  Lauf vor 22:00 Wien -> Vol% des letzten Balkens UNVOLLSTÄNDIG "
            "(Vol-Gate #8b erst nach US-Close aussagekräftig).")
        md_pre.append("⚠️ Lauf vor 22:00 Wien → Vol% letzter Balken unvollständig "
                      "(Vol-Gate #8b erst nach US-Close).")

    # --- Markt-Regime: VIX + Fear & Greed ---
    try:
        vlast, vchg, vreg = vix_read()
        out(f"\n[VIX]  {vlast:,.2f}  ({vchg:+.1f}%)  ->  {vreg}")
        md_pre.append(f"**VIX:** {vlast:,.2f} ({vchg:+.1f}%) → {vreg}")
    except Exception as ex:
        out(f"\n[VIX]  Fehler: {ex}")
        md_pre.append(f"**VIX:** Fehler: {ex}")

    try:
        fg = fear_greed()
        fg_parts = []
        if fg.get("cnn"):
            fg_parts.append(f"CNN-Aktien {int(fg['cnn'][0])} ({fg['cnn'][1]})")
        if fg.get("crypto"):
            fg_parts.append(f"Crypto {fg['crypto'][0]} ({fg['crypto'][1]})")
        fg_str = " · ".join(fg_parts) if fg_parts else "nicht abrufbar"
        out(f"[FEAR&GREED]  {fg_str}")
        md_pre.append(f"**Fear & Greed:** {fg_str}")
    except Exception as ex:
        out(f"[FEAR&GREED]  Fehler: {ex}")

    # --- Positionen + Pipeline Scan ---
    hdr = (f"\n{'Wert':22}{'St':>3} {'Cluster':16} {'S2D':>4}{'S2W':>5} "
           f"{'Close':>9} {'EMA10':>9} {'EMA20':>9} {'EMA50':>9} "
           f"{'RSL27':>6} {'VOLA':>5} {'MOM14':>7} {'Vol%':>6} {'AbHH%':>7} {'dE10%':>6}")
    md = ["| Wert | St | Cluster | S2D | S2W | Close | EMA10 | EMA20 | EMA50 | RSL27 | VOLA | MOM14 | Vol% | AbHH% | dE10% |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def row(name, stage, cluster, r):
        out(f"{name:22}{stage:>3} {cluster:16} {r['stage_d']:>4}{r['stage_w']:>5} "
            f"{r['close']:>9.2f} {r['e10']:>9.2f} {r['e20']:>9.2f} {r['e50']:>9.2f} "
            f"{r['rsl']:>6.3f} {r['vola']:>5.2f} {r['mom']:>7.2f} {r['vol_pct']:>5.0f}% "
            f"{r['abst_hh']:>6.1f}% {r['d_ema10']:>5.1f}%")
        md.append(f"| {name} | {stage} | {cluster} | {r['stage_d']} | {r['stage_w']} | "
                  f"{r['close']:.2f} | {r['e10']:.2f} | {r['e20']:.2f} | {r['e50']:.2f} | "
                  f"{r['rsl']:.3f} | {r['vola']:.2f} | {r['mom']:.2f} | {r['vol_pct']:.0f}% | "
                  f"{r['abst_hh']:.1f}% | {r['d_ema10']:.1f}% |")

    out("\n[POSITIONEN]")
    out(hdr)
    out("-" * 130)
    md.append("| **— POSITIONEN —** | | | | | | | | | | | | | | |")
    for name, tk in POSITIONS.items():
        try:
            row(name, "P", "Position", analyze(tk))
        except Exception as ex:
            out(f"{name:22}  Fehler: {ex}")
            md.append(f"| {name} | P | FEHLER: {ex} | | | | | | | | | | | | |")

    out("\n[PIPELINE]")
    out(hdr)
    out("-" * 130)
    md.append("| **— PIPELINE —** | | | | | | | | | | | | | | |")
    for name, (tk, stage, cluster) in PIPELINE.items():
        try:
            row(name, stage, cluster, analyze(tk))
        except Exception as ex:
            out(f"{name:22}  Fehler: {ex}")
            md.append(f"| {name} | {stage} | {cluster} FEHLER: {ex} | | | | | | | | | | | | |")

    # --- ATR-Überhitzung Positionen ---
    out(f"\n[ATR-ÜBERHITZUNG]  (>10x SMA50-Abstand = überhitzt -> Trail eskalieren)")
    out(f"  {'Position':24} {'Kurs':>9} {'SMA50':>9} {'ATR14':>8} {'Abst%':>7} {'xATR':>6}  Flag")
    out("  " + "-" * 76)
    md.append("")
    md.append("**ATR-Überhitzung Positionen:**")
    md.append("| Position | Kurs | SMA50 | ATR14 | Abst% | xATR | Flag |")
    md.append("|---|---|---|---|---|---|---|")
    for name, tk in POSITIONS.items():
        try:
            df = fetch(tk)
            close = df["Close"].iloc[-1]
            s50 = sma(df["Close"], 50)
            a14 = atr(df, 14)
            dist_pct = (close - s50) / s50 * 100
            dist_atr = (close - s50) / a14 if a14 else float("nan")
            flag = "🔴 ÜBERHITZT" if dist_atr > 10 else ("🟠 erhöht" if dist_atr > 7 else "✅ ok")
            out(f"  {name:24} {close:>9.2f} {s50:>9.2f} {a14:>8.2f} {dist_pct:>6.1f}% {dist_atr:>5.1f}x  {flag}")
            md.append(f"| {name} | {close:.2f} | {s50:.2f} | {a14:.2f} | {dist_pct:.1f}% | {dist_atr:.1f}x | {flag} |")
        except Exception as ex:
            out(f"  {name:24} Fehler: {ex}")

    # --- Sektor-Heatmap (SPDR-ETFs) = Finviz-Ersatz ---
    out(f"\n[SEKTOR-HEATMAP]  SPDR-ETFs, sortiert nach 1D% (Finviz-Ersatz)")
    out(f"  {'Sektor':18} {'ETF':>5} {'1D%':>7} {'5D%':>7}")
    out("  " + "-" * 42)
    md.append("")
    md.append("**Sektor-Heatmap (SPDR-ETFs, sortiert nach 1D%) — Finviz-Ersatz:**")
    md.append("| Sektor | ETF | 1D% | 5D% |")
    md.append("|---|---|---|---|")
    try:
        sp = sector_perf()
        for name, tk, c1, c5 in sp:
            c1s = f"{c1:+.2f}" if not np.isnan(c1) else "n/a"
            c5s = f"{c5:+.2f}" if not np.isnan(c5) else "n/a"
            out(f"  {name:18} {tk:>5} {c1s:>7} {c5s:>7}")
            md.append(f"| {name} | {tk} | {c1s} | {c5s} |")
        byname = {n: c1 for n, tk, c1, c5 in sp}
        offensive = np.nanmean([byname["Technology"], byname["Consumer Discr."], byname["Communication"]])
        defensive = np.nanmean([byname["Utilities"], byname["Consumer Staples"], byname["Health Care"]])
        tilt = "🟢 Risk-On" if offensive > defensive else "🔴 Risk-Off"
        out(f"  -> {tilt}  (Offensive Ø {offensive:+.2f}% vs Defensive Ø {defensive:+.2f}%)")
        md.append("")
        md.append(f"_Rotation: {tilt} — Offensive (Tech/Discr/Comm) Ø {offensive:+.2f}% vs "
                  f"Defensive (Util/Staples/Health) Ø {defensive:+.2f}%._")
    except Exception as ex:
        out(f"  Fehler: {ex}")
        md.append(f"| FEHLER | {ex} | | |")

    # --- Legende ---
    out("\n[LEGENDE]  S2D/S2W=Stage-2 Tag/Woche · RSL27=Close/SMA27 (~stock3, Levy) · "
        "VOLA=annual. 30T-Stdev (~stock3) · Vol%=vs Ø28T · AbHH%=Abstand 52W-Hoch · dE10%=Abstand EMA10 (Chase)")
    out("⚠️  RSL27+VOLA sind NAHE Äquivalente, NICHT bit-identisch mit stock3 -> exakte Schwellen via stock3-Screener.")
    md.append("")
    md.append("_Legende: S2D/S2W=Stage-2 Tag/Woche · RSL27=Close/SMA27 (~stock3 Levy) · VOLA=annual. 30T-Stdev (~stock3) · "
              "Vol%=vs Ø28T (intraday unvollständig) · AbHH%=Abstand 52W-Hoch · dE10%=Abstand EMA10 (hoch=Chase). "
              "RSL27+VOLA sind NAHE Äquivalente, NICHT bit-identisch mit stock3._")

    # --- Datei speichern ---
    base = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(base, "daily_data")
    os.makedirs(outdir, exist_ok=True)
    fpath = os.path.join(outdir, f"scan_{stamp}.md")
    header = f"# Watchlist-Scan {now.strftime('%d.%m.%Y %H:%M')} Wien\n\n"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(md_pre) + "\n\n" + "\n".join(md) + "\n")

    out(f"\n✅ Gespeichert: daily_data/scan_{stamp}.md  -> an Claude melden / Claude liest die Datei.")


if __name__ == "__main__":
    main()
