#!/usr/bin/env python3
"""Extract chat messages from BOSS直聘 chat page using Safari runner."""
import sys
import json
sys.path.insert(0, '/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts')
from safari_boss_runner import safari_js, json_js

# Read our JS file
with open('/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/extract_messages.js') as f:
    js_code = f.read()

result = json_js(js_code)
print(json.dumps(result, ensure_ascii=False, indent=2))
