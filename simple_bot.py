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
MAX_IMAGES = 4  # Maximum number of images to generate
MAX_WORDS = 700  # Maximum number of words allowed
# Padding will be calculated as 10% of image dimensions with priority to top and right
# Use the w_Aramesh fonts for Arabic/Persian characters
FONT_PATH = "fonts/w_Aramesh Medium.ttf"  # Persian font for regular text
FALLBACK_FONT_PATHS = [
    "fonts/w_Aramesh Medium.ttf",
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
FIRST_LINE_BOLD_FONT = "fonts/w_Aramesh Extra Bold.ttf"  # Bold font for titles

# Persian/Arabic numerals mapping
PERSIAN_DIGITS = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}

# Paragraph indentation constant
PARAGRAPH_INDENT = "    "  # Two non-breaking spaces (NBSP: U+00A0) for paragraph indentation

# Telegram Bot API URL
API_BASE_URL = "https://api.telegram.org/bot"

# User state management for two-step input
user_states = {}  # Dictionary to store user states: {chat_id: {'step': 'waiting_title'|'waiting_text', 'title': str}}

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
        # Preserve leading whitespace (indentation)
        leading_whitespace = ''
        stripped_text = text.lstrip()
        if len(text) > len(stripped_text):
            leading_whitespace = text[:len(text) - len(stripped_text)]
        
        # Split text into sentences and reverse their order for RTL reading
        sentences = stripped_text.split('.')
        # Remove empty strings and strip whitespace from sentences (but preserve leading indent)
        sentences = [s.strip() for s in sentences if s.strip()]
        # Reverse sentence order for RTL flow
        reversed_sentences = sentences[::-1]
        # Join back with periods
        rtl_text = '. '.join(reversed_sentences)
        if stripped_text.endswith('.'):
            rtl_text += '.'
        
        # Restore leading whitespace (indentation)
        final_text = leading_whitespace + rtl_text
        
        logger.info(f"RTL sentence processing: '{text}' -> '{final_text}'")
        return final_text
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

def parse_title_and_text(input_text: str) -> tuple:
    """Parse input text to separate title from body text.
    
    Args:
        input_text: The full input text
        
    Returns:
        Tuple of (title, body_text)
    """
    lines = input_text.strip().split('\n')
    if len(lines) == 0:
        return "", ""
    
    # First non-empty line is the title
    title = lines[0].strip()
    
    # Rest is body text, join with newlines
    body_lines = lines[1:] if len(lines) > 1 else []
    body_text = '\n'.join(body_lines).strip()
    
    return title, body_text

def add_paragraph_indentation(text: str) -> str:
    """Add indentation to the beginning of each paragraph.
    
    A paragraph is defined as a block of text separated by one or more newline characters.
    Inserts exactly four spaces ("    ") at the very beginning of each paragraph string.
    Preserves all existing whitespace characters (spaces, tabs, newlines) exactly as they are.
    
    Args:
        text: The body text
        
    Returns:
        Text with paragraph indentation using four spaces at the start of each paragraph
    """
    if not text:
        return text
    
    # Split text into paragraphs by one or more newlines
    import re
    paragraphs = re.split(r'\n+', text)
    indented_paragraphs = []
    
    for i, paragraph in enumerate(paragraphs):
        if paragraph.strip():  # Only indent non-empty paragraphs
            # Add exactly four spaces at the beginning of each paragraph
            indented_paragraph = "    " + paragraph
            indented_paragraphs.append(indented_paragraph)
        else:
            # Preserve empty paragraphs as-is
            indented_paragraphs.append(paragraph)
    
    # Merge paragraphs back together with single newlines
    return '\n'.join(indented_paragraphs)

