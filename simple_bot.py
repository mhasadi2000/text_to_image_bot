#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging
import random
import requests
import dotenv
import jdatetime
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Load environment variables from .env file
dotenv.load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define constants
IMAGE_FOLDER = "image"
DEFAULT_FONT_SIZE = 90  # Increased default font size
MIN_FONT_SIZE = 80  # Increased minimum font size as requested
MAX_FONT_SIZE = 110  # Increased maximum font size as requested
MAX_LINES_PER_IMAGE = 25  # Reduced to account for larger font size
MAX_IMAGES = 3  # Maximum number of images to generate
MAX_WORDS = 400  # Maximum number of words allowed
# Padding will be calculated as 10% of image dimensions with priority to top and right
# Use the Vazirmatn font for Arabic/Persian characters
FONT_PATH = "fonts/Vazirmatn-Regular.ttf"  # Persian font
FALLBACK_FONT_PATHS = [
    "fonts/Vazirmatn-Regular.ttf",
    "/usr/share/fonts/truetype/kacst/KacstBook.ttf",  # Arabic font
    "/usr/share/fonts/truetype/kacst-one/KacstOne.ttf",  # Arabic font
    "/usr/share/fonts/truetype/farsiweb/nazli.ttf",  # Persian font
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux Arabic support
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Common Linux fallback
    "/usr/share/fonts/TTF/DejaVuSans.ttf",  # Alternative Linux path
    "/System/Library/Fonts/Arial.ttf",  # macOS fallback
    "C:/Windows/Fonts/arial.ttf"  # Windows fallback
]
DATE_FONT_SIZE = 70  # Font size for Jalali date (increased by +10)
FIRST_LINE_BOLD_FONT = "fonts/vazirmatn-bold.ttf"  # Bold font for first line

# Persian/Arabic numerals mapping
PERSIAN_DIGITS = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}

# Telegram Bot API URL
API_BASE_URL = "https://api.telegram.org/bot"

def get_font(size, bold=False):
    """Get a font with fallback options, prioritizing Arabic/Persian support.
    
    Args:
        size: Font size
        bold: Whether to use bold font
        
    Returns:
        Font object
    """
    if bold:
        # Try to load the bold font first
        try:
            if os.path.exists(FIRST_LINE_BOLD_FONT):
                return ImageFont.truetype(FIRST_LINE_BOLD_FONT, size)
        except (IOError, OSError):
            pass
    
    for font_path in FALLBACK_FONT_PATHS:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except (IOError, OSError):
            continue
    
    # If no font found, use default
    try:
        return ImageFont.load_default()
    except Exception as e:
        logger.warning(f"Using default font - Arabic/Persian text may not render correctly: {e}")
        return ImageFont.load_default()

def convert_to_persian_numerals(text):
    """Convert Western numerals in text to Persian/Arabic numerals.
    
    Args:
        text: String containing Western numerals
        
    Returns:
        String with Western numerals replaced by Persian/Arabic equivalents
    """
    for western, persian in PERSIAN_DIGITS.items():
        text = text.replace(western, persian)
    return text

def process_arabic_text(text):
    """Process Arabic/Persian text for proper RTL display.
    
    Args:
        text: Raw Arabic/Persian text
        
    Returns:
        Text processed for RTL sentence flow
    """
    try:
        # Split text into sentences and reverse their order for RTL reading
        sentences = text.split('.')
        # Remove empty strings and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        # Reverse sentence order for RTL flow
        reversed_sentences = sentences[::-1]
        # Join back with periods
        rtl_text = '. '.join(reversed_sentences)
        if text.endswith('.'):
            rtl_text += '.'
        
        logger.info(f"RTL sentence processing: '{text}' -> '{rtl_text}'")
        return rtl_text
    except Exception as e:
        logger.error(f"Error processing Arabic text: {e}")
        return text

