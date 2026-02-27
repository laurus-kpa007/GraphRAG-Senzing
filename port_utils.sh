#!/bin/bash
# Port utilities for Linux/Mac

check_port() {
    PORT=${1:-8501}
    echo "============================================================"
    echo "  Port Checker - Port $PORT"
    echo "============================================================"
    echo ""

    PID=$(lsof -ti:$PORT 2>/dev/null)

    if [ -z "$PID" ]; then
        echo "✓ Port $PORT is FREE"
    else
        echo "✗ Port $PORT is OCCUPIED"
        echo ""
        echo "Process details:"
        lsof -i:$PORT
        echo ""
        read -p "Kill process $PID? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            kill -9 $PID
            echo "✓ Process $PID killed"
        fi
    fi
}

kill_streamlit() {
    echo "============================================================"
    echo "  Kill All Streamlit Processes"
    echo "============================================================"
    echo ""

    PIDS=$(pgrep -f "streamlit")

    if [ -z "$PIDS" ]; then
        echo "No Streamlit processes found"
    else
        echo "Found Streamlit processes:"
        ps aux | grep streamlit | grep -v grep
        echo ""
        read -p "Kill all Streamlit processes? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            pkill -9 -f streamlit
            echo "✓ All Streamlit processes killed"
        fi
    fi
}

# Main menu
if [ "$1" = "check" ]; then
    check_port $2
elif [ "$1" = "kill" ]; then
    kill_streamlit
else
    echo "Usage:"
    echo "  $0 check [port]  - Check if port is in use (default: 8501)"
    echo "  $0 kill          - Kill all Streamlit processes"
    echo ""
    echo "Examples:"
    echo "  $0 check 8501"
    echo "  $0 kill"
fi
