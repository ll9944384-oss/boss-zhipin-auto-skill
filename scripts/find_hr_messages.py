#!/usr/bin/env python3
"""Click on specific chat items and check for HR messages."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safari_boss_runner import json_js, click_screen_point

def get_chat_items():
    js = r"""
    var allLis = document.querySelectorAll('.chat-user li');
    var result = [];
    for (var i = 0; i < allLis.length; i++) {
        var r = allLis[i].getBoundingClientRect();
        var text = (allLis[i].innerText || '').trim();
        if (r.width > 50 && r.height > 20 && text.length > 5) {
            result.push({
                index: i,
                text: text.slice(0, 200),
                left: Math.round(r.left),
                top: Math.round(r.top),
                width: Math.round(r.width),
                height: Math.round(r.height)
            });
        }
    }
    return result;
    """
    return json_js(js)

def get_chat_content():
    js = r"""
    var result = {};
    
    // Get header (who we're chatting with)
    var headerEl = document.querySelector('.chat-header, .resume-info, ' +
        '[class*="chat-header"], [class*="resume-info"], ' +
        'header h3, header span, .dialog-title');
    if (headerEl) {
        result.header = (headerEl.innerText || '').trim().slice(0, 100);
    }
    
    // Get the full page text to find messages
    result.pageText = (document.body.innerText || '').trim().slice(0, 6000);
    
    // Check if there's a chat input (means we're in a conversation)
    var inputs = document.querySelectorAll('div[contenteditable="true"], textarea');
    var visibleInputs = [];
    for (var i = 0; i < inputs.length; i++) {
        var r = inputs[i].getBoundingClientRect();
        if (r.width > 20 && r.height > 10) {
            visibleInputs.push(true);
        }
    }
    result.hasInput = visibleInputs.length > 0;
    
    // Check unread badge in the active conversation
    var badges = document.querySelectorAll('.badge, [class*="unread"], [class*="red-dot"]');
    result.badgeFound = badges.length > 0;
    
    // URL
    result.url = location.href;
    
    return result;
    """
    return json_js(js)

def get_screen_info():
    js = r"""
    return {
        x: window.screenX,
        y: window.screenY,
        outerWidth: window.outerWidth,
        outerHeight: window.outerHeight,
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight
    };
    """
    return json_js(js)

# Step 1: Get chat items
print("=== GETTING CHAT ITEMS ===")
items_result = get_chat_items()
print(json.dumps(items_result, ensure_ascii=False, indent=2))

if not items_result.get("ok"):
    print("Failed to get chat items")
    sys.exit(1)

items = items_result.get("result", [])
print(f"\nFound {len(items)} chat items")

# Step 2: Get screen info for coordinate calculations
screen = get_screen_info()
screen_result = screen.get("result", {})
print(f"\nScreen: {json.dumps(screen_result, ensure_ascii=False)}")

# Step 3: Click on each potential HR message conversation and check content
# Target conversations (by index in the items list):
# Item 2 = <HR>先生 (origin plan, 动画剪辑 合肥)
# Item 3 = <HR_NAME> (COMPANY_6, asking for resume)

target_indices = [2, 3, 0, 1]  # Try in order of priority

for idx in target_indices:
    if idx >= len(items):
        continue
    
    item = items[idx]
    item_text = item.get('text', '')
    print(f"\n=== CLICKING ITEM {idx}: {item_text[:80]} ===")
    
    # Calculate center point
    center_x = item['left'] + item['width'] // 2
    center_y = item['top'] + item['height'] // 2
    
    # Convert to screen coordinates
    chrome_left = max((screen_result.get("outerWidth", 1512) - screen_result.get("innerWidth", 1512)) / 2, 0)
    chrome_top = max(screen_result.get("outerHeight", 945) - screen_result.get("innerHeight", 865) - chrome_left, 70)
    screen_x = int(screen_result.get("x", 0) + chrome_left + center_x)
    screen_y = int(screen_result.get("y", 0) + chrome_top + center_y)
    
    print(f"  Page coords: ({center_x}, {center_y})")
    print(f"  Screen coords: ({screen_x}, {screen_y})")
    
    # Click
    click_result = click_screen_point(screen_x, screen_y, pause=2.0)
    print(f"  Click: {json.dumps(click_result, ensure_ascii=False)}")
    
    time.sleep(1.5)
    
    # Get chat content
    content = get_chat_content()
    print(f"  Content: {json.dumps(content, ensure_ascii=False)}")
    
    content_result = content.get("result", {})
    page_text = content_result.get("pageText", "")
    
    # Extract just the chat messages for this conversation
    # Look for HR messages (not [送达], [已读] or our messages)
    print(f"\n  === PAGE TEXT (relevant part) ===")
    lines = page_text.split('\n')
    for line in lines[-30:]:
        print(f"  {line}")
    
    # Check if this has a new HR message we need to reply to
    chat_header = content_result.get("header", "")
    has_input = content_result.get("hasInput", False)
    
    print(f"\n  Header: {chat_header}")
    print(f"  Has input: {has_input}")
    
    # If we found a conversation with input, analyze if HR is asking us something
    if has_input:
        # Remove our messages and system messages
        is_hr_question = False
        hr_message = ""
        
        if '有兴趣聊聊吗' in page_text or '方便发一份你的简历' in page_text:
            is_hr_question = True
            # Find which HR message to process
            if '方便发一份你的简历' in page_text:
                hr_message = "request_resume"
            elif '有兴趣聊聊吗' in page_text:
                hr_message = "question_interest"
        
        print(f"  HR question: {is_hr_question}")
        print(f"  HR message type: {hr_message}")
        
        if is_hr_question:
            print(f"\n  *** FOUND HR MESSAGE TO PROCESS! ***")
            break
        else:
            print(f"  No HR message to process in this conversation")

print("\n=== DONE ===")
