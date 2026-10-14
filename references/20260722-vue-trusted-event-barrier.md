# Vue SPA Trusted Event Barrier (2026-07-22)

## The Problem

BOSS直聘聊天页面（`/web/geek/chat`）是 Vue 2 SPA，其事件系统**只响应浏览器可信事件（isTrusted=true）**。所有程序化触发的事件——无论通过什么方式——都会被 Vue 的事件委托系统忽略。

## Proven Failures

The following approaches were ALL attempted and ALL failed to open a conversation:

| Approach | Method | Result |
|----------|--------|--------|
| JS `element.click()` | Native DOM click | ❌ Silent failure |
| `dispatchEvent(new MouseEvent('click', ...))` | Dispatched mouse click | ❌ Silent failure |
| `dispatchEvent(new PointerEvent('pointerdown', ...))` | React 18+ pointer events | ❌ Silent failure |
| `dispatchEvent(mousedown + mouseup + click)` | Full event sequence | ❌ Silent failure |
| `pyautogui.click(x, y)` | macOS native mouse click at screen coords | ❌ No effect |
| `AppleScript System Events click at` | macOS accessibility click | ❌ No effect |
| `AppleScript tell Safari to do JavaScript element.click()` | Safari WebKit JS execution | ❌ Silent failure |
| Vue 2 `$router.push('/web/geek/chat/62001')` | Vue Router navigation | ❌ URL updates, UI doesn't change |
| Vue 2 `$router.push({query: {geekId: '62001'}})` | Vue Router with query params | ❌ URL updates, UI doesn't change |
| `boss-item.__vue__.handleOpenChat()` | Direct Vue method call on component | ❌ Function runs, but no side effects |
| `boss-list.__vue__.$children[0].handleClickItem(dcVal)` | Vue method on parent list component | ❌ Function runs (returns undefined), no UI change |
| `child.$emit('click', dcVal)` | Vue custom event emission | ❌ Event delivered, no UI change |

## Root Cause

Vue 2's event delegation attaches listeners at the root DOM level via `addEventListener`. When events arrive from `dispatchEvent()` or programmatic `.click()`, the `event.isTrusted` property is `false`. Vue's internal event handling checks for trusted status in certain event handlers, particularly those that trigger route changes or WebSocket connections.

## Vue Component Tree (Discovered 2026-07-22)

```
App (Vue root)
 └── Chat (parent component)
      ├── computed: selectedFriend
      ├── methods: homepageInit, jumpToGuide, postMessageHandler, isChatNumShow
      └── boss-list (conversation list component, .list-warp)
           ├── data: handleClick, currentId, selectedFriend$, listType$
           ├── handleBroadcastBossDelete
           ├── handleChangeType
           └── $children[0] = boss-list (child instance, virtual scroll)
                ├── methods: handleOpenChat, handleClickItem, scrollToUser, loadMore
                ├── events emitted: on-click
                └── $children = [boss-search, VirtualListItem*, ...]
                     └── Each conversation item:
                          li.__vue__ = VirtualListItem
                          └── .friend-content-warp.__vue__ = boss-item
                               ├── methods: handleOpenChat (minified)
                               ├── d-c attribute = conversation ID (e.g. "62001")
                               └── emits: click, select, item-click, on-click
```

### Key Elements

- **Chat container**: `.chat-container.page-container` at (123, 49, 1184x755)
- **Left sidebar**: `.chat-user.v2` at (123, 69, 368x582)
- **Conversation item wrapper**: `.friend-content-warp` inside `li` — has `__vue__` boss-item component
- **Conversation item content**: `.friend-content` with `d-c="62001"` attribute (the conversation ID)
- **Conversation list UL**: `document.querySelectorAll('ul')[8]` has 40+ li children
- **Conversation list container**: `.user-list-content` > `ul` > `li.friend-content-warp`

### Page Configuration Data

```javascript
_PAGE = {
    uid: <YOUR_UID>,           // User ID for "YOUR_NAME"
    encryptUserId: "<YOUR_ENCRYPT_USER_ID>",
    token: "<YOUR_TOKEN>",
    isLogin: false,            // ⚠️ Can be false even when Safari UI shows logged in
    isGeekChat: true,
    name: "YOUR_NAME",
    identity: 0,
    ws: { useSSL: true, server: "ws6.zhipin.com", port: 443 }
}
```

## Practical Implications for Cron Job Mode

1. **Cannot open conversations programmatically** — The Vue SPA trusted event barrier is absolute. No JS, pyautogui, or AppleScript click can trigger conversation opening.

2. **Must rely on page already being in a conversation** — If the user has left a conversation dialog open, the `chat-input` contenteditable div is available and `send_text_value()` works.

3. **Detection-first approach**: 
   - Navigate to `/web/geek/chat`
   - Read conversation list text from `document.body.innerText` to identify HR messages
   - If there's an open conversation (hasChatInput=true), reply using `send_text_value`
   - If not: report the unread messages and ask user to manually open the conversation

4. **`_PAGE.isLogin` false-positive trap**: The page shows the user as logged in (displays name "YOUR_NAME", shows conversation list) but `_PAGE.isLogin` can be `false`. When this happens, the right panel always shows the empty state `.chat-no-data` ("与您进行过沟通的 Boss 都会在左侧列表中显示").

## The `d-c` Attribute

The `d-c` attribute on `.friend-content` elements holds the conversation ID. For the conversation with <HR>女士 at COMPANY_1, this was `d-c="62001"`. This might correspond to a `geekId` or `encryptGeekId` parameter in the API.

## See Also

- `references/20260713-vue-component-chat-access.md` — Earlier Vue component access techniques
- `references/20260713-session-debugging.md` — Prior debugging session details
