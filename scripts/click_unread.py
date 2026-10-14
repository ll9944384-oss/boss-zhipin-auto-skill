#!/usr/bin/env python3
"""Click the first unread chat item and read messages."""
import sys, json, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safari_boss_runner import json_js, click_screen_point

# Step 1: Find and click the first unread chat item
print("=== FINDING FIRST UNREAD CHAT ===")
find_js = """
(function() {
  // Look for unread indicators in the chat list
  var items = document.querySelectorAll('li, div[class*="item"], div[class*="card"], a[href*="/web/geek/chat"]');
  var candidates = [];
  for (var i = 0; i < items.length; i++) {
    var el = items[i];
    var r = el.getBoundingClientRect();
    if (r.width > 100 && r.height > 30) {
      var txt = (el.innerText || '').trim();
      if (txt.length > 5) {
        var html = el.innerHTML || '';
        var hasUnread = txt.indexOf('\\u672a\\u8bfb') > -1 || html.indexOf('red') > -1 || html.indexOf('unread') > -1;
        if (hasUnread || txt.indexOf('20:10') > -1 || txt.indexOf('\\u53f6\\u6c49\\u7965') > -1) {
          candidates.push({
            text: txt.slice(0, 200),
            hasUnread: hasUnread,
            rect: {left: Math.round(r.left), top: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height)},
            screenX: window.screenX, screenY: window.screenY,
            innerWidth: window.innerWidth, innerHeight: window.innerHeight
          });
        }
      }
    }
  }
  return {count: candidates.length, candidates: candidates.slice(0, 5)};
})()
"""
result = json_js(find_js, tab_hint="zhipin.com")
print(json.dumps(result, ensure_ascii=False, indent=2))