def create_text_image(title: str, text: str) -> list:
    """Create image(s) with the given title and text and return the path(s) to the image(s).
    
    Args:
        title: The title text
        text: The body text
        
    Returns:
        List of paths to generated images or empty list if error
    """
    # Body text will be processed for indentation later in get_wrapped_text_and_height
    body_text = text
    
    # Combine title and body for processing
    full_text = title
    if body_text:
        full_text += '\n\n' + body_text
    # Reshape Arabic/Persian text
    reshaped_text = arabic_reshaper.reshape(full_text)
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
    text_length = len(full_text)
    word_count = len(full_text.split())
    
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
    bottom_padding = int(height * 0.2)  # Keep bottom padding
    
    # Calculate text width and height for wrapping
    max_text_width = width - (right_padding + left_padding)
    
    # Function to wrap text and calculate total height with justification and preserved whitespace
    def get_wrapped_text_and_height(text, font, title_font, max_width):
        lines = []
        line_info = []  # Store additional info about each line for justification
        
        # Parse title and body from combined text
        title_part, body_part = parse_title_and_text(text)
        
        # Process title first if it exists
        if title_part:
            # Handle title wrapping - use 0.7 of background width
            title_max_width = int(width * 0.7)  # 0.7 of background width
            title_words = title_part.split()
            current_title_line = []
            
            for word in title_words:
                # Test if adding this word would exceed 0.7 of background width
                test_line = ' '.join(current_title_line + [word])
                test_width = draw.textlength(test_line, title_font)
                
                if test_width <= title_max_width or not current_title_line:
                    current_title_line.append(word)
                else:
                    # Add current line and start new one
                    lines.append(' '.join(current_title_line))
                    line_info.append({'is_empty': False, 'is_title': True, 'is_last_in_paragraph': False, 'words': current_title_line.copy()})
                    current_title_line = [word]
            
            # Add the last title line
            if current_title_line:
                lines.append(' '.join(current_title_line))
                line_info.append({'is_empty': False, 'is_title': True, 'is_last_in_paragraph': True, 'words': current_title_line.copy()})
            
            # Add empty line after title
            lines.append('')
            line_info.append({'is_empty': True, 'is_title': False, 'is_last_in_paragraph': True})
        
        # Process body text if it exists
        if body_part:
            # Split by newlines first to preserve intentional line breaks
            paragraphs = body_part.split('\n')
        
            for paragraph_idx, paragraph in enumerate(paragraphs):
                if not paragraph.strip():  # Preserve empty lines
                    lines.append('')
                    line_info.append({'is_empty': True, 'is_title': False, 'is_last_in_paragraph': True})
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
                            'is_title': False,
                            'is_last_in_paragraph': False,
                            'words': current_line_words.copy()
                        })
                        current_line_words = [word]
                
                # Add the last line of this paragraph
                if current_line_words:
                    lines.append(' '.join(current_line_words))
                    line_info.append({
                        'is_empty': False,
                        'is_title': False,
                        'is_last_in_paragraph': True,
                        'words': current_line_words.copy()
                    })
        
        # Calculate line height and total text height
        line_height = int(font.size * 1.5)  # Add some spacing between lines
        title_line_height = int(title_font.size * 1.5) if title_part else line_height
        
        # Calculate total height considering title uses different line height
        total_text_height = 0
        for i, line_inf in enumerate(line_info):
            if line_inf.get('is_title', False):
                total_text_height += title_line_height
            else:
                total_text_height += line_height
        
        return lines, total_text_height, line_height, line_info
    
    # Find optimal font size
    wrapped_lines = []
    while font_size > MIN_FONT_SIZE:
        font = get_font(font_size)
        title_font_size = int(font_size * 1.2)  # Title is 1.2x the body font size
        title_font = get_font(title_font_size, bold=True)
        wrapped_lines, total_text_height, line_height, line_info = get_wrapped_text_and_height(full_text, font, title_font, max_text_width)
        
        # Check if text can fit in MAX_IMAGES images
        max_text_height_per_image = height - (top_padding + bottom_padding)  # Use height with calculated padding
        total_images_needed = (total_text_height + max_text_height_per_image - 1) // max_text_height_per_image
        
        if total_images_needed <= MAX_IMAGES:
            break
        
        font_size -= 1  # Decrease by 1 for finer control
    
    # If even with minimum font size, text doesn't fit in MAX_IMAGES images, return error
    if font_size <= MIN_FONT_SIZE:
        font = get_font(MIN_FONT_SIZE)
        title_font_size = int(MIN_FONT_SIZE * 1.2)
        title_font = get_font(title_font_size, bold=True)
        wrapped_lines, total_text_height, line_height, line_info = get_wrapped_text_and_height(full_text, font, title_font, max_text_width)
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
            
            # Check if this line is a title
            if current_line_info.get('is_title', False):
                # Use title font (1.2x size, bold)
                title_font_size = int(font.size * 1.2)
                current_font = get_font(title_font_size, bold=True)
            else:
                current_font = font
            
            # Handle positioning based on line type
            line_width = img_draw.textlength(bidi_line, font=current_font)
            
            if current_line_info.get('is_title', False):
                # Title: always center-aligned, bold, font size 1.2x, with proper padding
                # Center the title within the available text area (respecting padding)
                available_width = width - left_padding - right_padding
                x_position = left_padding + (available_width - line_width) // 2
                
                # Ensure title doesn't overflow outside text area
                if x_position < left_padding:
                    x_position = left_padding
                elif x_position + line_width > width - right_padding:
                    x_position = width - right_padding - line_width
            else:
                # Check if this is the first line of a paragraph for RTL right-side indentation
                is_first_line_of_paragraph = False
                if (not current_line_info.get('is_title', False) and 
                    not current_line_info.get('is_empty', False) and
                    global_line_idx > 0):
                    
                    # Check if previous line was empty (indicating start of new paragraph)
                    prev_line_info = line_info[global_line_idx - 1] if global_line_idx > 0 else None
                    is_first_line_of_paragraph = (
                        prev_line_info and prev_line_info.get('is_empty', False) or
                        (prev_line_info and prev_line_info.get('is_title', False))  # First body line after title
                    )
                
                # Calculate RTL indentation width (equivalent to 4 spaces for visibility)
                indent_width = 0
                if is_first_line_of_paragraph:
                    indent_width = img_draw.textlength('    ', current_font)  # 4 spaces width
                    logger.info(f"RTL indentation applied: line {global_line_idx}, indent_width={indent_width}px")
                
                # Body text: apply justification for non-last lines in paragraphs
                if not current_line_info.get('is_last_in_paragraph', True) and len(current_line_info.get('words', [])) > 1:
                    # Adjust justified width to account for RTL indentation
                    justified_width = width - left_padding - right_padding
                    if is_first_line_of_paragraph:
                        justified_width -= indent_width  # Reduce width for indented lines
                    
                    words = bidi_line.split()
                    if len(words) > 1:
                        bidi_line = justify_line(words, current_font, justified_width, img_draw)
                    # Justified text starts from left padding
                    x_position = left_padding
                else:
                    # Non-justified text aligns to right
                    x_position = width - right_padding - line_width
                    if x_position < left_padding:
                        x_position = left_padding
                    
                    # Apply RTL right-side indentation by moving text further left
                    if is_first_line_of_paragraph:
                        original_x = x_position
                        x_position -= indent_width
                        if x_position < left_padding:
                            x_position = left_padding
                        logger.info(f"RTL indentation positioning: x_pos {original_x} -> {x_position} (indent={indent_width}px)")
            
            img_draw.text((x_position, current_y), bidi_line, font=current_font, fill=(0, 0, 0))
            
            # Use appropriate line height based on whether it's a title or body text
            if current_line_info.get('is_title', False):
                current_y += int(current_font.size * 1.5)
            else:
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

