@echo off
echo Starting all monitoring systems...
echo.

echo [1/2] Starting Smart Money Monitor...
start "Smart Money Monitor" python monitor_smart_money.py
timeout /t 2 >nul

echo [2/2] Starting Migration Monitor...
start "Migration Monitor" python monitor_pumpportal.py
timeout /t 2 >nul

echo.
echo All monitors started successfully!
echo - Smart Money Monitor: Tracking elite wallets
echo - Migration Monitor: Watching for token graduations
echo.
echo Close this window when done.
pause
