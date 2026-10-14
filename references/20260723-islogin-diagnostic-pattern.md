# `_PAGE.isLogin` Diagnostics (2026-07-23)

## The Diagnostic-First Pattern

Before attempting ANY interaction with the BOSS chat page (clicking on conversations, dispatching events, accessing Vue components), **always check `_PAGE.isLogin` first**.

```python
from scripts.safari_boss_runner import json_js

login_check = json_js("return typeof _PAGE !== 'undefined' ? _PAGE.isLogin : 'undefined';")
```

If `isLogin` is `false`:
- Vue's `handleClickItem()` will NOT open conversations
- MouseEvent dispatch will NOT open conversations
- pyautogui native clicks will NOT open conversations
- The right panel will stay stuck on `.chat-no-data` with placeholder text
- All conversation interaction attempts are futile

But crucially, **reading conversation data from the DOM still works** — the page renders the full conversation list text even when the session is expired.

## Why This Happens

BOSS直聘 is a Vue SPA. When a session token expires mid-use:
1. Safari still shows the page (no redirect to login)
2. The conversation list still renders in the DOM
3. But `_PAGE.isLogin` flips to `false` internally
4. Vue component methods that would trigger WebSocket connections to load chat history are silently suppressed
5. No error is thrown — the interaction simply doesn't work

## Recommended Cron Job Pattern

```python
from scripts.safari_boss_runner import run_bridge, safari_js
import json, time

# Step 0: Navigate to chat page
run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
time.sleep(4)

# Step 1: Diagnose login status FIRST
raw = safari_js("""
(function() {
  try {
    var isLogin = typeof _PAGE !== 'undefined' ? _PAGE.isLogin : null;
    var bodyText = (document.body.innerText || '').replace(/\\s+/g, ' ').trim();
    var hasNoData = bodyText.includes('30天内暂无联系人');
    return JSON.stringify({
      isLogin: isLogin,
      hasNoData: hasNoData,
      bodyPreview: bodyText.slice(0, 2000)
    });
  } catch(e) {
    return JSON.stringify({error: String(e)});
  }
})()
""")
parsed = json.loads(raw)

if parsed.get("isLogin") is False:
    print("[SILENT] — BOSS session expired, cannot interact")
    # Still report conversations visible in DOM
    # ... but do NOT attempt to open or reply
    sys.exit(0)
```

## What DID Work in This Session

| Action | Worked? | Notes |
|--------|---------|-------|
| Navigate to chat page | ✅ | `run_bridge("navigate", URL)` |
| Read conversation list from DOM | ✅ | `safari_js` returning `document.body.innerText` |
| `send_text_value()` in chat context | ✅ | Successfully sent "测试" and clicked send |
| `try_click_send()` | ✅ | pyautogui clicked send button successfully |
| Open conversation (any method) | ❌ | Possibly due to expired session (`isLogin` was not checked) |
| JS `.click()` on LI item | ❌ | Vue SPA barrier |
| MouseEvent dispatch | ❌ | Possibly also blocked by expired session |
| Vue `handleClickItem()` | ❌ | Would also fail if `isLogin=false` |

## Root Cause vs Symptom

The `.chat-no-data` text "与您进行过沟通的 Boss 都会在左侧列表中显示" can mean TWO different things:

1. **Legitimate**: No conversation is selected yet (user hasn't clicked anything) — SOLVABLE by opening one
2. **Session expired**: `_PAGE.isLogin === false` — UNSOLVABLE by any interaction method

The diagnostic-first pattern distinguishes these two cases.

## See Also

- `references/20260713-session-debugging.md` — original session debugging
- SKILL.md "阶段四" section — conversation opening workflow
