#!/usr/bin/env python3
"""READ-ONLY scan of BOSS chat page: account, conversation list, unread flags, open chat state.

Sends nothing. Used by cron to decide whether an HR-initiated message exists.
"""
import json
import sys
import time

sys.path.insert(0, "/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts")
from safari_boss_runner import json_js, run_bridge, chat_state_value  # noqa: E402


SCAN_JS = r"""
function vis(n){var r=n.getBoundingClientRect();var s=getComputedStyle(n);
    return r.width>5&&r.height>5&&s.visibility!=='hidden'&&s.display!=='none';}
  var out = {url: location.href, pathname: location.pathname, title: document.title};

  // account
  var nav = document.querySelector('.user-nav, .nav-figure, [class*="user-nav"]');
  out.account = nav ? (nav.innerText || '').trim().slice(0, 120) : '';
  var navImgAlt = '';
  var imgs = document.querySelectorAll('.user-nav img, [class*="user-nav"] img');
  if (imgs.length) navImgAlt = imgs[0].getAttribute('alt') || imgs[0].src || '';
  out.accountImg = String(navImgAlt).slice(0, 200);

  // conversation list
  var lis = Array.from(document.querySelectorAll('.user-list-content li, .chat-user-list li, li'));
  var convos = [];
  var seen = {};
  lis.forEach(function (li) {
    var r = li.getBoundingClientRect();
    var t = (li.innerText || '').trim();
    if (r.width < 120 || r.height < 25 || !t) return;
    if (r.left > 500) return;                 // left column only
    if (seen[t]) return;
    seen[t] = 1;
    var badge = li.querySelector('.badge, [class*="badge"], [class*="unread"], sup');
    var red = 0;
    var redNodes = li.querySelectorAll('*');
    for (var i = 0; i < redNodes.length; i++) {
      var c = getComputedStyle(redNodes[i]).backgroundColor || '';
      var m = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (m && +m[1] > 190 && +m[2] < 110 && +m[3] < 110 &&
          redNodes[i].getBoundingClientRect().width > 3 &&
          redNodes[i].getBoundingClientRect().width < 40 &&
          (redNodes[i].innerText || '').trim().length < 5) {
        red = 1;
      }
    }
    var nameEl = li.querySelector('.friend-content .title, .name, [class*="name"]');
    convos.push({
      top: Math.round(r.top),
      name: nameEl ? (nameEl.innerText || '').trim().slice(0, 40) : '',
      text: t.slice(0, 260),
      badge: badge ? (badge.innerText || '').trim() : '',
      redDot: red
    });
  });
  convos.sort(function (a, b) { return a.top - b.top; });
  out.convos = convos.slice(0, 20);

  // open conversation pane
  var pane = document.querySelector('.chat-conversation');
  out.openConv = false;
  if (pane) {
    var paneText = (pane.innerText || '').trim();
    if (paneText.length > 20) {
      out.openConv = true;
      var hdr = pane.querySelector('.top-info-content, .chat-header, [class*="header"], .name-box');
      out.openHeader = hdr ? (hdr.innerText || '').trim().slice(0, 120) : '';
      out.paneText = paneText.slice(-2000);
    }
  }
  return out;
})()
"""


def main():
    print("=== BOSS CHAT READ-ONLY SCAN ===")
    print("time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
    time.sleep(4.0)
    state = chat_state_value()
    print("\n--- chat_state ---")
    print(json.dumps(state, ensure_ascii=False))
    scan = json_js(SCAN_JS, tab_hint="zhipin.com")
    print("\n--- scan ---")
    print(json.dumps(scan, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
