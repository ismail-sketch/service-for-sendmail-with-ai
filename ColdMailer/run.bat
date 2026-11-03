@echo off
chcp 65001 >nul
title ColdMailer - Рассылка
cd /d "%~dp0"

echo ========================================
echo         ColdMailer - Запуск рассылки
echo ========================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py sender.py
) else (
    python sender.py
)

echo.
echo ========================================
echo  Работа завершена. Нажмите любую клавишу.
echo ========================================
pause >nul
