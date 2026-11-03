@echo off
chcp 65001 >nul
title ColdMailer - Панель рассылки
cd /d "%~dp0"

echo ================================================
echo        ColdMailer - запуск веб-панели
echo ================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON=py
) else (
    set PYTHON=python
)

rem Проверяем зависимости
%PYTHON% -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo Устанавливаю зависимости...
    %PYTHON% -m pip install -r requirements.txt
    echo.
)

echo Открываю панель: http://127.0.0.1:5000
echo Закройте это окно, чтобы остановить сервер. Ctrl+C тоже подходит.
echo.
start "" http://127.0.0.1:5000
%PYTHON% app.py