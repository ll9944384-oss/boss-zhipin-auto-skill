#!/usr/bin/env python3
"""Get chat state and page text from BOSS直聘."""
import json
import sys
sys.path.insert(0, '/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts')
from safari_boss_runner import json_js, chat_state_value

# Check chat state first
state = chat_state_value()
print("=== CHAT STATE ===")
print(json.dumps(state, ensure_ascii=False, indent=2))

# Now get page text
js = """
(function() {
  const text = document.body.innerText || '';
  return {
    url: location.href,
    title: document.title,
    text: text.slice(0, 8000),
    textLength: text.length
  };
})();
"""
page = json_js(js)
print("\\n=== PAGE TEXT ===")
if page.get('ok') and page.get('result'):
    r = page['result']
    print(f"URL: {r.get('url')}")
    print(f"Title: {r.get('title')}")
    print(f"Text length: {r.get('textLength')}")
    print(f"Text:\\n{r.get('text', '')[:8000]}")
else:
    print(json.dumps(page, ensure_ascii=False, indent=2))
