# BOSS直聘 Conversation List DOM Structure (2026-07-23)

See `references/20260723-conversation-list-dom-and-dynamic-render.md` for detailed documentation of:

## Key Findings

### `.list-warp li` Index Layout
- Indices 0-4: Filter tabs (全部, 未读, 新招呼, 仅沟通, 更多)
- Indices 5-7: Dropdown options (有交换, 有面试, 不感兴趣)
- **Index 8+**: Actual conversation items

### Identifying HR vs Sent Messages
- Messages with `[已读]` or `[送达]` tag = messages WE sent
- Messages with NO tag = messages FROM HR (the last message in that conversation)

### Dynamic Re-Rendering
Conversations can disappear/appear between page visits due to Vue virtual scrolling / lazy loading. Always scan fresh.

### Conversation Clicking is Blocked
macOS Sequoia blocks all synthetic click events (pyautogui, JS .click(), AppleScript) from reaching Safari web content. Vue SPA requires `event.isTrusted === true`. This is a fundamental barrier — conversations cannot be opened programmatically.
