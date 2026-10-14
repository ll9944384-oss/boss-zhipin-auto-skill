# chatStore Global Object Discoveries (2026-07-13)

## Background

This session attempted the cron job message-check workflow and discovered that the previously-documented `__vue__` component access approach no longer works. BOSS直聘 updated their chat page to use a virtual scrolling list (vue-virtual-scroller) which intercepts all synthetic events.

## What Changed

| Feature | Before (2026-07-11) | Now (2026-07-13) |
|---------|---------------------|-------------------|
| DOM structure | `.friend-list li`, `.chat-list li` | `ul[role="group"] > li[role="listitem"]` |
| Vue access | `el.__vue__.list$`, `.handleClickItem()` | `.__vue__` returns no useful API |
| CSS selectors (runner) | `.chat-list li` etc. found items | Same selectors find 0 items |
| Event handling | `.click()` or `mousedown+mouseup+click` worked | No synthetic event triggers virtual scroller |
| macOS click | `pyautogui` worked | Blocked by accessibility permissions (error -25200) |

## New Discovery: `window.chatStore`

The page exposes these global objects that survived the UI update:

### `window.chatStore`
- `chatStore.friends` — Array-like object (203 entries) containing ALL conversations
- `chatStore.getFriendInfoById(id)` — Returns full info object for a friend
- `chatStore.addFriends` — Function to add friends
- `chatStore.friendInfos` — Object indexed by friend ID

### `window.GeekChat`
- `GeekChat.default` — Vue 2 root component instance (`_isVue`, `_uid`, `$refs`, `$children`)
- Contains no exposed methods for opening conversations in current version

### Other useful globals
- `window.BossStartChat` — Chat configuration object
- `window.chat.communicating` — Current conversation state
- `window.ChatWebsocket` — WebSocket connection constructor

## Extracting Conversation Data

```python
from scripts.safari_boss_runner import json_js

# Get all conversation metadata
js = r'''
const cs = window.chatStore;
if (!cs || !cs.friends) return [];
const keys = Object.keys(cs.friends);
const results = [];
for (let i = 0; i < Math.min(keys.length, 50); i++) {
  const val = cs.friends[keys[i]];
  const info = cs.getFriendInfoById ? cs.getFriendInfoById(val) : null;
  if (info) {
    results.push({
      name: info.name,
      brandName: info.brandName,
      uniqueId: info.uniqueId,
      lastTS: info.lastTS,
      friendId: info.friendId
    });
  }
}
return results;
'''
all_friends = json_js(js)
```

## Virtual Scroller: Why Clicks Don't Work

The virtual scroll component uses:
1. `style="padding: 1170px 0px 3510px"` — padding-based scroll offset
2. WAI-ARIA roles: `role="group"`, `role="listitem"`
3. Event delegation on the container (not individual items)
4. ClientX/ClientY coordinate checking — synthetic events with correct coordinates still fail

**Confirmed failures**:
- `element.click()`
- `element.dispatchEvent(new MouseEvent('click', {clientX, clientY}))`  
- Full mousedown→mouseup→click sequence with PointerEvents
- Focus + Enter keyboard event
- AppleScript `tell application "System Events" to click at {x, y}`
- `pyautogui.click(x, y)`

## WebSocket Monitoring Potential

`window.ChatWebsocket` exists as a class. In future sessions, consider:
- Checking if `ChatWebsocket` exposes incoming message events
- Monitoring WebSocket frames for real-time HR message notifications
- This would avoid DOM interaction entirely for message detection

## Verification of Runner Script

The `open_recent_chat_value()` function in `safari_boss_runner.py` uses these CSS selectors which match 0 items:

```javascript
'.chat-list li, .friend-list li, .conversation-list li, [class*="chat"] [class*="item"], [class*="conversation"] [class*="item"], a[href*="/web/geek/chat"]'
```

Current matching selectors:
```javascript
'ul[role="group"] > li[role="listitem"]'
'[role="listitem"]'
'.friend-content-warp'
```