def send_start_button(chat_id):
    """Send a message with start button for creating new images."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"{API_BASE_URL}{token}/sendMessage"
    
    keyboard = {
        "inline_keyboard": [[
            {"text": "📝 Create New Image", "callback_data": "start"}
        ]]
    }
    
    data = {
        "chat_id": chat_id,
        "text": "✅ تصویر شما آماده شد!\n\n✅ Your image is ready!\n\nبرای ساخت تصویر جدید دکمه زیر را فشار دهید:\nClick the button below to create a new image:",
        "reply_markup": keyboard
    }
    
    response = requests.post(url, data=data)
    return response.json()

def handle_message(message):
    """Process incoming message and respond appropriately."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    
    # Handle commands
    if text.startswith('/'):
        if text == '/start':
            # Reset user state and ask for title
            user_states[chat_id] = {'step': 'waiting_title'}
            send_message(chat_id, 'سلام! لطفاً ابتدا عنوان خود را وارد کنید:\n\nHello! Please enter your title first:')
        elif text == '/help':
            send_message(chat_id, 'برای شروع /start را بفرستید. ابتدا عنوان، سپس متن را وارد کنید.\n\nSend /start to begin. Enter title first, then text.')
        return
    
    # Get user state
    user_state = user_states.get(chat_id, {})
    current_step = user_state.get('step')
    
    if current_step == 'waiting_title':
        # User is sending the title
        user_states[chat_id] = {'step': 'waiting_text', 'title': text}
        send_message(chat_id, 'عنوان دریافت شد! حالا لطفاً متن خود را وارد کنید:\n\nTitle received! Now please enter your text:')
        return
    
    elif current_step == 'waiting_text':
        # User is sending the text
        title = user_state.get('title', '')
        
        # Check word count limit for the text (not including title)
        word_count = len(text.split())
        if word_count > MAX_WORDS:
            send_message(chat_id, f"متن شما بیش از حد مجاز {MAX_WORDS} کلمه است. لطفاً متن کوتاه‌تری را ارسال کنید.\n\nYour text exceeds the maximum limit of {MAX_WORDS} words. Please send a shorter text.")
            return
        
        # Reset user state
        user_states[chat_id] = {}
        
        # Handle text processing
        processing_msg = send_message(chat_id, "در حال پردازش متن شما...")
        
        try:
            # Create the image(s) with title and text
            image_paths = create_text_image(title, text)
            
            if not image_paths:
                # Text is too long to fit even with minimum font size and max images
                send_message(chat_id, "متن شما بسیار طولانی است. لطفاً متن کوتاه‌تری را ارسال کنید.\n\nYour text is too long. Please send a shorter text (maximum 4 images).")
                return
            
            # If there are multiple images, inform the user
            if len(image_paths) > 1:
                send_message(chat_id, f"متن شما در {len(image_paths)} تصویر قرار داده شده است.\n\nYour text has been placed on {len(image_paths)} images.")
            
            # Send each image back to the user
            for image_path in image_paths:
                send_photo(chat_id, image_path)
                
                # Delete the temporary image file after sending
                os.remove(image_path)
            
            # Send start button after processing is complete
            send_start_button(chat_id)
            
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            send_message(chat_id, "متأسفانه در پردازش متن شما مشکلی پیش آمد. لطفاً دوباره تلاش کنید.\n\nSorry, there was an error processing your text. Please try again.")
    
    else:
        # User hasn't started the process
        send_message(chat_id, 'لطفاً ابتدا /start را بفرستید تا فرآیند را شروع کنید.\n\nPlease send /start first to begin the process.')

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
                    # Process callback query (button press) if present
                    elif 'callback_query' in update:
                        callback_query = update['callback_query']
                        chat_id = callback_query['message']['chat']['id']
                        if callback_query['data'] == 'start':
                            # Reset user state and ask for title
                            user_states[chat_id] = {'step': 'waiting_title'}
                            send_message(chat_id, 'لطفاً ابتدا عنوان خود را وارد کنید:\n\nPlease enter your title first:')
            
            # Sleep briefly to avoid hitting rate limits
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)  # Wait a bit longer if there's an error

if __name__ == '__main__':
    main()
