@echo off
chcp 65001 >nul 2>&1
echo ============================================================
echo   Trading Bot -- V5 + V7 (TEK PENCERE)
echo ============================================================
echo.
echo   V5: Price Action, filtresiz, risk, 50 coin
echo   V7: Price Action, filtreli,  risk, 200 coin
echo.
echo   Baslamak icin bir tusa basin...
pause >nul

cd /d "%~dp0"

REM Kutuphaneleri kontrol et ve yukle
echo.
echo [1/2] Kutuphaneler kontrol ediliyor...
pip install -q pyyaml python-dotenv pandas numpy ccxt 2>nul
if errorlevel 1 (
    echo Kutuphaneler yukleniyor...
    pip install pyyaml python-dotenv pandas numpy ccxt
)
echo [OK] Kutuphaneler hazir.

echo.
echo [2/2] Bot baslatiliyor...
echo.

REM Venv varsa kullan, yoksa sistem Python'u kullan
IF EXIST "venv\Scripts\python.exe" (
    venv\Scripts\python.exe run_all_bots.py
) ELSE (
    python run_all_bots.py
)
pause
