#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FINNHUB REALTIME-SNAPSHOT für TRADING - LEVEL UP
=================================================
Holt ECHTE Realtime-Kurse (US-Aktien) für alle Positions- und Pipeline-Ticker
über die kostenlose Finnhub-API und schreibt eine Markdown-Tabelle nach
  daily_data\\realtime_<YYYYMMDD_HHMM>.md

WOZU  watchlist_scanner.py nutzt yfinance -> US-Kurse ~15 Min verzögert und
      vor 15:30 Wien = Vortagsschluss. Dieses Skript liefert den ECHTEN aktuellen
      Kurs (Finnhub /quote = realtime für US) -> ideal für Trigger-Check tagsüber.
      Ergänzt den Scanner, ersetzt ihn nicht (Scanner bleibt für EMA/RSL/Vola).

KOSTENLOSER KEY  (60 Calls/min, keine Kreditkarte):
  1. https://finnhub.io/register  -> kostenlos registrieren
  2. Dashboard -> API-Key kopieren
  3. Key bereitstellen, EINE Variante genügt:
       a) Umgebungsvariable:  setx FINNHUB_API_KEY "DEIN_KEY"   (danach NEUES Terminal)
       b) Datei daneben:      finnhub_key.txt  (nur der Key als einzige Zeile)
       c) Konstante unten:    API_KEY_INLINE = "DEIN_KEY"
     (a) oder (b) sind sauberer -> Key landet nicht im Code / Git.

KEINE Zusatzpakete nötig (nur Python-Standardbibliothek).
AUSFÜHREN (nativ Windows):
  python finnhub_realtime.py                 # alle Positions-+Pipeline-Ticker
  python finnhub_realtime.py NVDA AMD MU     # nur diese Ticker
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Ticker aus dem bestehenden Scanner übernehmen (keine Doppelpflege).
# Import ist unkritisch: watchlist_scanner führt beim Import nichts aus
# (main() steht unter dem __name__ == "__main__"-Guard).
try:
    from watchlist_scanner import POSITIONS, PIPELINE
except Exception:
    POSITIONS, PIPELINE = {}, {}

API_KEY_INLINE = ""   # optional: Key hier eintragen (weniger sauber, siehe Kopf)

FINNHUB_URL = "https://finnhub.io/api/v1/quote"
BASE = os.path.dirname(os.path.abspath(__file__))


def load_key() -> str:
    """Key-Suche: Umgebungsvariable -> finnhub_key.txt -> Inline-Konstante."""
    key = os.getenv("FINNHUB_API_KEY", "").strip()
    if key:
        return key
    kf = os.path.join(BASE, "finnhub_key.txt")
    if os.path.exists(kf):
        with open(kf, encoding="utf-8") as f:
            k = f.read().strip()
            if k:
                return k
    if API_KEY_INLINE.strip():
        return API_KEY_INLINE.strip()
    return ""


def is_us_symbol(tk: str) -> bool:
    """Finnhub Free = US-Realtime. Ticker mit Punkt-Suffix (z.B. MB.MI) = Nicht-US."""
    return "." not in tk


def collect_tickers(argv):
    """CLI-Ticker haben Vorrang, sonst Positions + Pipeline aus dem Scanner."""
    if len(argv) > 1:
        return [(t, t) for t in argv[1:]]
    items = []
    for name, tk in POSITIONS.items():
        items.append((name, tk))
    for name, val in PIPELINE.items():
        tk = val[0] if isinstance(val, (list, tuple)) else val
        items.append((name, tk))
    return items


def fetch_quote(symbol: str, key: str, timeout: int = 10) -> dict:
    """Finnhub /quote: {c,d,dp,h,l,o,pc,t}. Nur Standardbibliothek."""
    qs = urllib.parse.urlencode({"symbol": symbol, "token": key})
    req = urllib.request.Request(FINNHUB_URL + "?" + qs,
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    key = load_key()
    if not key:
        print("FEHLER: Kein Finnhub-API-Key gefunden.\n"
              "  -> kostenlos holen auf https://finnhub.io/register , dann EINE Variante:\n"
              '     setx FINNHUB_API_KEY "DEIN_KEY"   (danach neues Terminal)   ODER\n'
              "     finnhub_key.txt neben dieses Skript legen (nur der Key).")
        sys.exit(1)

    wien = timezone(timedelta(hours=2))  # CEST (Sommer). Winter: hours=1.
    now = datetime.now(wien)
    stamp = now.strftime("%Y%m%d_%H%M")

    tickers = collect_tickers(sys.argv)
    if not tickers:
        print("Keine Ticker gefunden (watchlist_scanner nicht importierbar "
              "und keine Ticker als Argument übergeben).")
        sys.exit(1)

    print("=" * 84)
    print(f"  FINNHUB REALTIME-SNAPSHOT  —  {now.strftime('%d.%m.%Y %H:%M')} Wien")
    print("=" * 84)
    hdr = (f"{'Wert':24} {'Sym':7} {'Kurs':>10} {'d%':>8} "
           f"{'Tag-T':>9} {'Tag-H':>9} {'VorClose':>10}")
    print(hdr)
    print("-" * 84)

    md = [f"# Finnhub Realtime-Snapshot {now.strftime('%d.%m.%Y %H:%M')} Wien",
          "",
          "| Wert | Sym | Kurs | d% | Tag-Tief | Tag-Hoch | Vor-Close |",
          "|---|---|---|---|---|---|---|"]

    for name, tk in tickers:
        if not is_us_symbol(tk):
            print(f"{name:24} {tk:7} {'n/a (Finnhub Free = nur US)':>49}")
            md.append(f"| {name} | {tk} | n/a | Finnhub Free = nur US | | | |")
            continue
        try:
            q = fetch_quote(tk, key)
            c = q.get("c")
            dp = q.get("dp")
            lo, hi, pc = q.get("l"), q.get("h"), q.get("pc")
            if not c:  # 0/None -> kein Kurs (unbekanntes Symbol / kein Free-Zugriff)
                print(f"{name:24} {tk:7} {'kein Kurs (Symbol prüfen)':>40}")
                md.append(f"| {name} | {tk} | kein Kurs | | | | |")
                continue
            print(f"{name:24} {tk:7} {c:>10.2f} {dp:>7.2f}% "
                  f"{lo:>9.2f} {hi:>9.2f} {pc:>10.2f}")
            md.append(f"| {name} | {tk} | {c:.2f} | {dp:+.2f}% | "
                      f"{lo:.2f} | {hi:.2f} | {pc:.2f} |")
            time.sleep(0.2)  # 60/min Free-Limit locker eingehalten
        except Exception as ex:
            print(f"{name:24} {tk:7} Fehler: {ex}")
            md.append(f"| {name} | {tk} | FEHLER: {ex} | | | | |")

    md.append("")
    md.append("_Quelle: Finnhub /quote (Realtime US). d% = ggü. Vortagesschluss. "
              "Nicht-US-Ticker (z.B. .MI) im Free-Tier nicht abgedeckt._")

    outdir = os.path.join(BASE, "daily_data")
    os.makedirs(outdir, exist_ok=True)
    fpath = os.path.join(outdir, f"realtime_{stamp}.md")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print("-" * 84)
    print(f"OK Gespeichert: daily_data/realtime_{stamp}.md")


if __name__ == "__main__":
    main()
