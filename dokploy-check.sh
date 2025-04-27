#!/bin/bash
# Script to check deployment status in Dokploy

echo "===== Server Control Suite Deployment Check ====="
echo "Date: $(date)"
echo "Directory: $(pwd)"
echo

# List all files in the current directory
echo "Files in current directory:"
ls -la
echo

# Check if the Dockerfile exists
if [ -f "Dockerfile" ]; then
  echo "✅ Dockerfile exists"
  echo "Dockerfile content:"
  grep -n "ENTRYPOINT" Dockerfile
  echo
else
  echo "❌ Dockerfile is missing"
fi

# Check if the entrypoint script exists
if [ -f "entrypoint.sh" ]; then
  echo "✅ entrypoint.sh exists"
  echo "Permissions:"
  ls -la entrypoint.sh
  echo
else
  echo "❌ entrypoint.sh is missing"
fi

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
    TELEGRAM_BOT_TOKEN=$(docker exec $CONTAINER_ID printenv TELEGRAM_BOT_TOKEN 2>/dev/null || echo "Not set")
    TELEGRAM_CHAT_ID=$(docker exec $CONTAINER_ID printenv TELEGRAM_CHAT_ID 2>/dev/null || echo "Not set")
    
    echo "TELEGRAM_BOT_TOKEN: $TELEGRAM_BOT_TOKEN"
    echo "TELEGRAM_CHAT_ID: $TELEGRAM_CHAT_ID"
    echo
    
    # List files in /app
    echo "Files in /app:"
    docker exec $CONTAINER_ID ls -la /app 2>/dev/null || echo "Cannot access /app"
    echo
    
    # Check if entrypoint.sh exists in the container
    echo "Checking for entrypoint.sh in container:"
    docker exec $CONTAINER_ID find / -name entrypoint.sh 2>/dev/null || echo "entrypoint.sh not found in container"
    echo
    
    # Check container logs
    echo "Container logs:"
    docker logs --tail 20 $CONTAINER_ID
  else
    echo "❌ Container exists but is not running"
    echo
    echo "Container logs:"
    docker logs $(docker ps -aqf "name=server-control-suite")
  fi
else
  echo "❌ Container does not exist"
  echo
  echo "Docker images:"
  docker images
  echo
  echo "Docker containers:"
  docker ps -a
fi

echo
echo "===== Check Completed ====="