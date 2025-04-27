#!/bin/bash
# Script to check Docker container status

set -e

echo "=== Server Control Suite Status Check ==="
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "===================================="

# Check if the container is running
if docker ps | grep -q server-control-suite; then
    echo "✅ Container Status: RUNNING"
    
    # Get container ID
    CONTAINER_ID=$(docker ps -qf "name=server-control-suite")
    
    # Print container info
    echo "Container ID: $CONTAINER_ID"
    
    # Get container stats
    echo "==== Container Resources ===="
    docker stats --no-stream $CONTAINER_ID
    
    # Check if the Python process is running inside the container
    if docker exec $CONTAINER_ID ps aux | grep -q "[p]ython.*server_control_bot.py"; then
        echo "✅ Bot Process: RUNNING"
        
        # Show Python process details
        echo "==== Bot Process Details ===="
        docker exec $CONTAINER_ID ps aux | grep "[p]ython"
        
        # Check logs
        echo "==== Recent Logs ===="
        docker logs --tail 20 $CONTAINER_ID
        
        # Test bot functionality
        echo "==== Environment Variables ===="
        docker exec $CONTAINER_ID printenv | grep TELEGRAM
    else
        echo "❌ Bot Process: NOT RUNNING"
        echo "==== Container Logs ===="
        docker logs --tail 50 $CONTAINER_ID
    fi
else
    echo "❌ Container Status: NOT RUNNING"
    
    # Check if the image exists
    if docker images | grep -q server-control-suite; then
        echo "✅ Image Status: EXISTS"
    else
        echo "❌ Image Status: NOT FOUND"
    fi
    
    # Show docker-compose status
    echo "==== Docker Compose Status ===="
    docker-compose ps
fi

echo "===================================="
echo "Check complete" 