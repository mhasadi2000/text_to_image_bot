# Persian Text to Image Telegram Bot

A professional Telegram bot that converts Persian/Arabic text into beautifully formatted images with proper RTL (right-to-left) text rendering, justification, and Persian date display.

## Features

- ✅ **RTL Text Support**: Proper Persian/Arabic text rendering with right-to-left flow
- ✅ **Text Justification**: Professional text alignment and spacing
- ✅ **Smart Font Sizing**: Automatic font size adjustment based on text length
- ✅ **Bold First Line**: Enhanced first line with bold Vazirmatn font
- ✅ **Persian Date**: Automatic Persian calendar date in top corner
- ✅ **Multi-Image Support**: Splits long text across multiple images
- ✅ **Professional Layout**: Elegant background with proper padding and margins
- ✅ **Docker Support**: Ready for production deployment

## Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Clone and configure:**
```bash
git clone https://github.com/mhasadi2000/text_to_image_bot.git
cd text_to_image_bot
cp .env.example .env
nano .env  # Add your bot token
```

2. **Deploy with Docker:**
```bash
docker-compose up -d --build
```

3. **Monitor:**
```bash
docker-compose logs -f telegram-bot
```

### Option 2: Manual Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your Telegram bot token
```

3. **Run the bot:**
```bash
python simple_bot.py
```

## Bot Setup

1. **Create Telegram Bot:**
   - Message [@BotFather](https://t.me/BotFather)
   - Use `/newbot` command
   - Copy the provided API token

2. **Configure Token:**
   - Add token to `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

## Usage

1. Start chat with your bot
2. Send `/start` to begin
3. Send any Persian/Arabic text
4. Receive professionally formatted image(s)
5. Use "📝 Create New Image" button to continue

## Technical Features

- **Font Support**: Vazirmatn Regular & Bold fonts
- **Text Processing**: Advanced RTL sentence processing
- **Image Generation**: High-quality JPEG output
- **Resource Management**: Automatic cleanup and optimization
- **Error Handling**: Robust error handling and logging

## File Structure

```
├── simple_bot.py          # Main bot application
├── fonts/                 # Persian/Arabic fonts
│   ├── Vazirmatn-Regular.ttf
│   └── vazirmatn-bold.ttf
├── image/                 # Background images
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables
```

## Docker Management

```bash
# View status
docker-compose ps

# View logs
docker-compose logs telegram-bot

# Restart bot
docker-compose restart

# Stop bot
docker-compose down

# Update after changes
docker-compose up -d --build
```

## Requirements

- Python 3.11+
- PIL/Pillow for image processing
- python-bidi for RTL text
- jdatetime for Persian calendar
- requests for Telegram API

## License

MIT License - Open source and free to use.
