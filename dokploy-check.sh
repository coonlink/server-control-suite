#!/bin/bash
# Script to check deployment status in Dokploy

echo "===== Server Control Suite Deployment Check ====="
echo "Running deployment checks..."
echo

# Check if the container exists
if docker ps -a | grep -q server-control-suite; then
  echo "✅ Container exists"
  
  # Check if it's running
  if docker ps | grep -q server-control-suite; then
    echo "✅ Container is running"
    
    # Get container ID
    CONTAINER_ID=$(docker ps -qf "name=server-control-suite")
    
    # Check environment variables
    echo "Checking environment variables..."
    TELEGRAM_BOT_TOKEN=$(docker exec $CONTAINER_ID printenv TELEGRAM_BOT_TOKEN)
    TELEGRAM_CHAT_ID=$(docker exec $CONTAINER_ID printenv TELEGRAM_CHAT_ID)
    
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
      echo "✅ TELEGRAM_BOT_TOKEN is set"
    else
      echo "❌ TELEGRAM_BOT_TOKEN is not set"
    fi
    
    if [ ! -z "$TELEGRAM_CHAT_ID" ]; then
      echo "✅ TELEGRAM_CHAT_ID is set"
    else
      echo "❌ TELEGRAM_CHAT_ID is not set"
    fi
    
    # Check Python process
    if docker exec $CONTAINER_ID ps aux | grep -q "[p]ython.*server_control_bot.py"; then
      echo "✅ Python process is running"
    else
      echo "❌ Python process is not running"
      echo
      echo "Container logs:"
      docker logs --tail 20 $CONTAINER_ID
    fi
    
    # Check if files are accessible
    echo
    echo "Checking file access..."
    if docker exec $CONTAINER_ID ls -la | grep -q "critical_processes_config.sh"; then
      echo "✅ Configuration files are accessible"
    else
      echo "❌ Configuration files are not accessible"
      echo "Files in container:"
      docker exec $CONTAINER_ID ls -la
    fi
    
  else
    echo "❌ Container exists but is not running"
    echo
    echo "Container logs:"
    docker logs --tail 20 $(docker ps -aqf "name=server-control-suite")
  fi
else
  echo "❌ Container does not exist"
  echo
  echo "Docker images:"
  docker images
  echo
  echo "Docker ps:"
  docker ps -a
fi

echo
echo "===== Check Completed =====" 