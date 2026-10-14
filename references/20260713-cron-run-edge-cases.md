# 2026-07-13 Cron Run: Edge Cases

## Run Summary

Script `check_hr_messages_cron.py` ran at ~15:15. Processed: <HR_NAME> (COMPANY_6猎头顾问, 短剧方向提问). 
Unread at start: `未读(2)`. Conversation reopened during run: `未读` (王玉博 new message appeared mid-session).

## Conversation Order vs. Opening Success

**First conversation** (王玉博, 杭州欣上品牌设计) was top of list with unread badge "2":
- Text: `2\n15:11\n王玉博杭州欣上品牌设计招聘者\n我们在华元大厦 南苑地铁口`
- Classification fallback returned "reply" (len(lines)=4 ≥3, last line len=15 >8)
- **But `open_conversation()` returned False** — likely because the `<li>` element was not a `.friend-content` child and the `left/top` position matched a virtual-scroller-managed item whose Vue handler ignored dispatched events
- Script correctly fell through to next conversation (<HR_NAME>) and replied there

**Key lesson**: Being first in the list with correct classification does not guarantee opening works. Virtual-scroller or Vue event-binding differences can cause failure. The fallthrough mechanism is essential.

## The "Badge Number as First Line" Classification Fragility

Conversation text from DOM scan looks like:

```
2
15:11
王玉博杭州欣上品牌设计招聘者
我们在华元大厦 南苑地铁口
```

The leading "2" is the **unread badge number** bleeding into the DOM text content. `classify_conversation()`:
- `first_line = "2"` → doesn't match `[送达]`/`[已读]`/`[图片]` guards
- Falls through to `lines[-1].length > 8` check → returns "reply"

**This works correctly today**, but is fragile:
- If the badge number happens to be consumed by the `lines >= 3` check as part of the line count requirement, it's fine
- If the HR's actual message starts with a number (e.g., "5分钟到公司"), it could be confused with the badge
- Fix: explicitly check and strip leading all-numeric lines that look like badge counts before classification

## New HR Pattern: Location Share + Follow-Up

王玉博's two messages form a pattern not explicitly listed in the classification table:

1. `我们在华元大厦 南苑地铁口` — HR shares office location (invitation subtext)
2. `好的 你可以考虑一下` — HR asks candidate to consider (follow-up nudge)

This is an interview invitation expressed via location share + nudge, rather than explicit "方便来面试吗?". 
The classification correctly triggers "reply" via fallback, but the **reply template** for `build_reply()` does not have a specific match for this pattern — it uses the generic catch-all at the bottom:

> `"您好，感谢您的联系！我有剪辑和后期制作经验..."`

**Recommendation**: Add a pattern match in `build_reply()` for location-sharing invites, e.g.:
```python
if any(kw in hr_msg for kw in ["华元大厦", "南苑", "地铁口", "我们在"]):
    return f"好的，感谢您的邀请！我在杭州，方便进一步了解岗位详情。这是我的作品集，您先看看。{PORTFOLIO_TEXT}"
```

## New Message Appeared Mid-Session (Confirmed Existing Finding)

After processing <HR_NAME>, 王玉博's conversation gained a new message: `"好的 你可以考虑一下"` at 15:15.
This confirms the existing documented behavior (发现4 in SKILL.md) that **WebSocket-pushed messages appear mid-process**.

IMPORTANT: The unread badge went from `未读(2)` → `未读` (still has unread count, just no number shown in the tab). After the script finishes, there is still **1 unread conversation** (王玉博's new message). The next cron run will pick it up.
