# 2026-07-23 Conversation List DOM Structure & Dynamic Re-Rendering

**Context**: Cron job checking `/web/geek/chat` for new HR messages. Reading the conversation list from the left sidebar via Safari JS bridge.

## DOM Structure: `.list-warp li`

The conversation list lives inside a scrollable `div.list-warp` (CSS class `list-warp` inside `div.chat-user.v2`). All items are rendered as `<li>` elements.

### Index Layout

| Index | Type | Content | Example |
|:-----:|------|---------|---------|
| 0 | Filter tab | 全部 | "selected" class when active |
| 1 | Filter tab | 未读 | |
| 2 | Filter tab | 新招呼 | |
| 3 | Filter tab | 仅沟通 | |
| 4 | Filter tab | 更多 (dropdown trigger) | |
| 5 | Dropdown option | 有交换 | Only visible when "更多" is clicked |
| 6 | Dropdown option | 有面试 | |
| 7 | Dropdown option | 不感兴趣 | |
| **8+** | **Conversation item** | HR/company name + last msg | See below |

**Selector**: `document.querySelectorAll('.list-warp li')` — returns all filter tabs + conversation items.

### Conversation Item Structure

Each conversation `<li>` contains:
```
<li>
  <div class="friend-content-warp">
    <div class="friend-content" d-c="UNIQUE_ID">    ← clickable element
      <div class="text">
        <span class="name-text">HR_NAME</span>
        <span class="last-msg-text">LAST_MESSAGE_PREVIEW</span>
      </div>
    </div>
  </div>
</li>
```

### Identifying Message Origin (HR vs Sent)

In the `.innerText` of each conversation item, the format is:

```
TIME\n
HR_NAME COMPANY_TITLE\n
STATUS_TAG (optional)\n
LAST_MESSAGE_TEXT
```

**Key rule**: Messages SENT BY US (the user) are tagged with `[已读]` or `[送达]`:
- `[已读]` = HR has read our message
- `[送达]` = Our message delivered but not yet read

**HR messages have NO tag** — just the name + company + message text.

**Example — sent message (tag present):**
```
昨天
<HR>女士油样文化人事主管
[送达]
这是我的作品集，百度网盘链接：...
```

**Example — HR message (no tag):**
```
昨天
<HR_NAME>COMPANY_18总经理
上线的短剧叫什么，在哪个平台可以搜到，你剪辑了哪几集
```

### Finding New HR Messages (Algorithm)

```javascript
// Get all conversation items (skip filters at indices 0-7)
var items = document.querySelectorAll('.list-warp li');
var convs = [];
for (var i = 8; i < items.length; i++) {
  var text = (items[i].innerText || '').trim();
  // HR messages have NO [已读] or [送达] tag
  var isFromHr = text.indexOf('[已读]') === -1 && text.indexOf('[送达]') === -1;
  convs.push({index: i, text: text.slice(0, 200), isFromHr: isFromHr});
}
// convs is sorted newest-first. First isFromHr === true item is the top HR message.
```

Python (via `json_js`):
```python
js = '''
  var lis = document.querySelectorAll('.list-warp li');
  var items = [];
  for (var i = 8; i < lis.length && i < 40; i++) {
    var text = (lis[i].innerText || '').trim();
    if (text) {
      items.push({
        index: i,
        preview: text.slice(0, 150),
        lastMsgFromHR: text.indexOf('[已读]') === -1 && text.indexOf('[送达]') === -1,
        isFilter: false
      });
    }
  }
  return items;
'''
result = json_js(js)
```

## ⚠️ Dynamic Re-Rendering Behavior

The conversation list **dynamically re-renders** between page visits. Conversations observed in one session's `document.body.innerText` may be **absent in the `.list-warp` DOM** on the next check. This is due to Vue's virtual scrolling / lazy rendering.

**Observed example** (July 23, 2026):
- Early session (03:18): `has-header` text showed conversations in order: <HR>女士 → <HR>女士 → <HR>女士 → <HR>女士 → <HR>女士 → ... → <HR>女士
- Later session (same day): `.list-warp li` showed conversations starting from <HR>女士 (index 8). The <HR>女士/<HR>女士/<HR>女士/<HR>女士/<HR>女士 conversations were **gone** — not present anywhere in the DOM.

**Causes** (likely):
1. Vue virtual scroller only renders visible items + buffer
2. Page re-rendered between visits (navigation or re-mount)
3. Conversations may be loaded from cache/WebSocket and the cache was refreshed

**Implications for cron job logic**:
- **Do NOT assume stable conversation ordering**. The top item today may not exist tomorrow.
- The "newest HR message" should be determined by scanning what's currently in `.list-warp`, not by caching a position.
- Always start fresh: scroll `.list-warp` to top, read first N items, find the first HR-originated message.
- If a conversation was previously identified but is now absent, assume it was handled or the page re-rendered.

## Practical Workflow for HR Message Check

1. Verify page is loaded and user is logged in
2. Scroll `.list-warp` to top: `document.querySelector('.list-warp').scrollTop = 0`
3. Read items: `document.querySelectorAll('.list-warp li')` → slice from index 8+
4. Find first item where `innerText` does NOT contain `[已读]` or `[送达]`
5. This is the topmost HR-originated message
6. Apply reply rules (skip excluded, reply to relevant)
7. **Cannot click to open conversation programmatically** (macOS Sequoia blocks synthetic clicks on SPA elements). Report the message + decision; do not attempt pyautogui/JS click to open.

## Conversation Item Clicking (Blocked)

Despite multiple approaches, **no programmatic method can reliably open a conversation** from the chat list sidebar:
- `pyautogui.click()` → macOS Sequoia blocks synthetic OS-level events on Safari web content
- JS `element.click()` → Vue SPA requires `event.isTrusted === true`, synthetic events are rejected
- AppleScript `click at` → Same macOS Sequoia block
- `dispatchEvent(new MouseEvent('click', ...))` → `isTrusted: false`

**Workarounds attempted**:
- Vue `__vue__.handleClickItem(itemObject)` → requires Vue component access which may fail with `_PAGE.isLogin === false`
- Finding `[d-c]` attribute elements → same `isTrusted` barrier

**Fallback**: When reply is needed but conversation cannot be opened, note it in the report and require user manual action.
