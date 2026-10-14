# 2026-07-22 Session: Runner Fixes & Auto-Reply Workflow

## Runner Code Fixes Applied

### 1. CONTACT_BUTTON_JS scoring fix
- Problem: "感兴趣" and "立即沟通" scored the same (239.325), but "感兴趣" was listed first in DOM → pyautogui clicked wrong button
- Fix: Added `if (/^(立即沟通|继续沟通)$/.test(text)) score += 300;` before penalty subtraction
- Result: "立即沟通" now scores 539.325 vs "感兴趣" 239.325

### 2. click-send command (new)
- New command: `./safari_boss_runner.py click-send`
- Dynamically finds "发送" button via JS + pyautogui click
- Handles both UI variants: initial textarea (DIV.send-message) and full chat page (BUTTON.btn-v2.btn-sure-v2.btn-send)
- Button found by: smallest visible element with text "发送", not disabled, not "subscribe"

### 3. pyautogui send fallback in send_text_value
- After JS fills text and attempts JS click/Enter, `try_click_send()` is called as fallback
- This fixes React SPA ignoring `dispatchEvent(KeyboardEvent)` and `send.click()`

### 4. Auto-navigate to chat after first send (cmd_send_bundle)
- After send_text + click-send, checks `chat_state_after_send`
- If `hasChatInput: true` but `hasChatControls: false` → still on initial textarea
- Auto-navigates to `https://www.zhipin.com/web/geek/chat` for full chat page
- This ensures image upload and portfolio send work for NEW companies

## Apply Flow (working order)

For NEW companies:
1. navigate → job_detail page
2. click-chat (click "立即沟通", opens initial textarea)
3. send-text (fills greeting+portfolio, pyautogui clicks send)
4. navigate → /web/geek/chat (auto-redirect to full chat)
5. upload-image (send resume)
6. send-text + click-send (send portfolio link separately)

For EXISTING chats:
1. navigate → job_detail page
2. click-chat (click "继续沟通", goes to full chat page)
3. upload-image (send resume)  
4. send-text + click-send (send greeting+portfolio OR just portfolio)

## HR Auto-Reply Pattern

Cron job runs every 30min, checks chat page for unread HR messages:
- **HR asks for resume** → click "同意" button → select first .pdf → click dialog "发送"
- **HR asks question / invites** → polite reply + portfolio link
- **HR sends irrelevant ad** (AI抽卡师, 经纪人, 无关岗位) → skip
- Use send-text + click-send to actually send replies

## Resume "同意" Button Flow
1. Find "同意" SPAN in chat area
2. Click with pyautogui → opens dialog with .pdf files
3. Find first .pdf item in dialog (YOUR_NAME.pdf)
4. Find "发送" button in dialog (not main chat send)
5. Click both

## Image Upload
- Works only on full chat page (hasChatControls: true)
- Uses pyautogui to click file dialog + Cmd+Shift+G + paste path
- Verify via before/after image count comparison

## Window Size Note
Safari window: 1430x884 (inner: 1430x804) — different from earlier 1512x945
chrome_top = max(884 - 804, 70) = 80
