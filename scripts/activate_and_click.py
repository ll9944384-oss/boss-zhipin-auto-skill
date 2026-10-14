#!/usr/bin/env python3
"""Activate Safari first, then click on conversation."""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safari_boss_runner import json_js, click_screen_point

# Step 1: Activate Safari and bring it to front
print("=== ACTIVATING SAFARI ===")
subprocess.run(["osascript", "-e", '''
    tell application "Safari"
        activate
        set index of front window to 1
    end tell
'''], timeout=10)
time.sleep(1)

# Also bring the browser window to front
subprocess.run(["osascript", "-e", '''
    tell application "System Events"
        tell process "Safari"
            set frontmost to true
        end tell
    end tell
'''], timeout=10)
time.sleep(0.5)

# Step 2: Get the current conversations list
probe_js = r"""
var allLis = Array.from(document.querySelectorAll('.chat-user li'));
var conversations = [];
for (var i = 0; i < allLis.length; i++) {
    var el = allLis[i];
    var r = el.getBoundingClientRect();
    var text = (el.innerText || '').trim();
    if (r.width > 50 && r.height > 20 && r.top > 100 && 
        text.length > 10 && !/^(全部|未读|新招呼|仅沟通|更多)$/.test(text)) {
        conversations.push({
            text: text.slice(0, 200),
            left: Math.round(r.left),
            top: Math.round(r.top),
            width: Math.round(r.width),
            height: Math.round(r.height)
        });
    }
}
return conversations;
"""
probe = json_js(probe_js)
convs = probe.get("result", [])
print(f"\n=== CONVERSATIONS ({len(convs)} found) ===")
for idx, c in enumerate(convs[:5]):
    print(f"  [{idx}] {c['text'][:100]}")

if not convs:
    print("No conversations found!")
    sys.exit(0)

# Step 3: Click the first conversation (most recent)
first = convs[0]
cx = first['left'] + first['width'] // 2
cy = first['top'] + first['height'] // 2

# Get screen info
screen_info = json_js("return {x: window.screenX, y: window.screenY, outerWidth: window.outerWidth, outerHeight: window.outerHeight, innerWidth: window.innerWidth, innerHeight: window.innerHeight};")
screen = screen_info.get("result", {})

chrome_left = max((screen.get("outerWidth", 1430) - screen.get("innerWidth", 1430)) / 2, 0)
chrome_top = max(screen.get("outerHeight", 751) - screen.get("innerHeight", 671) - chrome_left, 70)
sx = int(screen.get("x", 0) + chrome_left + cx)
sy = int(screen.get("y", 0) + chrome_top + cy)

print(f"\nClicking at screen coords: ({sx}, {sy})")
print(f"Target: {first['text'][:80]}")

# Click multiple times
for attempt in range(3):
    click_result = click_screen_point(sx, sy, pause=1.0)
    print(f"Attempt {attempt+1}: {json.dumps(click_result, ensure_ascii=False)}")
    time.sleep(1.5)

# Wait for the chat to load
print("\nWaiting 5s for conversation to load...")
time.sleep(5)

# Step 4: Check the chat state
check_js = r"""
var result = {};

// Check for chat input
var inputs = document.querySelectorAll('div[contenteditable="true"], textarea');
var visInputs = [];
for (var i = 0; i < inputs.length; i++) {
    var r = inputs[i].getBoundingClientRect();
    if (r.width > 20 && r.height > 10) {
        visInputs.push(true);
    }
}
result.hasInput = visInputs.length > 0;
result.inputCount = visInputs.length;

// Check conversation panel
var conv = document.querySelector('.chat-conversation');
var noData = document.querySelector('.chat-no-data');
if (conv) {
    result.convClass = conv.className;
    result.convChildCount = conv.children.length;
    result.convText = (conv.innerText || '').trim().slice(0, 500);
    result.convDisplay = getComputedStyle(conv).display;
}
if (noData) {
    result.noDataDisplay = getComputedStyle(noData).display;
    result.noDataText = (noData.innerText || '').trim().slice(0, 200);
}

// Check URL
result.url = location.href;

return result;
"""
check = json_js(check_js)
print("\n=== CHAT STATE ===")
print(json.dumps(check, ensure_ascii=False, indent=2))

check_result = check.get("result", {})
if check_result.get("hasInput"):
    print("\n✅ 聊天已成功打开！")
    print(f"对话内容: {check_result.get('convText', '')}")
else:
    print("\n❌ 聊天未能打开")
    if check_result.get("noDataText"):
        print(f"空状态显示: {check_result.get('noDataText')}")
    
    # Try one more thing - click directly with AppleScript
    print("\n尝试AppleScript点击...")
    as_script = f'''
    tell application "Safari"
        activate
        set theBounds to bounds of front window
    end tell
    
    tell application "System Events"
        tell process "Safari"
            set frontmost to true
            delay 0.3
            click at {{{sx}, {sy}}}
        end tell
    end tell
    '''
    try:
        as_result = subprocess.run(["osascript", "-e", as_script], 
                                   text=True, capture_output=True, timeout=15)
        print(f"AS click output: {as_result.stdout.strip()}")
        if as_result.stderr:
            print(f"AS click stderr: {as_result.stderr.strip()}")
    except Exception as e:
        print(f"AS click error: {e}")
    
    time.sleep(4)
    
    check2 = json_js(check_js)
    print("\n=== CHAT STATE AFTER AS CLICK ===")
    print(json.dumps(check2, ensure_ascii=False, indent=2))
