@echo off
chcp 65001 >nul
title Tapnow Studio 本地接收器
echo.
echo ========================================
echo   Tapnow Studio 本地接收器
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.x
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 启动服务器
cd /d "%~dp0"
python tapnow-local-server.py

pause
