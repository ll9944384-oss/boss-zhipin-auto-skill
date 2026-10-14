#!/usr/bin/env python3
"""Check BOSS chat page for new HR messages - v2."""
import sys, json, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safari_boss_runner import json_js, run_bridge

# Step 1: Ensure we're on chat page
state = json_js("return {url: location.href, pathname: location.pathname, title: document.title};", tab_hint="zhipin.com")
print("CHAT STATE:", json.dumps(state, ensure_ascii=False))

pathname = state.get("result", {}).get("pathname", "")
if "/web/geek/chat" not in pathname:
    print("Not on chat page, navigating...")
    run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
    time.sleep(3)
    state = json_js("return {url: location.href, pathname: location.pathname, title: document.title};", tab_hint="zhipin.com")
    print("AFTER NAV:", json.dumps(state, ensure_ascii=False))

# Step 2: Get all visible text on the page
js_code = """
(function() {
  var text = document.body.innerText || '';
  var textLen = text.length;
  var tail = text.slice(-10000);
  
  // Get all elements that look like clickable chat items (HR contacts)
  var chatItems = [];
  var candidates = document.querySelectorAll('li, div[class*="item"], div[class*="card"], a[href*="/web/geek/chat"]');
  for (var i = 0; i < candidates.length; i++) {
    var el = candidates[i];
    var r = el.getBoundingClientRect();
    if (r.width > 100 && r.height > 30) {
      var txt = (el.innerText || '').trim();
      if (txt && txt.length > 5 && txt.length < 500) {
        var html = el.innerHTML || '';
        var hasUnread = html.indexOf('red') > -1 || html.indexOf('unread') > -1 || html.indexOf('badge') > -1 || html.indexOf('dot') > -1;
        chatItems.push({
          text: txt.slice(0, 300),
          hasUnread: hasUnread,
          rect: {w: Math.round(r.width), h: Math.round(r.height)}
        });
        if (chatItems.length >= 10) break;
      }
    }
  }
  
  return {
    url: location.href,
    title: document.title,
    textTail: tail,
    textLen: textLen,
    chatItemCount: chatItems.length,
    chatItems: chatItems
  };
})()
"""
result = json_js(js_code, tab_hint="zhipin.com")
print("EXTRACTED:", json.dumps(result, ensure_ascii=False, indent=2))
