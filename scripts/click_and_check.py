#!/usr/bin/env python3
"""Better click and check chat using screen coords from DOM."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safari_boss_runner import json_js, click_screen_point

# Step 1: Get the current screen/browser info and clickable items
probe_js = r"""
var allLis = Array.from(document.querySelectorAll('.chat-user li'));
var conversations = [];
for (var i = 0; i < allLis.length; i++) {
    var el = allLis[i];
    var r = el.getBoundingClientRect();
    var text = (el.innerText || '').trim();
    // Skip filter tabs at top - look for items with names/messages
    if (r.width > 50 && r.height > 20 && r.top > 100 && 
        text.length > 10 && !/^(全部|未读|新招呼|仅沟通|更多)$/.test(text)) {
        conversations.push({
            idx: i,
            text: text.slice(0, 200),
            left: Math.round(r.left),
            top: Math.round(r.top),
            width: Math.round(r.width),
            height: Math.round(r.height)
        });
    }
}
return {conversations: conversations.slice(0, 5), total: conversations.length};
"""
probe = json_js(probe_js)
print("=== CONVERSATIONS ===")
print(json.dumps(probe, ensure_ascii=False, indent=2))

convs = probe.get("result", {}).get("conversations", [])
if not convs:
    print("No conversations found")
    sys.exit(0)

# Step 2: Click on the first conversation (most recent = <HR>先生)
first = convs[0]
cx = first['left'] + first['width'] // 2
cy = first['top'] + first['height'] // 2
print(f"\nClicking conversation 0 at page coords ({cx}, {cy})")
print(f"Text: {first['text'][:80]}")

# Get screen info for coordinate conversion
screen_info = json_js("return {x: window.screenX, y: window.screenY, outerWidth: window.outerWidth, outerHeight: window.outerHeight, innerWidth: window.innerWidth, innerHeight: window.innerHeight};")
screen = screen_info.get("result", {})
print(f"Screen info: {json.dumps(screen, ensure_ascii=False)}")

# Convert to screen coords
chrome_left = max((screen.get("outerWidth", 1430) - screen.get("innerWidth", 1430)) / 2, 0)
chrome_top = max(screen.get("outerHeight", 751) - screen.get("innerHeight", 671) - chrome_left, 70)
sx = int(screen.get("x", 0) + chrome_left + cx)
sy = int(screen.get("y", 0) + chrome_top + cy)
print(f"Screen coords: ({sx}, {sy})")

# Click
click_result = click_screen_point(sx, sy, pause=0.5)
print(f"Click: {json.dumps(click_result, ensure_ascii=False)}")

# Wait for chat to load
print("Waiting 4s for chat to load...")
time.sleep(4)

# Step 3: Now check what's in the right panel
check_js = r"""
var result = {};

// Check for chat input (contenteditable div or textarea)
var inputs = document.querySelectorAll('div[contenteditable="true"], textarea');
var visibleInputs = [];
for (var i = 0; i < inputs.length; i++) {
    var r = inputs[i].getBoundingClientRect();
    if (r.width > 20 && r.height > 10) {
        visibleInputs.push({tag: inputs[i].tagName, className: (inputs[i].className || '').slice(0, 60)});
    }
}
result.hasChatInput = visibleInputs.length > 0;
result.inputDetails = visibleInputs;

// Check the right panel specifically - look for chat message containers
var rightPanel = document.querySelector('.chat-content-right, .chat-right, ' +
    '[class*="chat-content-right"], [class*="chat-right"], ' +
    '.content-right, .dialog-content, .conversation-detail, ' +
    '.chat-main, [class*="chat-main"]');
if (rightPanel) {
    result.rightPanelClass = (rightPanel.className || '').slice(0, 80);
    result.rightPanelText = (rightPanel.innerText || '').trim().slice(0, 2000);
    result.rightPanelHTML = rightPanel.innerHTML.slice(0, 500);
} else {
    result.rightPanelClass = 'not_found';
}

// Also check the page URL for any changes
result.url = location.href;
result.currentTitle = document.title;

// Check for a "发送" button in the page
var sendButtons = document.querySelectorAll('button, div, span');
var sendFound = [];
for (var j = 0; j < sendButtons.length; j++) {
    var btn = sendButtons[j];
    var btnText = (btn.innerText || '').trim();
    if (btnText === '发送' && btn.offsetParent !== null) {
        sendFound.push(btnText);
    }
}
result.sendButtons = sendFound;

return result;
"""
check = json_js(check_js)
print("\n=== RIGHT PANEL CHECK ===")
print(json.dumps(check, ensure_ascii=False, indent=2))

# Try clicking again with native approach
print("\n=== Trying JavaScript click on same element ===")
click_js = r"""
var allLis = Array.from(document.querySelectorAll('.chat-user li'));
for (var i = 0; i < allLis.length; i++) {
    var r = allLis[i].getBoundingClientRect();
    if (r.top > 100 && r.width > 50) {
        var text = (allLis[i].innerText || '').trim();
        if (text.length > 10 && !/^(全部|未读|新招呼|仅沟通|更多)$/.test(text)) {
            // Click this one
            allLis[i].click();
            return {clicked: i, text: text.slice(0, 100)};
        }
    }
}
return {clicked: false};
"""
js_click = json_js(click_js)
print(json.dumps(js_click, ensure_ascii=False, indent=2))
time.sleep(3)

# Check again
check2 = json_js(check_js)
print("\n=== RIGHT PANEL CHECK 2 ===")
print(json.dumps(check2, ensure_ascii=False, indent=2))
