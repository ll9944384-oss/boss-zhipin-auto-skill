# Runner Fixes — 2026-07-11 Session

## Bridge Fix: navigate used wrong tab

**Problem**: `safari_boss_bridge.applescript` navigate mode set `URL of document 1` (first document of front window), which could be a Google Images or other non-BOSS tab. The BOSS直聘 tab was never navigated.

**Fix**: Changed navigate to first find the existing zhipin.com tab via `findBossTab("zhipin.com")`, then set its URL:

```applescript
try
  set targetTab to my findBossTab("zhipin.com")
  set URL of targetTab to targetUrl
on error
  if (count of windows) = 0 then make new document
  set URL of document 1 to targetUrl
end try
```

**Status**: Patch applied to `safari_boss_bridge.applescript`.

## Runner Fix: extract-cards selectors

**Problem**: `cmd_extract_cards` used `.job-card-wrap, .job-card-box` which no longer match current BOSS直聘 SPA DOM. Results were always empty.

**Fix**: Added multiple fallback selectors:
- `[class*="job-card"]`, `[class*="jobCard"]` — class-agnostic match
- `.job-list-box > li`, `.job-item` — list-based layout
- `'li[class*="job"]'`, `div[class*="job"] > a[href*="/job_detail/"]` — generic
- Fallback: `document.querySelectorAll('a[href*="/job_detail/"]')` → map to closest container

Also added per-card `rect` (bounding client rect) for click-coordinate-based navigation.

**Status**: Patch applied to `safari_boss_runner.py`.

## Runner Fix: click-chat matched "感兴趣"

**Problem**: `cmd_click_chat` and the inline `ensure_chat` JS searched for nodes containing `/立即沟通|继续沟通|感兴趣/`. On job detail pages, "感兴趣" appears in the DOM before "立即沟通", so it was matched first. Clicking "感兴趣" marks interest but does NOT open chat.

**Fix**: Changed to only match exact text: `t === '立即沟通' || t === '继续沟通' || t.startsWith('立即沟通') || t.startsWith('继续沟通')`. Removed "感兴趣" entirely.

**Status**: Patch applied to `safari_boss_runner.py` (both `cmd_click_chat` and inline in `cmd_send_bundle`).

## Runner Fix: send-text input selector too narrow

**Problem**: `send_text_value` searched for `div.chat-input, [contenteditable="true"], textarea, .ql-editor` which didn't match the job detail page's in-page chat overlay panel.

**Fix**: Added fallback chain:
1. `document.querySelector('[contenteditable="true"], textarea, div[contenteditable], [role="textbox"], input[type="text"], input:not([type])')` — generic
2. `Array.from(document.querySelectorAll('div, span')).find(el => el.isContentEditable)` — iterate all divs/span for contenteditables
3. Legacy class-based selectors as final fallback

**Status**: Patch applied to `safari_boss_runner.py`.

## Runner Fix: upload-image misidentifies detail-page "新增附件简历"

**Problem**: `upload_image_value` searches for `input[type="file"]` or class containing `sendimg/image/upload`. On the job detail page, the sidebar "新增附件简历" link (class `attachment-resume-upload`) is found first. This is NOT the chat image upload — it's an attachment resume upload for BOSS's resume system. The file dialog opened successfully but no image appeared in chat.

**Root cause**: The detail page does NOT have a visible chat image upload button. The "立即沟通" overlay chat panel doesn't include an image upload button in the current BOSS直聘 UI.

**Workaround**: Mark as `resume_image_manual_required` and output the full result JSON. User must manually drag the image into the chat.

## Successful quick-apply flow (verified):

```
1. navigate to job_detail/xxx.html (specific job detail page)
2. quick-apply --job-title ... --company ... --resume-image ...
   a. click_chat finds "立即沟通" → clicks it → chat overlay opens
   b. send_intro_with_portfolio finds overlay's contenteditable → types greeting+portfolio → clicks send button
   c. verify_greeting checks overlay page body for greeting key phrase
   d. verify_portfolio checks for pan.baidu.com in page body
   e. upload_resume_image (usually fails — see above)
3. Result: partial_sent_verified (greeting+portfolio OK, image needs manual drag)
```
