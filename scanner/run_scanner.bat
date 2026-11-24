@echo off
REM ============================================================
REM  Auto-Start für watchlist_scanner.py (Trading - Level Up)
REM  Wird von der Windows-Aufgabenplanung aufgerufen.
REM  Schreibt scan_<datum>.md + Log nach daily_data\
REM ============================================================
cd /d "%~dp0"
if not exist "daily_data" mkdir "daily_data"
echo ---- Lauf: %date% %time% ---- >> "daily_data\scanner_log.txt"
where py >nul 2>&1
if %errorlevel%==0 (
  py watchlist_scanner.py >> "daily_data\scanner_log.txt" 2>&1
) else (
  python watchlist_scanner.py >> "daily_data\scanner_log.txt" 2>&1
)
echo ---- Ende:  %date% %time% (ExitCode %errorlevel%) ---- >> "daily_data\scanner_log.txt"
