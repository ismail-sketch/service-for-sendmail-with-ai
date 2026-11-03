@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Запускаю бота-напоминалку...
py bot.py
pause