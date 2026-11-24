# Methodik — das Regelwerk

> 🔴 **NICHT GELTEND — historischer Stand vom Juli 2026** (alle Dateien dieses Repos tragen
> das Datum 20.07.2026). Gekennzeichnet am 25.09.2026.
>
> Das geltende Regelwerk ist ausschließlich `Documents\trading\METHODIK.md`. Diese Seite trägt
> denselben Dateinamen und sieht vollständig aus — deshalb der Vermerk: eine Suche nach
> `METHODIK.md` soll nicht zwei geltend aussehende Treffer liefern.
>
> Seit Juli sind Positionsgröße, Stop-System, Ausstiege, KO-Abstand, Heat-Deckel,
> Drawdown-Bremse und die Einstiegs-Gates umgebaut worden. **Einzelne Aussagen dieser Seite
> stimmen trotzdem noch — auch Schutzregeln.** Welche, sagt allein das geltende Regelwerk;
> diese Seite ist dafür weder Beleg noch Gegenbeleg. Die heutigen Werte stehen bewusst
> **nicht** hier: jede zweite ausschreibende Stelle läuft der ersten hinterher.
>
> Der mitgelieferte Backtest (`backtest/backtest_methodik_v6.py`) folgt dieser Seite nicht in
> allen Parametern — u. a. bei Hebel und KO-Abstand, Stop und Trail sowie Positionszahl gegen
> Heat-Deckel. Der Satz „Alle Werte hier sind die Methodik-Parameter des Projekts" im ersten
> Absatz gilt nicht mehr.
>
> **Vor einer Veröffentlichung entscheidet Günter:** aktualisieren, ersetzen oder aus dem Repo
> nehmen.

Regelbasiertes Swing-Trading auf US-Aktien, umgesetzt über Hebelprodukte (Mini-Futures /
Turbo-KO-Zertifikate). Grundlage: Trendfolge nach Stan Weinstein (Stage-Analyse),
Relative Stärke nach Robert Levy, Volumen-Bestätigung, striktes Risiko-Management.
Alle Werte hier sind die Methodik-Parameter des Projekts — **keine Anlageberatung**.

Die Zahlen in diesem Dokument sind bewusst als **Prozent vom Kapital bzw. R-Multiples**
formuliert (1R = das pro Trade riskierte Kapital). So bleibt die Methodik unabhängig von
der Depotgröße auswertbar und vergleichbar.

---

## 1. Hard Gates — neun Pflicht-Prüfungen vor jedem Trade

Kein Einstieg, solange auch nur ein Gate rot ist. Die Gates sind das Ergebnis
dokumentierter Fehltrades und werden empirisch nachgeschärft (alle 20–30 Trades).

| # | Gate | Kriterium |
|---|---|---|
| 1 | Katalysator | Belegbarer Kurstreiber mit 4–12 Wochen Horizont — keine bloße Story |
| 2 | Emittenten-Hierarchie | Produktwahl nach Gebühren-Tier des Emittenten (gebührenfreie Tiers bevorzugt) |
| 3 | KO-Abstand | ≥ 25 % Abstand der Knock-out-Schwelle zum Aktienkurs |
| 4 | Mindestvolumen | Positionsgröße über der Tier-Schwelle, sonst frisst der Gebühren-Drag die Erwartung |
| 5 | Chance/Risiko | R/R ≥ 2,5 auf Basis Chart-Ziel vs. Initial-Stop |
| 6 | Earnings-Sperre | Kein Neueinstieg 7 Tage (stabile Mega-Caps) bzw. 14 Tage (volatile Werte) vor Zahlen; Termin **immer** über Investor-Relations verifiziert |
| 7 | Klumpungs-Limit | Max. 2 Positionen je GICS-Sektor, max. 1 je Theme-Cluster (Cluster = gemeinsamer fundamentaler Treiber) |
| 8 | Stage 2 (Weinstein) | Kurs über steigender 30-Wochen-EMA + RSL > 1 + Volumen über 28-Wochen-Schnitt |
| 8b | Tages-Volumen-Gate | Bei Tagesschluss-Triggern: Tagesvolumen ≥ 28-Tage-Schnitt (Grauzone 90–100 % nur für Reclaim-Setups; Breakouts idealerweise ≥ 1,5×) — geprüft am Tageschart, nie am Stundenchart |
| 9 | Konvergenz-Score | Mind. 4 von 5 unabhängigen Kriterien erfüllt: Stage 2, Volumen-Bestätigung, RSL > 1, Pattern-Qualität, externer Validator |

## 2. Gate-0 — Markt-Regime-Filter (backtest-validiert)

Vor jedem Neueinstieg: Nasdaq-100-Tageschart, EMA10 vs. EMA20.

- **EMA10 > EMA20 (grün):** Swing-Entries erlaubt.
- **EMA10 < EMA20 (rot):** kein Neueinstieg — **aber nur für Tech-/AI-Werte (Tier A).**

Die Tier-Differenzierung ist das Ergebnis der Backtest-Reihe v1–v6: Für Diversifizierer
außerhalb des Nasdaq-Universums (Tier B) verschlechterte ein harter NDX-Block die
Erwartung — sie folgen ihrem Sektor-Regime, nicht dem Nasdaq. v6 validiert diese Regel
out-of-sample (getrennte Zeitfenster + frisches, zurückgehaltenes Aktien-Set), siehe
`backtest/backtest_methodik_v6.py`.

