#!/bin/bash
# Agentic GraphRAG Web UI Launcher

echo "============================================================"
echo "  Agentic GraphRAG Web UI Launcher"
echo "============================================================"
echo ""
echo "Select UI version:"
echo "  1. Enhanced Modern UI (Recommended)"
echo "  2. Simple Agentic UI"
echo "  3. Original UI"
echo "  0. Exit"
echo ""

read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Launching Enhanced Modern UI..."
        echo "URL: http://localhost:8501"
        echo ""
        streamlit run app_agentic_v2.py --server.port 8501 --server.headless true
        ;;
    2)
        echo ""
        echo "Launching Simple Agentic UI..."
        echo "URL: http://localhost:8502"
        echo ""
        streamlit run app_agentic.py --server.port 8502 --server.headless true
        ;;
    3)
        echo ""
        echo "Launching Original UI..."
        echo "URL: http://localhost:8503"
        echo ""
        streamlit run app.py --server.port 8503 --server.headless true
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac
