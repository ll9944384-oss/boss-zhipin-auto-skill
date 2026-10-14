#!/usr/bin/env python3
"""Extract BOSS chat list items."""
import json
import sys
sys.path.insert(0, '/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts')
from safari_boss_runner import safari_js

# Simple JS to get chat list and page text
js = """
(function() {
  var body = document.body.innerText || '';
  return JSON.stringify({text: body.slice(0, 8000), len: body.length});
})();
"""

raw = safari_js(js)
print(raw)