def justify_line(words, font, target_width, draw_obj):
    """Justify a line by distributing extra spaces between words.
    
    Args:
        words: List of words in the line
        font: Font object for measuring text
        target_width: Target width for the justified line
        draw_obj: ImageDraw object for measuring text
        
    Returns:
        Justified line as a string
    """
    if len(words) <= 1:
        return ' '.join(words)
    
    # Calculate the width of words without extra spaces (simplified for RTL)
    words_width = sum(draw_obj.textlength(word, font) for word in words)
    
    # Calculate the width of normal spaces between words
    normal_spaces_width = (len(words) - 1) * draw_obj.textlength(' ', font)
    
    # Calculate how much extra space we need to distribute
    extra_space_needed = target_width - words_width - normal_spaces_width
    
    if extra_space_needed <= 0:
        return ' '.join(words)
    
    # Calculate how many extra spaces to add between each pair of words
    space_char_width = draw_obj.textlength(' ', font)
    if space_char_width > 0:
        extra_spaces_total = int(extra_space_needed / space_char_width)
        gaps = len(words) - 1
        
        if gaps > 0:
            # Distribute extra spaces as evenly as possible
            extra_spaces_per_gap = extra_spaces_total // gaps
            extra_spaces_remainder = extra_spaces_total % gaps
            
            justified_words = [words[0]]
            for i in range(1, len(words)):
                # Add normal space plus extra spaces
                spaces = ' ' * (1 + extra_spaces_per_gap)
                # Add one more space to the first few gaps to distribute remainder
                if i <= extra_spaces_remainder:
                    spaces += ' '
                justified_words.append(spaces + words[i])
            
            return ''.join(justified_words)
    
    # Fallback to normal spacing if calculation fails
    return ' '.join(words)

