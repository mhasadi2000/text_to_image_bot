# Persian Text to Image Telegram Bot

This Telegram bot takes text messages (particularly Persian/Arabic text) and places them onto background images with proper right-to-left alignment.

## Features

- Places user text onto predefined background images
- Supports right-to-left text (Persian/Arabic)
- Automatically wraps text and adjusts font size to fit
- Uses Vazir font, suitable for Persian/Arabic text

## Setup Instructions

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Create a Telegram Bot**

- Talk to [@BotFather](https://t.me/BotFather) on Telegram
- Create a new bot with the `/newbot` command
- Copy the API token provided by BotFather

3. **Configure the bot**

- Copy `.env.example` to `.env`
- Open `.env` and replace `your_telegram_bot_token_here` with the token from BotFather

4. **Run the bot**

```bash
python bot.py
```

## Usage

1. Start a chat with your bot on Telegram
2. Send any text message
3. The bot will place your text on a random background image and send it back to you

## Background Images

The bot uses images from the `image` folder. You can add more images to this folder to expand the selection.

## Font

The bot automatically downloads the Vazir font, which is suitable for Persian/Arabic text. If you want to use a different font, replace the `FONT_PATH` variable in `bot.py`.

## License

This project is open source and available under the MIT License.
