# 2026-07-13: Cron Chat Monitoring Workflow

## Context

This cron job checks BOSS直聘 chat page for unread HR messages and replies automatically.
The chat page (`/web/geek/chat`) is a Vue SPA that renders both the conversation list and
individual chat content in the same `document.body.innerText`.

## Key Findings

### 1. json_js vs safari_js — Choosing the Right Tool

The runner's `json_js()` function wraps JS in an inner IIFE:
```python
const result = (function() { <your_code> })();
return JSON.stringify({ok: true, result});
```

**Limitation**: If the inner function body has syntax issues (Unicode escapes `\u####`,
template literals with `${}`, complex multi-line strings), Safari's JS engine silently
returns `undefined` → `json_js` returns `{"ok": true}` with NO `result` field.

**Fix**: Use `safari_js()` directly with `JSON.stringify()` at the end for complex queries:
```python
from safari_boss_runner import safari_js
js_code = '''
var text = document.body.innerText || "";
JSON.stringify({ fullText: text, length: text.length });
'''
raw = safari_js(js_code, tab_hint='zhipin.com')
data = json.loads(raw)
```

Keep `json_js` only for trivially simple `return <expr>;` one-liners.

### 2. Identifying Unread HR Messages

The conversation list text structure (from `document.body.innerText`):
```
15:16
王玉博杭州欣上品牌设计招聘者
[已读]          ← status tag: [已读]=read, [送达]=delivered, (none)=unread from HR
好的，谢谢

14:44
<HR_NAME>COMPANY_6猎头顾问
你这个剪辑方向是漫剧或短剧方向的么  ← NO status tag = UNREAD HR message
```

**Rule**: Entries without `[已读]` or `[送达]` as the first line after the contact name are
unread messages from HR. System messages (简历已发送 etc.) also lack these tags, so
filter by checking `lastText` doesn't contain system keywords.

### 3. Reliable Send Pattern

**`click-send` alone is NOT reliable** — it reports `ok: true` but the message may
remain in the input box. The `pyautogui` click may not register on BOSS's React buttons.

**Correct approach**: Always use `send-text` which:
1. Base64-encodes the text
2. Injects it into `contenteditable` via JS (`document.execCommand`)
3. Tries JS `click()` on the send button
4. Falls back to `pyautogui` click on the send button (via `try_click_send`)

```python
from safari_boss_runner import send_text_value
result = send_text_value('回复内容')
# result['sent'] == True if JS method worked
# result['pyautogui_send_click']['ok'] == True if pyautogui fallback worked
```

### 4. Send Verification

After `send-text`, re-read `document.body.innerText` and check the conversation area
for the sent message text followed by a timestamp and "送达" (delivered) status:

```python
raw = safari_js('JSON.stringify(document.body.innerText.slice(-1000));')
# Look for: "<sent text>\\n<timestamp>\\n送达" pattern
```

### 5. Cron Job Pattern

```
1. Navigate to /web/geek/chat (Safari already has it open)
2. Check hasChatInput — already inside a conversation?
3. If inside conversation:
   a. Read bodyText to identify latest unread HR message
   b. Determine reply based on rules (question/ad/interview/portfolio request)
   c. Use send_text_value() to type and send
   d. Verify by re-reading bodyText
4. If on list page (no ChatInput):
   a. Need to click conversation item to open it
   b. [Not yet automated via cron — needs manual or Vue.handleClickItem]
5. Process only 1 unread message per trigger
```

### 6. User Profile (for cron replies)

| Field | Value |
|-------|-------|
| Job Type | 视频剪辑/后期制作 |
| Skills | PR, AE, 达芬奇 (NOT Final Cut Pro) |
| Expected Salary | 7000元/月 |
| Portfolio | 百度网盘 https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE> |
| Exclude | 纯短视频/抖音/快手, AI抽卡师, 经纪人 |
| Last Resort | 短剧, AIGC方向 |
