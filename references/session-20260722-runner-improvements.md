# 2026-07-22 Runner Improvements & Workflow

## Fix: Button Scoring — "感兴趣" vs "立即沟通"

The CONTACT_BUTTON_JS scoring function gave equal scores to "感兴趣" and "立即沟通"
but "感兴趣" appeared first in the DOM, causing pyautogui to click it instead of
"立即沟通". This meant chat never opened.

**Fix (safari_boss_runner.py line 142):**
```js
if (/^(立即沟通|继续沟通)$/.test(text)) score += 300;
```
This ensures "立即沟通"/"继续沟通" always score higher than "感兴趣" (now 539 vs 239).

## New Command: click-send

BSOS直聘's React SPA ignores JS `send.click()` and `dispatchEvent(KeyboardEvent)`.
The `send-text` command fills text into the input but the message is NOT actually sent.

**Fix:** Added `click-send` command that:
1. Uses `FIND_SEND_BUTTON_JS` to locate the "发送" button dynamically (supports both
   initial textarea dialog and full chat page)
2. Converts viewport coordinates to screen coordinates via `screen_click_points()`
3. Clicks with pyautogui

**Usage:**
```bash
./safari_boss_runner.py send-text '您的消息'
./safari_boss_runner.py click-send      # ← must call this after every send-text
```

## Improved: send_text_value — Auto pyautogui Fallback

`send_text_value()` now calls `try_click_send()` after the JS fill, so `apply-current-job`,
`smart-apply`, and `quick-apply` all benefit from pyautogui click-send automatically.
Result includes `pyautogui_send_click` key with click coordinates and status.

## Improved: cmd_send_bundle — Auto Navigate to Chat After First Send

For NEW companies (no prior chat), clicking "立即沟通" opens a TEXTAREA on the job
detail page (hasChatInput=true, hasChatControls=false). After sending the first
message, the page needs to navigate to the full chat page before image upload works.

**Fix:** Added post-send check in `cmd_send_bundle` (after greeting_result):
```python
chat_state_after_send = chat_state_value()
if hasChatInput and not hasChatControls:
    run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
    time.sleep(args.wait + 1.0)
```
This navigates to the full chat page so subsequent `upload-image` calls work.

## Workflow for Different Scenarios

### New Company (no prior chat)
1. `navigate` to job_detail page
2. `click-chat` → clicks "立即沟通", opens textarea
3. `send-text` greeting+portfolio → `click-send`
4. Bundle auto-navigates to /chat
5. `upload-image` resume image
6. `send-text` portfolio link → `click-send`

### Existing Chat (has prior conversation)
1. `navigate` to job_detail page
2. `click-chat` → clicks "继续沟通", goes to full chat page (hasChatControls=true)
3. `upload-image` resume image
4. `send-text` portfolio link → `click-send`

### Sending Images on Full Chat Page
The image upload button only works when `hasChatControls=true` (full chat page DIV.chat-input,
not the initial TEXTAREA.input-area). If `upload-image` returns `image_button_not_found`,
navigate to /chat first, then retry.

## User Preferences (2026-07-22)
- AIGC-related editing positions ARE acceptable (previously "最后考虑", now open)
- 拍剪一体 (shoot+edit integrated) positions are excluded
- MCN剪辑 positions are excluded
- Pure editing/后期 positions preferred over 拍摄+剪辑
