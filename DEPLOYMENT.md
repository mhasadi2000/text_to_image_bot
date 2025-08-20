# Telegram Bot Deployment Guide

This guide explains how to deploy your Telegram bot with text justification feature using Docker.

## Prerequisites

- Docker installed on your server
- Docker Compose installed (optional but recommended)
- Your Telegram bot token

## Quick Start

### Method 1: Using Docker Compose (Recommended)

1. **Clone/Upload your project** to the server:
   ```bash
   # Upload all files to your server directory
   scp -r /path/to/image_telegram_bot user@server:/path/to/deployment/
   ```

2. **Set up environment variables**:
   ```bash
   cd /path/to/deployment/image_telegram_bot
   
   # Edit .env file with your bot token
   nano .env
   ```
   
   Make sure your `.env` file contains:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

3. **Build and run the bot**:
   ```bash
   # Build and start the container
   docker-compose up -d
   
   # View logs
   docker-compose logs -f telegram-bot
   
   # Stop the bot
   docker-compose down
   ```

### Method 2: Using Docker directly

1. **Build the Docker image**:
   ```bash
   docker build -t telegram-text-bot .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     --name telegram-bot \
     --restart unless-stopped \
     --env-file .env \
     telegram-text-bot
   ```

3. **View logs**:
   ```bash
   docker logs -f telegram-bot
   ```

4. **Stop the container**:
   ```bash
   docker stop telegram-bot
   docker rm telegram-bot
   ```

## Server Deployment Steps

### 1. Prepare Your Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group (optional)
sudo usermod -aG docker $USER
```

### 2. Deploy the Bot

```bash
# Create deployment directory
mkdir -p ~/telegram-bot
cd ~/telegram-bot

# Upload your project files here
# Make sure you have: Dockerfile, docker-compose.yml, simple_bot.py, fonts/, image/, .env

# Build and start
docker-compose up -d

# Check if running
docker-compose ps
```

### 3. Monitor the Bot

```bash
# View real-time logs
docker-compose logs -f

# Check container status
docker-compose ps

# Restart if needed
docker-compose restart

# Update the bot (after code changes)
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Features

- **Text Justification**: Full lines have equal length with distributed spacing
- **RTL Support**: Proper Arabic/Persian text handling
- **Multi-image Support**: Long texts split across multiple images
- **Auto-restart**: Container restarts automatically if it crashes
- **Resource Limits**: Memory and CPU limits to prevent server overload

## Troubleshooting

### Bot not responding
```bash
# Check logs
docker-compose logs telegram-bot

# Verify bot token
docker-compose exec telegram-bot python -c "import os; print('Token:', os.getenv('TELEGRAM_BOT_TOKEN'))"
```

### Container keeps restarting
```bash
# Check logs for errors
docker-compose logs --tail=50 telegram-bot

# Common issues:
# 1. Invalid bot token in .env
# 2. Network connectivity issues
# 3. Missing font files
```

### Update the bot
```bash
# After making code changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## File Structure

```
telegram-bot/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── simple_bot.py
├── requirements.txt
├── .env
├── fonts/
│   └── Vazirmatn-Regular.ttf
└── image/
    └── image_1.jpg
```

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Consider using Docker secrets for production deployments
- Regularly update the base Python image for security patches
- Monitor resource usage to prevent abuse

## Production Considerations

- Set up log rotation to prevent disk space issues
- Use a reverse proxy (nginx) if exposing any web interfaces
- Consider using Docker Swarm or Kubernetes for high availability
- Set up monitoring and alerting for the bot service