## 3. Position-Sizing — risikobasiert statt bauchgesteuert

Steuergröße ist das **Risiko pro Trade (1R)** in Prozent des Kapitals, gestaffelt nach
Setup-Qualität (Konvergenz-Score). Mehr Überzeugung bedeutet mehr Risikobudget — nie
eine Ausnahme von den Gates.

| Setup-Qualität | 1R-Ziel (% Kapital) |
|---|---|
| 4/5-Konvergenz | 1,5 % (Basis; steigt erst nach 10–15 disziplinierten Trades mit positiver Erwartung — „Ratchet") |
| 5/5-Konvergenz | 3,5 % |
| A+ (5/5 + parabolisches Pattern + harter Termin) | bis max. 5 % |

**Feste Grenzen (nie verhandelbar, der „Sicherheitsgurt"):**

- **Ruin-Deckel:** 1R ≤ 5 % je Trade — egal, wie gut der Trade aussieht.
- **Portfolio-Heat:** Summe aller offenen 1R ≤ 10 % des Kapitals. Stop im Gewinn = 0 Heat.
- **Konzentrations-Cap:** kein Einzelwert > 25 % des Depots (> 100 % Volatilität: 20 %).
- **Drawdown-Drossel:** −15 % vom Equity-Hoch → alle 1R-Ziele halbieren, bis neues Hoch.
- **Pause-Regel:** 3 Stops in Folge oder −10 % in 14 Tagen → 5 Handelstage keine neuen
  Positionen, nur Trail-Pflege und Methodik-Review.

## 4. Stop-System — gestaffelt, asymmetrisch

Initial-Stop strukturell (unter Pivot/Support), Puffer nach Volatilität des Underlyings.
Danach eine feste Staffel (bezogen auf den Buchgewinn des Hebelprodukts):

| Buchgewinn | Stop-Aktion |
|---|---|
| +50 % | keine Änderung — der Trade darf atmen |
| +100 % | Stop auf Break-Even |
| +150 % / +200 % / +300 % | Stop auf 33 % / 50 % / 66 % des Gewinns |
| +500 % und mehr | 75 % des Gewinns + Wochenhoch-Trail |

Sonderregel für extrem volatile Werte (annualisierte Vola > 100 %): Vor Einstieg
**ATD-Check** (Average True Daily Move = Vola/√252 × Kurs). Liegt der strukturell
korrekte Stop näher als 1,5× ATD am Kurs, ist der Stop nur Tagesrauschen — dann läuft
die Risikokontrolle über Teilverkäufe statt über engere Stops.

Stops werden nur angehoben, nie gesenkt. Nach jeder Order wird die Stop-Existenz im
Broker-System explizit verifiziert (gelernt aus einem dokumentierten Beinahe-Fehler).

## 5. Exits — genau vier legitime Gründe

Stop-Auslösung · Take-Profit am Chart-Ziel · Katalysator abgelaufen · Stage 2 im
Wochenchart verloren. **Nicht** legitim: Nervosität, Bauchgefühl, „der Markt fühlt sich
schwach an". Vor mehrtägigen Handelspausen mit hohem Buchgewinn und Stop unter Einstand:
Default Teilverkauf (Lehre aus einem realen Fall).

## 6. Pipeline — drei Stufen statt Impuls-Trades

| Stufe | Limit | Bedeutung |
|---|---|---|
| 1 Beobachtung | unbegrenzt | Kandidaten mit These |
| 2 Watch | max. 5 | Kursalarm gesetzt, Stage-Check aktiv |
| 3 Order-bereit | max. 2–3 | Produkt gewählt, Trigger definiert, sofort handelbar |

Spontane Trade-Impulse laufen durch einen **Schnellcheck** (6 Punkte, ≤ 5 Minuten) —
die dokumentierte Alternative zum Impuls-Kauf. Empirie im Projekt: ungecheckte
Impuls-Entries waren 0 aus 3 negativ.

## 7. Journal, Statistik, Lern-Schleife

- **Pre-Trade-Doku** (Pflicht, ±1 h um die Order): Setup, Konvergenz-Score, alle Gates,
  Plan (Trigger/Stop/Ziele), Sizing-Begründung.
- **Abschluss-Doku** binnen 24 h: Verlauf, R-Multiple, Exit-Grund, Selbstbewertung, Lehre.
- **Zentrale Statistik:** R-Multiples, Win-Rate, Expectancy — getrennt nach
  methodik-konformen und non-konformen Trades (die Trennung selbst ist eine Regel:
  sonst verfälschen Alt-Trades die Bewertung der Methodik).
- **Missed-Setup-Log:** abgelehnte Setups werden mitsamt späterem Outcome getrackt —
  misst, was die Gates kosten und was sie ersparen.
- **Lehren-Dateien:** jeder relevante Fehler wird als eigene, benannte Regel persistiert
  (z. B. Tages-Vol-Gate, ATD-Mindest-Stop, Konzentrations-Cap) und fließt in die
  Session-Routine ein.

## 8. Tabus

Kein Index-Short als „Hedge" · keine Open-End-Turbos bei Vola > 55 % oder Pre-Revenue ·
keine unverifizieren Fundamental-Claims aus Social Media (IR-Quelle Pflicht) · keine
Positionen unter der Gebühren-Mindestschwelle · kein Nachkauf in Post-Earnings-Spikes
ohne Konsolidierung · keine Veröffentlichung eigener Trades in Social Media.
