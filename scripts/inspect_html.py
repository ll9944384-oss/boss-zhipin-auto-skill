#!/usr/bin/env python3
"""Inspect page HTML structure for BOSS直聘 chat."""
import json
import sys
sys.path.insert(0, '/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts')
from safari_boss_runner import safari_js

# Get top-level structure
js = """
(function() {
  // Get all top-level elements and their classes
  var allDivs = document.querySelectorAll('div');
  var classes = {};
  allDivs.forEach(function(d) {
    var c = d.className || '';
    if (c && typeof c === 'string') {
      classes[c] = (classes[c] || 0) + 1;
    }
  });
  
  // Get links and their texts
  var links = Array.from(document.querySelectorAll('a')).slice(0, 20).map(function(a) {
    return {href: (a.getAttribute('href') || '').slice(0, 100), text: (a.innerText || '').trim().slice(0, 50), cls: (a.className || '').slice(0, 60)};
  });
  
  // Get spans
  var spans = Array.from(document.querySelectorAll('span')).slice(0, 40).map(function(s) {
    return {text: (s.innerText || '').trim().slice(0, 40), cls: (s.className || '').slice(0, 60)};
  });
  
  return JSON.stringify({
    classCounts: Object.entries(classes).sort(function(a,b){return b[1]-a[1]}).slice(0, 30),
    links: links,
    spans: spans.filter(function(s){return s.text.length > 0}).slice(0, 30),
    html: document.body.innerHTML.slice(0, 5000)
  });
})();
"""

raw = safari_js(js)
print(raw[:8000])
