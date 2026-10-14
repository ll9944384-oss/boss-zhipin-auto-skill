#!/usr/bin/env python3
"""Get remaining conversations."""
import json
import sys
sys.path.insert(0, '/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts')
from safari_boss_runner import safari_js

js = """
(function() {
  var items = document.querySelectorAll('.friend-content-warp');
  var convos = Array.from(items).slice(30).map(function(el, idx) {
    var time = (el.querySelector('.time') || {}).innerText || '';
    var nameBox = (el.querySelector('.name-box') || {}).innerText || '';
    var nameText = (el.querySelector('.name-text') || {}).innerText || '';
    var lastMsg = (el.querySelector('.last-msg-text') || {}).innerText || '';
    return {
      idx: 30 + idx,
      time: time.trim(),
      nameBox: nameBox.trim(),
      nameText: nameText.trim(),
      lastMsg: lastMsg.trim()
    };
  });
  return JSON.stringify({convos: convos, count: convos.length, total: items.length});
})();
"""

raw = safari_js(js)
print(raw)