def create_text_image(text: str) -> list:
    """Create image(s) with the given text and return the path(s) to the image(s).
    
    Args:
        text: The text to place on the image
        
    Returns:
        List of paths to generated images or empty list if error
    """
    # Reshape Arabic/Persian text
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    # Use only image_1.jpg as the background image
    background_image_path = os.path.join(IMAGE_FOLDER, "image_1.jpg")
    if not os.path.exists(background_image_path):
        logger.error("Background image not found: image_1.jpg")
        return []
    
    # Open the background image and get its original dimensions
    try:
        bg_img = Image.open(background_image_path)
        width, height = bg_img.size
        logger.info(f"Using background image: {background_image_path} with dimensions {width}x{height}")
    except Exception as e:
        logger.error(f"Error opening background image: {e}")
        # Fallback dimensions
        width, height = 800, 600
    
    # Create a temporary image for text measurement
    temp_img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(temp_img)
    
    # Adjust font size based on text length
    text_length = len(text)
    word_count = len(text.split())
    
    if word_count < 100:
        font_size = MAX_FONT_SIZE  # 14pt for shorter texts
    elif word_count < 200:
        font_size = DEFAULT_FONT_SIZE  # 12pt for medium texts
    else:
        # For longer text, use smaller font
        font_size = MIN_FONT_SIZE  # 10pt for longer texts
    
    font = get_font(font_size)
    
    # Calculate padding as 0.1 of image dimensions
    right_padding = int(width * 0.1)  # 0.1 of width for right padding
    left_padding = int(width * 0.1)  # 0.1 of width for left padding
    top_padding = int(height * 0.25)  # Keep top padding for header space
    bottom_padding = int(height * 0.15)  # Keep bottom padding
    
    # Calculate text width and height for wrapping
    max_text_width = width - (right_padding + left_padding)
    
    # Function to wrap text and calculate total height with justification and preserved whitespace
    def get_wrapped_text_and_height(text, font, max_width):
        lines = []
        line_info = []  # Store additional info about each line for justification
        # Split by newlines first to preserve intentional line breaks
        paragraphs = text.split('\n')
        
        for paragraph_idx, paragraph in enumerate(paragraphs):
            if not paragraph.strip():  # Preserve empty lines
                lines.append('')
                line_info.append({'is_empty': True, 'is_last_in_paragraph': True})
                continue
                
            words = paragraph.split(' ')
            current_line_words = [words[0]] if words else []
            
            for word in words[1:]:
                # Try adding the word to the current line
                test_line = ' '.join(current_line_words + [word])
                # For RTL text, we need to measure each line with proper Arabic processing
                processed_test_line = process_arabic_text(test_line)
                test_width = draw.textlength(processed_test_line, font)
                
                if test_width <= max_width:
                    current_line_words.append(word)
                else:
                    # Add the current line to lines
                    lines.append(' '.join(current_line_words))
                    line_info.append({
                        'is_empty': False, 
                        'is_last_in_paragraph': False,
                        'words': current_line_words.copy()
                    })
                    current_line_words = [word]
            
            # Add the last line of this paragraph
            if current_line_words:
                lines.append(' '.join(current_line_words))
                line_info.append({
                    'is_empty': False, 
                    'is_last_in_paragraph': True,
                    'words': current_line_words.copy()
                })
        
        # Calculate line height and total text height
        line_height = int(font.size * 1.5)  # Add some spacing between lines
        total_text_height = len(lines) * line_height
        
        return lines, total_text_height, line_height, line_info
    
    # Find optimal font size
    wrapped_lines = []
    while font_size > MIN_FONT_SIZE:
        font = get_font(font_size)
        wrapped_lines, total_text_height, line_height, line_info = get_wrapped_text_and_height(text, font, max_text_width)
        
        # Check if text can fit in MAX_IMAGES images
        max_text_height_per_image = height - (top_padding + bottom_padding)  # Use height with calculated padding
        total_images_needed = (total_text_height + max_text_height_per_image - 1) // max_text_height_per_image
        
        if total_images_needed <= MAX_IMAGES:
            break
        
        font_size -= 1  # Decrease by 1 for finer control
    
    # If even with minimum font size, text doesn't fit in MAX_IMAGES images, return error
    if font_size <= MIN_FONT_SIZE:
        font = get_font(MIN_FONT_SIZE)
        wrapped_lines, total_text_height, line_height, line_info = get_wrapped_text_and_height(text, font, max_text_width)
        max_text_height_per_image = height - (top_padding + bottom_padding)
        total_images_needed = (total_text_height + max_text_height_per_image - 1) // max_text_height_per_image
        
        if total_images_needed > MAX_IMAGES:
            logger.warning(f"Text too long to fit in {MAX_IMAGES} images even with minimum font size.")
            return []
    
    # Calculate how many lines can fit in each image
    max_lines_per_image = (height - (top_padding + bottom_padding)) // line_height
    
    # Split lines across images
    image_lines = []
    for i in range(0, len(wrapped_lines), max_lines_per_image):
        image_lines.append(wrapped_lines[i:i + max_lines_per_image])
    
    # Limit to MAX_IMAGES
    if len(image_lines) > MAX_IMAGES:
        image_lines = image_lines[:MAX_IMAGES]
    
    output_paths = []
    
    # Create each image
    for img_index, current_lines in enumerate(image_lines):
        # Create a copy of the background image for each output image
        img = bg_img.copy()
        
        # Create an RGBA version for the semi-transparent overlay
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        # Add a very light semi-transparent white overlay to improve text readability
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 30))  # White with alpha=30 (much lighter)
        img = Image.alpha_composite(img, overlay)
        
        # Calculate text block height
        text_block_height = len(current_lines) * line_height
        
        # Use calculated top padding
        start_y = top_padding
        
        # Create a draw object for the actual image
        img_draw = ImageDraw.Draw(img)
        
        # Add Jalali date to top left corner with Persian numerals
        today = jdatetime.datetime.now().strftime("%Y/%m/%d")
        today = convert_to_persian_numerals(today)  # Convert to Persian numerals
        date_font = get_font(DATE_FONT_SIZE)
        date_text = process_arabic_text(today)
        date_width = img_draw.textlength(date_text, font=date_font)
        img_draw.text((left_padding, int(top_padding * 0.5)), date_text, font=date_font, fill=(0, 0, 0))
        
        # Draw each line of text justified within the padding
        current_y = start_y
        usable_width = width - (right_padding + left_padding)
        
        # Calculate which line info corresponds to current lines
        line_start_idx = img_index * max_lines_per_image
        
        for line_idx, line in enumerate(current_lines):
            global_line_idx = line_start_idx + line_idx
            
            # Skip empty lines but still advance the y position
            if not line:
                current_y += line_height
                continue
            
            # Get line info for justification
            current_line_info = line_info[global_line_idx] if global_line_idx < len(line_info) else {'is_empty': False, 'is_last_in_paragraph': True, 'words': line.split()}
            
            # PROPER RTL PROCESSING: Manual sentence reversal for RTL flow
            try:
                # Split line into sentences and reverse their order
                sentences = line.split('.')
                sentences = [s.strip() for s in sentences if s.strip()]
                reversed_sentences = sentences[::-1]
                bidi_line = '. '.join(reversed_sentences)
                if line.endswith('.'):
                    bidi_line += '.'
                logger.info(f"RTL sentence processing: '{line}' -> '{bidi_line}'")
            except Exception as e:
                logger.error(f"RTL processing failed: {e}")
                bidi_line = line
            
            # Use bold font for first line, same size as other lines
            if img_index == 0 and line_idx == 0:
                # Use bold font with same size
                bold_font = get_font(font.size, bold=True)
                current_font = bold_font
            else:
                current_font = font
            
            # Apply justification for all lines
            if not current_line_info.get('is_last_in_paragraph', True) and len(current_line_info.get('words', [])) > 1:
                justified_width = width - left_padding - right_padding
                words = bidi_line.split()
                if len(words) > 1:
                    bidi_line = justify_line(words, current_font, justified_width, img_draw)
            
            # Position all lines consistently
            line_width = img_draw.textlength(bidi_line, font=current_font)
            
            # If justified, align to left padding; otherwise align to right
            if not current_line_info.get('is_last_in_paragraph', True) and len(current_line_info.get('words', [])) > 1:
                # Justified text starts from left padding
                x_position = left_padding
            else:
                # Non-justified text aligns to right
                x_position = width - right_padding - line_width
                if x_position < left_padding:
                    x_position = left_padding
            
            img_draw.text((x_position, current_y), bidi_line, font=current_font, fill=(0, 0, 0))
            current_y += line_height
        
        # Save this image
        output_path = f"output_{img_index+1}.jpg" if len(image_lines) > 1 else "output.jpg"
        # Convert RGBA to RGB before saving as JPEG
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            rgb_img.save(output_path)
        else:
            img.save(output_path)
        output_paths.append(output_path)
        logger.info(f"Saved image {img_index+1} to {output_path}")
    
    return output_paths

