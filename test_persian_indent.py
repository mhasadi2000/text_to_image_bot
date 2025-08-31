#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test script to verify paragraph indentation with Persian text
import sys
import os
sys.path.append(os.path.dirname(__file__))

from simple_bot import create_text_image

def test_persian_indentation():
    """Test the paragraph indentation functionality with Persian text"""
    
    # Test text with multiple Persian paragraphs
    title = "آزمایش تورفتگی"
    text = """حملات رژیم صهیونیستی به ایران، نقض بند ۴ ماده ۲ منشور ملل متحد و تجاوز آشکار علیه جمهوری اسلامی ایران است. پاسخ به این تجاوز حق قانونی و مشروع ایران وفق ماده ۵۱ منشور ملل متحد است و نیروهای مسلح جمهوری اسلامی ایران با تمام قوا و به شیوه‌ای که خود تشخیص می‌دهند در دفاع از کیان ایران درنگ نخواهند کرد.

این پاراگراف دوم است. این هم باید تورفتگی در خط اول داشته باشد.

این پاراگراف سوم است. تورفتگی باید در اینجا هم قابل مشاهده باشد."""
    
    print("Testing Persian paragraph indentation...")
    print(f"Title: {title}")
    print(f"Text: {text}")
    print("\nGenerating image...")
    
    # Create the image
    image_paths = create_text_image(title, text)
    
    if image_paths:
        print(f"✅ Success! Generated {len(image_paths)} image(s):")
        for path in image_paths:
            print(f"  - {path}")
        print("\nCheck the generated image(s) to see if Persian paragraph indentation is visible.")
    else:
        print("❌ Failed to generate image")

if __name__ == "__main__":
    test_persian_indentation()
