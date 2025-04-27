#!/bin/bash
# Verification script for Dokploy deployment

echo "===== Server Control Suite Verification Script ====="
echo "Date: $(date)"
echo

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if container exists and is running
if docker ps | grep -q server-control-suite; then
    echo "✅ Container is running"
    
    # Get container ID
    CONTAINER_ID=$(docker ps -qf "name=server-control-suite")
    
    # Check if entrypoint script exists
    if docker exec $CONTAINER_ID ls -la /app/entrypoint.sh &> /dev/null; then
        echo "✅ Entrypoint script exists"
    else
        echo "❌ Entrypoint script is missing"
        echo "Files in /app:"
        docker exec $CONTAINER_ID ls -la /app
    fi
    
    # Check Python process
    if docker exec $CONTAINER_ID ps aux | grep -q "[p]ython.*server_control_bot.py"; then
        echo "✅ Python process is running"
        echo
        echo "Process details:"
        docker exec $CONTAINER_ID ps aux | grep "[p]ython"
    else
        echo "❌ Python process is not running"
        echo
        echo "Container logs:"
        docker logs --tail 20 $CONTAINER_ID
    fi
    
    # Check if all required files are present
    echo
    echo "Checking important files:"
    for file in server_control_bot.py critical_processes_config.sh entrypoint.sh; do
        if docker exec $CONTAINER_ID ls -la /app/$file &> /dev/null; then
            echo "✅ $file exists"
        else
            echo "❌ $file is missing"
        fi
    done
    
    # Check environment variables
    echo
    echo "Environment variables:"
    docker exec $CONTAINER_ID printenv | grep -E 'TELEGRAM|PYTHON'
    
    # Print simple container stats
    echo
    echo "Container stats:"
    docker stats $CONTAINER_ID --no-stream
else
    echo "❌ Container is not running"
    
    echo
    echo "Docker processes:"
    docker ps -a
    
    echo
    echo "Docker logs (if container exists):"
    CONTAINER_ID=$(docker ps -aqf "name=server-control-suite")
    if [ ! -z "$CONTAINER_ID" ]; then
        docker logs --tail 20 $CONTAINER_ID
    else
        echo "No container found"
    fi
fi

echo
echo "===== Verification Complete =====" 