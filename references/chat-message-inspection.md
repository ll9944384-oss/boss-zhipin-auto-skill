# BOSS直聘 Chat Message Inspection (Cron Job)

## Page Structure (Vue SPA)

The BOSS直聘 chat page (`https://www.zhipin.com/web/geek/chat`) is a Vue SPA. The conversation list sits in the left sidebar:

```
.chat-container.page-container
  └── .chat-wrap
        ├── .list-warp.v2              ← left sidebar (368px)
        │     └── .chat-user.v2
        │           └── .chat-content
        │                 └── .user-list
        │                       └── .user-list-content
        │                             └── ul (virtual list)
        │                                   └── li × N  ← one per conversation
        │                                         └── .friend-content-warp
        │                                               └── .friend-content (text preview)
        └── .chat-conversation          ← right pane (empty when no chat selected)
              └── .chat-no-data
```

## Detecting Unread Conversations

- The header shows `未读(N)` — total unread count
- Each conversation `<li>` with an unread badge contains a child element with numeric text `"1"`, `"2"`, etc.
- Detection: look for child elements inside `<li>` where `innerText` matches `/^[0-9]+$/` and is > 0
- The page also shows `未读(2)` in the tab filter bar area

## Conversation Item Format

Each `<li>` inner text follows this pattern:

```
{unread_badge}\n{time}\n{name}{company}{title}\n{last_message_preview}
```

Example:
```
1
20:10
<HR_NAME>COMPANY_5经理
你好，我们急招抖音短视频拍剪，如有兴趣希望可以深聊
```

## Message Type Classification

When checking HR messages, classify each conversation's last message:

| Type | Indicator | Action |
|------|-----------|--------|
| **HR question/invite** | Natural language: "方便面试吗", "会XX软件吗", "期望薪资" | Reply per rules |
| **Resume notification** | "您的附件简历...已发送给Boss" | System notification — skip |
| **Our sent message** | Contains `[送达]` or `[已读]` prefix | Our own message — skip |
| **Ad (AI抽卡师/经纪人)** | "诚聘AI抽卡师/经纪人/无关岗位" | Skip per exclusion rules |
| **Image-only** | `[图片]` with no text | Usually our sent image — skip |

## Unread Message Detection JS (for safari_boss_runner)

```javascript
// Find all conversation LI items
const lis = document.querySelector('.chat-user.v2').querySelectorAll('li');

// Find unread badges within each LI
for (let i = 0; i < lis.length; i++) {
  const li = lis[i];
  const allChildren = li.querySelectorAll('*');
  for (let j = 0; j < allChildren.length; j++) {
    const ch = allChildren[j];
    const ct = (ch.innerText || ch.textContent || '').trim();
    if (/^[0-9]+$/.test(ct) && parseInt(ct) > 0) {
      // Found unread badge — this conversation has an unread HR message
    }
  }
}
```

## Clicking into a Specific Conversation

Use `pyautogui` or the runner's click infrastructure to click the correct `<li>` element. The left sidebar is `.chat-user.v2`, each `<li>` has a known position from `getBoundingClientRect()`.

## After Opening a Conversation

Once a conversation is opened, the right pane (`.chat-conversation`) shows the message history. The `chat_state_value()` function's `hasChatInput` property confirms you're in an active chat context and can send messages.

## Common Pitfalls

- The page renders differently on first load vs. subsequent navigations — always check `chat_state_value().result.hasChatInput` before attempting to send
- Vue rendering can cause `getBoundingClientRect()` to return 0-width/0-height for elements that exist in DOM but aren't laid out yet — wait 1-2s after navigation
- The `user-list-content` child elements may not have identifiable class names — use index or text content matching instead
- Conversations are ordered newest-first; the first `<li>` with a badge is the most recent unread
