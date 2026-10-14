#!/usr/bin/env python3
"""Check if there's an unread filter tab and extract only HR's unread messages."""
import json
import sys
sys.path.insert(0, '/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts')
from safari_boss_runner import safari_js

# Check for unread indicators and tab structure
js = """
(function() {
  // Check all tabs
  var tabs = Array.from(document.querySelectorAll('.tab-item, .filter-item, [class*="tab"], [class*="filter"]'));
  var tabInfo = tabs.map(function(t) {
    return {
      text: (t.innerText || '').trim().slice(0, 20),
      className: (t.className || '').slice(0, 100),
      selected: t.classList.contains('active') || t.classList.contains('on') || t.classList.contains('selected')
    };
  });
  
  // Check for unread badges/conversations
  var items = document.querySelectorAll('[class*="chat-list"] [class*="item"], [class*="chat"] [class*="item"], ' +
    '[class*="conversation"] [class*="item"], .geek-list-item, .im-list-item');
  
  var convos = Array.from(items).slice(0, 30).map(function(el, idx) {
    var text = (el.innerText || '').trim().slice(0, 300);
    var hasBadge = !!el.querySelector('.unread, .badge, [class*="unread"], [class*="badge"], [class*="red-dot"]');
    var cls = (el.className || '').slice(0, 80);
    return {idx: idx, text: text, hasBadge: hasBadge, cls: cls};
  });
  
  return JSON.stringify({
    tabs: tabInfo,
    convos: convos,
    bodyLen: (document.body.innerText || '').length
  });
})();
"""

raw = safari_js(js)
print(raw)
