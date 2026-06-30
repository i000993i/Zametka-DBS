@echo off
cd /d "%~dp0"
echo Building Zametka...
pyinstaller --clean --noconfirm Zametka.spec
if %errorlevel% neq 0 (
    echo Build failed.
    pause
    exit /b %errorlevel%
)
echo.
echo Copying assets...
xcopy /E /I /Y assets dist\Zametka\_internal\assets >nul
copy uninstall.cmd dist\Zametka\uninstall.cmd >nul
echo.
echo Done. Executable: dist\Zametka\Zametka.exe
echo Icon: dist\Zametka\Zametka.exe (embedded)
echo.
pause
