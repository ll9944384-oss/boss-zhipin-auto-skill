# Session 2026-07-12: Button Scoring Fix & Image Upload Workflow

## Problem: Clicked "感兴趣" Instead of "立即沟通"

The runner's `CONTACT_BUTTON_JS` scoring algorithm gave identical scores to "感兴趣"
and "立即沟通" buttons (both ~239.325), and since "感兴趣" appeared first in the DOM,
pyautogui always clicked the wrong button.

### Fix Applied (2026-07-12)

In `/scripts/safari_boss_runner.py`, line ~142:

```javascript
// Before:
score -= Math.max(0, r.width * r.height / 10000);

// After:
if (/^(立即沟通|继续沟通)$/.test(text)) score += 300;
score -= Math.max(0, r.width * r.height / 10000);
```

This gives "立即沟通"/"继续沟通" a +300 bonus, making them always (score ~539) beat
"感兴趣" (score ~239).

## Image Upload Workflow

### Problem: `apply-current-job` returns `resume_image_manual_required` with
`reason: image_button_not_found`

The job detail page's inline chat textarea (`TEXTAREA.input-area`, placeholder "请简短描述您的问题")
has `hasChatInput: true` but NO chat controls toolbar — the image upload button only
exists in the FULL chat page UI where `hasChatControls: true`.

### Recovery Flow (verified working 2026-07-12)

1. Navigate to the job detail page (where "继续沟通" button exists)
2. Run `click-chat` — this clicks "继续沟通", navigates to the full chat page,
   AND opens the specific conversation, producing `hasChatInput: true, hasChatControls: true`
3. Now run `upload-image <path>` — the image button is available and upload succeeds

### Verification

```
before = {textCount, imgCount, total}
after  = {textCount, imgCount, total}
```
If `after.total > before.total`, the image was sent and counted in the DOM.

## Runner Notes

- The runner writes temp `.js` files and passes them to AppleScript via `osascript`.
- `apply-current-job` on an existing chat correctly detects `has_prior_intro` and
  switches to `resume_image_only` mode.
- "作品集" keyword match is used as proxy for portfolio verification; the actual
  `pan.baidu.com` URL may NOT have been sent even when `has_portfolio: true`.
