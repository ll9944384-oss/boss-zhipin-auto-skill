#!/usr/bin/env python3
"""Check HR messages on BOSS直聘 chat - simple version using runner directly."""
import json
import os
import sys
import subprocess
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(SCRIPT_DIR, "safari_boss_runner.py")
BRIDGE = os.path.join(SCRIPT_DIR, "safari_boss_bridge.applescript")

def run_bridge(mode, *args, timeout=20):
    proc = subprocess.run(
        ["osascript", BRIDGE, mode, *args],
        text=True, capture_output=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()

# Navigate to chat
print("Navigating to chat...")
run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
time.sleep(3)

# Get all visible text
js_show = """
tell application "Safari"
    set docText to do JavaScript "document.body.innerText" in document 1
    return docText
end tell
"""
proc = subprocess.run(["osascript", "-e", js_show], text=True, capture_output=True, timeout=20)
print("=== PAGE TEXT (first 8000 chars) ===")
print(proc.stdout.strip()[:8000])

# Try to get chat list items and click the first one with unread
js_get_items = """
tell application "Safari"
    set result to do JavaScript "
        (function() {
            // Find chat list items
            const items = Array.from(document.querySelectorAll(
                '.chat-list li, .friend-list li, .conversation-list li, ' +
                '[class*=\\\"chat\\\"] [class*=\\\"item\\\"], [class*=\\\"conversation\\\"] [class*=\\\"item\\\"], ' +
                '.geek-chat-list li, .chat-list-wrap li, ' +
                'ul li, div[class*=\\\"chat-item\\\"], div[class*=\\\"session-item\\\"]'
            )).filter(n => {
                const r = n.getBoundingClientRect();
                const text = (n.innerText || '').trim();
                return r.width > 100 && r.height > 20 && text.length > 10;
            });
            return JSON.stringify(items.map((n, i) => ({
                index: i,
                text: (n.innerText || '').trim().slice(0, 150),
                isUnread: (n.innerText || '').includes('新') || !!n.querySelector('.badge, [class*=\\\"unread\\\"]')
            })));
        })()
    " in document 1
    return result
end tell
"""
proc2 = subprocess.run(["osascript", "-e", js_get_items], text=True, capture_output=True, timeout=20)
print("\n=== CHAT LIST ITEMS ===")
print(proc2.stdout.strip())

# Try to click the first item
js_click_first = """
tell application "Safari"
    do JavaScript "
        (function() {
            const items = Array.from(document.querySelectorAll(
                '.chat-list li, .friend-list li, .conversation-list li, ' +
                '[class*=\\\"chat\\\"] [class*=\\\"item\\\"], [class*=\\\"conversation\\\"] [class*=\\\"item\\\"], ' +
                '.geek-chat-list li, .chat-list-wrap li, ' +
                'ul li, div[class*=\\\"chat-item\\\"], div[class*=\\\"session-item\\\"]'
            )).filter(n => {
                const r = n.getBoundingClientRect();
                const text = (n.innerText || '').trim();
                return r.width > 100 && r.height > 20 && text.length > 10;
            });
            if (items.length > 0) {
                items[0].click();
                return 'clicked item 0: ' + (items[0].innerText || '').trim().slice(0, 100);
            }
            return 'no items found';
        })()
    " in document 1
end tell
"""
proc3 = subprocess.run(["osascript", "-e", js_click_first], text=True, capture_output=True, timeout=20)
print("\n=== CLICK RESULT ===")
print(proc3.stdout.strip())
time.sleep(2)

# Now get the chat content of the opened conversation
js_chat_content = """
tell application "Safari"
    set result to do JavaScript "
        (function() {
            const body = document.body.innerText || '';
            // Try to get the chat message area specifically
            const chatBody = document.querySelector(
                '.chat-body, .chat-msg-list, [class*=\\\"chat-body\\\"], [class*=\\\"msg-list\\\"], ' +
                '[class*=\\\"message-list\\\"], .msg-scroll, ' +
                '.chat-content-right, [class*=\\\"chat-content-right\\\"]'
            );
            const chatText = chatBody ? chatBody.innerText : '';
            const hasInput = !!document.querySelector('div[contenteditable=\\\"true\\\"], textarea');
            return JSON.stringify({
                pageUrl: location.href,
                header: (document.querySelector('.chat-header, [class*=\\\"chat-header\\\"]') || {}).innerText || '',
                chatText: chatText.slice(0, 4000),
                fullText: body.slice(0, 6000),
                hasInput: hasInput
            });
        })()
    " in document 1
    return result
end tell
"""
proc4 = subprocess.run(["osascript", "-e", js_chat_content], text=True, capture_output=True, timeout=20)
print("\n=== CHAT CONTENT ===")
print(proc4.stdout.strip())
