#!/usr/bin/env python3
"""Click the friend-content-warp element inside each conversation."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safari_boss_runner import json_js, click_screen_point

# First, find the actual clickable friend-content-warp elements
find_js = r"""
var items = document.querySelectorAll('.friend-content-warp, .friend-content, .text');
var result = [];
for (var i = 0; i < items.length; i++) {
    var el = items[i];
    var r = el.getBoundingClientRect();
    var parentText = (el.parentElement ? el.parentElement.innerText || '' : '');
    var text = (el.innerText || '').trim();
    if (r.width > 50 && r.height > 20 && r.top > 100 && text.length > 5) {
        result.push({
            idx: i,
            className: (el.className || '').slice(0, 40),
            tag: el.tagName,
            text: parentText.slice(0, 120),
            left: Math.round(r.left),
            top: Math.round(r.top),
            width: Math.round(r.width),
            height: Math.round(r.height)
        });
    }
}
return result;
"""
items_result = json_js(find_js)
print("=== CLICKABLE ITEMS ===")
items = items_result.get("result", [])
for idx, item in enumerate(items[:8]):
    print(f"  [{idx}] {item['className']:25s} ({item['left']:3d},{item['top']:3d}) w={item['width']:3d} h={item['height']:2d} | {item['text'][:80]}")

if not items:
    print("No clickable items found!")
    sys.exit(0)

# Get screen info
screen_info = json_js("return {x: window.screenX, y: window.screenY, outerWidth: window.outerWidth, outerHeight: window.outerHeight, innerWidth: window.innerWidth, innerHeight: window.innerHeight};")
screen = screen_info.get("result", {})

chrome_left = max((screen.get("outerWidth", 1430) - screen.get("innerWidth", 1430)) / 2, 0)
chrome_top = max(screen.get("outerHeight", 751) - screen.get("innerHeight", 671) - chrome_left, 70)

# Click the first friend-content-warp (most recent conversation = <HR>先生 at 13:12)
# Looking at the data: first item (idx 0) should be <HR>先生
target = items[0]
cx = target['left'] + target['width'] // 2
cy = target['top'] + target['height'] // 2
sx = int(screen.get("x", 0) + chrome_left + cx)
sy = int(screen.get("y", 0) + chrome_top + cy)

print(f"\n=== CLICKING: {target['text'][:80]} ===")
print(f"Page coords: ({cx}, {cy}) -> Screen coords: ({sx}, {sy})")

# Click
click_result = click_screen_point(sx, sy, pause=1.5)
print(f"Click: {json.dumps(click_result, ensure_ascii=False)}")
time.sleep(3)

# Check if conversation opened
check_js = r"""
var result = {};
var conv = document.querySelector('.chat-conversation');
var noData = document.querySelector('.chat-no-data');
result.hasConversation = conv ? (conv.innerText || '').length > 50 : false;
result.conversationText = conv ? (conv.innerText || '').trim().slice(0, 2000) : '';
result.hasNoData = noData ? (noData.offsetParent !== null) : false;
result.noDataText = noData ? (noData.innerText || '').trim().slice(0, 200) : '';

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

return result;
"""
check = json_js(check_js)
print(f"\n=== CHAT OPENED? ===")
print(json.dumps(check, ensure_ascii=False, indent=2))

check_result = check.get("result", {})
if check_result.get("hasConversation"):
    print("\n聊天已打开！内容如下：")
    print(check_result.get("conversationText", ""))
elif check_result.get("hasNoData"):
    print("\n聊天未打开，显示空状态：" + check_result.get("noDataText", ""))
    print("尝试第二种点击方法...")
    
    # Try a mouse event directly
    click_js_2 = r"""
    var items = document.querySelectorAll('.friend-content-warp, .friend-content');
    var convItem = null;
    for (var i = 0; i < items.length; i++) {
        var r = items[i].getBoundingClientRect();
        if (r.top > 100 && r.top < 250 && r.width > 50) {
            convItem = items[i];
            break;
        }
    }
    if (!convItem) return {clicked: false, reason: 'no_item_found'};
    
    // Try multiple event types
    convItem.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window, button: 0}));
    convItem.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window, button: 0}));
    convItem.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window, button: 0}));
    
    // Also try the LI parent
    var li = convItem.closest('li');
    if (li) {
        li.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window, button: 0}));
        li.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window, button: 0}));
        li.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window, button: 0}));
    }
    
    return {clicked: true, text: (convItem.innerText || '').trim().slice(0, 100)};
    """
    js_click = json_js(click_js_2)
    print(f"JS Click: {json.dumps(js_click, ensure_ascii=False, indent=2)}")
    time.sleep(3)
    
    check2 = json_js(check_js)
    print(f"\n=== CHECK AFTER JS CLICK ===")
    print(json.dumps(check2, ensure_ascii=False, indent=2))
    
    check2_result = check2.get("result", {})
    if check2_result.get("hasConversation"):
        print("\n聊天已打开！内容如下：")
        print(check2_result.get("conversationText", ""))