def send_message(chat_id, text):
    """Send a text message to a chat."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"{API_BASE_URL}{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(url, data=data)
    return response.json()

def send_photo(chat_id, photo_path):
    """Send a photo to a chat."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"{API_BASE_URL}{token}/sendPhoto"
    with open(photo_path, 'rb') as photo_file:
        files = {'photo': photo_file}
        data = {'chat_id': chat_id}
        response = requests.post(url, data=data, files=files)
    return response.json()

def handle_message(message):
    """Process incoming message and respond appropriately."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    
    # Handle commands
    if text.startswith('/'):
        if text == '/start':
            send_message(chat_id, 'سلام! متن خود را بفرستید تا آن را روی تصویر قرار دهم.\n\nHello! Send me your text and I will place it on an image.')
        elif text == '/help':
            send_message(chat_id, 'متن خود را بفرستید تا آن را روی تصویر قرار دهم.\n\nSend me your text and I will place it on an image.')
        return
    
    # Check word count limit
    word_count = len(text.split())
    if word_count > MAX_WORDS:
        send_message(chat_id, f"متن شما بیش از حد مجاز {MAX_WORDS} کلمه است. لطفاً متن کوتاه‌تری را ارسال کنید.\n\nYour text exceeds the maximum limit of {MAX_WORDS} words. Please send a shorter text.")
        return
    
    # Handle text messages
    processing_msg = send_message(chat_id, "در حال پردازش متن شما...")
    
    try:
        # Create the image(s) with text
        image_paths = create_text_image(text)
        
        if not image_paths:
            # Text is too long to fit even with minimum font size and max images
            send_message(chat_id, "متن شما بسیار طولانی است. لطفاً متن کوتاه‌تری را ارسال کنید.\n\nYour text is too long. Please send a shorter text (maximum 2 images).")
            return
        
        # If there are multiple images, inform the user
        if len(image_paths) > 1:
            send_message(chat_id, f"متن شما در {len(image_paths)} تصویر قرار داده شده است.\n\nYour text has been placed on {len(image_paths)} images.")
        
        # Send each image back to the user
        for image_path in image_paths:
            send_photo(chat_id, image_path)
            
            # Delete the temporary image file after sending
            os.remove(image_path)
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        send_message(chat_id, "متأسفانه در پردازش متن شما مشکلی پیش آمد. لطفاً دوباره تلاش کنید.\n\nSorry, there was an error processing your text. Please try again.")

def get_updates(offset=None):
    """Get updates from Telegram Bot API."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"{API_BASE_URL}{token}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    response = requests.get(url, params=params)
    return response.json()

def main():
    """Start the bot."""
    # Check for Telegram bot token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: No Telegram bot token found. Please set the TELEGRAM_BOT_TOKEN environment variable.")
        print("You can create a .env file based on .env.example")
        return
    
    # Create fonts directory if needed for future use
    if not os.path.exists("fonts"):
        os.makedirs("fonts")
    
    print("Starting bot...")
    last_update_id = None
    
    while True:
        try:
            # Get updates from Telegram
            updates = get_updates(last_update_id)
            
            if updates.get('ok') and updates.get('result'):
                for update in updates['result']:
                    # Update the offset to acknowledge the update
                    last_update_id = update['update_id'] + 1
                    
                    # Process message if present
                    if 'message' in update:
                        handle_message(update['message'])
            
            # Sleep briefly to avoid hitting rate limits
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)  # Wait a bit longer if there's an error

if __name__ == '__main__':
    main()
