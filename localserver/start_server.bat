@echo off
chcp 65001
echo 正在启动 Tapnow 本地全功能服务器...
cd /d "%~dp0"

:: 检查依赖
python -c "import websocket" 2>nul
if %errorlevel% neq 0 (
    echo [警告] 未检测到 websocket-client 库，正在尝试安装...
    pip install websocket-client
)

:: 启动服务
python tapnow-server-full.py

pause
