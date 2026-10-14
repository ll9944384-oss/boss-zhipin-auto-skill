# BOSS直聘 Cron Job Pitfalls (Session 2026-07-22)

Discovered during the 11:00 cron run:

## 1. Safari Multiple-Tab Ambiguity

`findBossTab("zhipin.com")` in the AppleScript bridge returns the **first** tab whose URL contains "zhipin.com". When both a job-detail page and the chat page are open, navigation and JS execution may target the wrong tab.

**Fix:** After every `navigate`, call `chat_state_value()` and verify `isChatPage === true`. If not, navigate again.

## 2. React Click Events

BOSS直聘's chat conversation list uses React. `element.dispatchEvent(new MouseEvent('click'))` does NOT trigger the page to switch conversations.

**Fix:** Use pyautogui to click at screen coordinates:
```
rect = element.getBoundingClientRect()
bounds = safari_bounds()  # via run_bridge('bounds')
toolbar_top = max(bounds['height'] - innerHeight, 70)
x = bounds['left'] + rect['left'] + rect['width'] / 2
y = bounds['top'] + toolbar_top + rect['top'] + rect['height'] / 2
click_screen_point(x, y, pause=1.5)
```

## 3. send-text + click-send as a Pair

`safari_boss_runner.py send-text "..."` types text into the contentEditable input and dispatches a KeyboardEvent('Enter'), but BOSS直聘's React chat may ignore the synthetic event. The message appears typed but is NOT sent.

**Fix:** Always call `click-send` immediately after `send-text`:
```
python safari_boss_runner.py send-text "..."
python safari_boss_runner.py click-send
```

## 4. HR Message vs Auto-Reply Detection

The conversation list shows the **last message** of each conversation. When the last message is our own auto-reply ("这是我的作品集…"), the conversation has already been handled. When the last message contains a greeting from HR ("你好~ 我对...很感兴趣"), it's an untouched HR message needing a reply.

The [送达] vs [已读] tag on our auto-reply is unreliable for determining if HR has seen it — [送达] just means the message was delivered to the server.

## 5. Name Collision

There are 4 directories under `.hermes/skills/` whose SKILL.md all declare `name: boss-zhipin-auto`:
- `boss-zhipin-auto/` (active)
- `boss-zhipin-auto.backup-20260711-1718/` (stale backup)
- `boss-zhipin-auto.backup-20260711-atomic-flow/` (stale backup)
- `boss-zhipin-auto.backup-20260711-no-online-resume/` (stale backup)

The 3 `.backup-*` directories cause skill_view() to fail with an ambiguous-name error. They should be removed to restore proper skill loading.
