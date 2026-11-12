@echo off
cd /d "%~dp0"
echo.
echo ========================================
echo  DECISION DRIFT LAB - LOCAL ONLY
 echo ========================================
echo.
echo  Open http://127.0.0.1:8765/
echo  Stop with CTRL+C
 echo  No model, no account, no outbound API calls.
echo.
py -3 -m http.server 8765 --bind 127.0.0.1 --directory docs
if errorlevel 1 (
  echo.
  echo Python launcher not available. Trying python...
  python -m http.server 8765 --bind 127.0.0.1 --directory docs
)
