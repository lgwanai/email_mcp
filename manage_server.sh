#!/bin/bash

# Email MCP Server Management Script
# 用于启动、重启和停止邮件MCP服务器

# 从.env文件读取实际端口配置
if [ -f ".env" ]; then
    SERVER_PORT=$(grep "^PORT=" .env | cut -d'=' -f2)
fi
# 如果没有找到端口配置，使用默认值
SERVER_PORT=${SERVER_PORT:-8000}
SERVER_SCRIPT="main.py"
PID_FILE=".server.pid"
LOG_FILE="server.log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查进程是否运行
check_process() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null 2>&1; then
            return 0  # 进程正在运行
        else
            rm -f "$PID_FILE"  # 清理无效的PID文件
            return 1  # 进程未运行
        fi
    else
        return 1  # PID文件不存在
    fi
}

# 通过端口查找并终止进程
kill_by_port() {
    echo -e "${YELLOW}正在查找端口 $SERVER_PORT 上的进程...${NC}"
    local pids=$(lsof -ti:$SERVER_PORT 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}发现进程: $pids${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null
        echo -e "${GREEN}已终止端口 $SERVER_PORT 上的进程${NC}"
        sleep 1
    else
        echo -e "${BLUE}端口 $SERVER_PORT 上没有运行的进程${NC}"
    fi
}

# 启动服务器
start_server() {
    echo -e "${BLUE}启动邮件MCP服务器...${NC}"
    
    if check_process; then
        echo -e "${YELLOW}服务器已经在运行中 (PID: $(cat $PID_FILE))${NC}"
        return 1
    fi
    
    # 确保端口没有被占用
    kill_by_port
    
    # 启动服务器
    echo -e "${BLUE}正在启动服务器...${NC}"
    nohup python "$SERVER_SCRIPT" > "$LOG_FILE" 2>&1 &
    local server_pid=$!
    
    # 保存PID
    echo $server_pid > "$PID_FILE"
    
    # 等待服务器启动
    sleep 3
    
    # 检查服务器是否成功启动
    if check_process; then
        echo -e "${GREEN}✓ 服务器启动成功!${NC}"
        echo -e "${GREEN}  PID: $server_pid${NC}"
        echo -e "${GREEN}  URL: http://localhost:$SERVER_PORT${NC}"
        echo -e "${GREEN}  日志文件: $LOG_FILE${NC}"
    else
        echo -e "${RED}✗ 服务器启动失败${NC}"
        echo -e "${RED}请检查日志文件: $LOG_FILE${NC}"
        return 1
    fi
}

# 停止服务器
stop_server() {
    echo -e "${BLUE}停止邮件MCP服务器...${NC}"
    
    if check_process; then
        local pid=$(cat "$PID_FILE")
        echo -e "${YELLOW}正在停止服务器 (PID: $pid)...${NC}"
        kill $pid 2>/dev/null
        
        # 等待进程结束
        local count=0
        while [ $count -lt 10 ] && ps -p $pid > /dev/null 2>&1; do
            sleep 1
            count=$((count + 1))
        done
        
        # 如果进程仍在运行，强制终止
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}强制终止进程...${NC}"
            kill -9 $pid 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        echo -e "${GREEN}✓ 服务器已停止${NC}"
    else
        echo -e "${YELLOW}服务器未运行${NC}"
    fi
}

# 重启服务器
restart_server() {
    echo -e "${BLUE}重启邮件MCP服务器...${NC}"
    stop_server
    sleep 2
    start_server
}

# 查看服务器状态
status_server() {
    echo -e "${BLUE}邮件MCP服务器状态:${NC}"
    
    if check_process; then
        local pid=$(cat "$PID_FILE")
        echo -e "${GREEN}✓ 服务器正在运行${NC}"
        echo -e "  PID: $pid"
        echo -e "  URL: http://localhost:$SERVER_PORT"
        echo -e "  日志文件: $LOG_FILE"
        
        # 显示内存使用情况
        local memory=$(ps -o rss= -p $pid 2>/dev/null | awk '{print $1/1024 " MB"}')
        if [ -n "$memory" ]; then
            echo -e "  内存使用: $memory"
        fi
    else
        echo -e "${RED}✗ 服务器未运行${NC}"
    fi
    
    # 检查端口占用情况
    local port_process=$(lsof -ti:$SERVER_PORT 2>/dev/null)
    if [ -n "$port_process" ]; then
        echo -e "${YELLOW}⚠ 端口 $SERVER_PORT 被其他进程占用: $port_process${NC}"
    fi
}

# 查看日志
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}显示服务器日志 (最后50行):${NC}"
        echo "----------------------------------------"
        tail -n 50 "$LOG_FILE"
        echo "----------------------------------------"
    else
        echo -e "${YELLOW}日志文件不存在: $LOG_FILE${NC}"
    fi
}

# 实时查看日志
follow_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}实时查看服务器日志 (按 Ctrl+C 退出):${NC}"
        echo "----------------------------------------"
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}日志文件不存在: $LOG_FILE${NC}"
    fi
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}邮件MCP服务器管理脚本${NC}"
    echo ""
    echo "用法: $0 {start|stop|restart|status|logs|follow|help}"
    echo ""
    echo "命令:"
    echo "  start    - 启动服务器"
    echo "  stop     - 停止服务器"
    echo "  restart  - 重启服务器"
    echo "  status   - 查看服务器状态"
    echo "  logs     - 查看服务器日志 (最后50行)"
    echo "  follow   - 实时查看服务器日志"
    echo "  help     - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start     # 启动服务器"
    echo "  $0 restart   # 重启服务器"
    echo "  $0 status    # 查看状态"
}

# 主程序
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status_server
        ;;
    logs)
        show_logs
        ;;
    follow)
        follow_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        echo -e "${RED}错误: 请指定一个命令${NC}"
        echo ""
        show_help
        exit 1
        ;;
    *)
        echo -e "${RED}错误: 未知命令 '$1'${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac