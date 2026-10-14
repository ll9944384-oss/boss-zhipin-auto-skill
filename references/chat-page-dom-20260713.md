# BOSS直聘 Chat Page DOM Structure (discovered 2026-07-13)

## Page URL
`https://www.zhipin.com/web/geek/chat`

## Framework
Vue 2 SPA (production build, `__vue__` property on elements, `data-v-*` scoped attributes)

## Full DOM Hierarchy

```
DIV.chat-container.page-container     [left=123, top=49, 1184×622]
  DIV.chat-wrap                        [left=123, top=69, 1184×582]
    DIV.chat-user.v2                   [left=123, top=69, 368×582]    ← left sidebar
      DIV.user-list?                   (between chat-user and list-warp)
        DIV.user-list-content          [left=123, top=161, 368×490]
          UL[role="group"]             (virtual scroller)
            LI[role="listitem"]        [left=123, top=167, 364×78]  ← each conversation
              DIV.friend-content-warp  [left=123, top=167, 364×78]
                DIV.friend-content     [left=131, top=169, 348×75]  ← d-c="62001" (fixed, NOT session ID!)
                  DIV.figure           [left=143, top=184, 46×46]   ← avatar wrapper
                    IMG.image-circle                                   ← avatar image
                  DIV.text             [left=201, top=184, 266×45]  ← text content
                    DIV (time)         [left=201, top=184, 266×0]   ← "02:41"
                      SPAN.time        [left=434, top=184, 33×19]   ← "02:41"
                    DIV.title-box      [left=201, top=184, 233×18]
                      SPAN.name-box    [left=201, top=184, 219×18]  ← "<HR>女士杭州萧山王波美甲..."
                    DIV.gray.last-msg  [left=201, top=211, 266×18]
                      SPAN.last-msg-text [left=201, top=211, 230×18] ← message preview
                  DIV.user-operation    [hidden, 0×0]
    DIV.chat-content                   [left=123, top=161, 368×490]  ← same as user-list-content? (overlap)
      DIV.user-list                    [left=123, top=161, 368×490]
        DIV.user-list-content          (see above)
          UL[role="thead"]             (empty, table header slot)
          UL[role="group"]             (virtual scroller, style="padding: 0px 0px 4680px;")
            LI[role="listitem"] ×N

    DIV.chat-conversation              [left=495, top=69, 812×582]  ← right panel
    DIV.chat-no-data                   [left=495, top=69, 812×582]  ← shown when no conversation open
```

## Filter Tabs

```
DIV.label-list                         [left=123, top=117, 368×44]
  LI.selected > SPAN.label-name        "全部" (default)
  LI > SPAN.label-name                 "新招呼"
  LI > SPAN.label-name                 "仅沟通"
  LI (or DIV.ui-dropmenu-v1)           "更多" (dropdown)
```

**Note:** "未读(2)" appears as text inside `.label-list` but is NOT a separate clickable tab element. It's a counter shown alongside the "全部" tab.

## Vue Components (discovered via `__vue__` property)

### chat-user (.chat-user)
- Methods: `handleClickItem(index)`, `handleOpenChat(item)`, `loadMore`, `checkOverFlow`, `getIsAIFilterActive`, `scrollToUser`, `clearRouteQuery`, `updateShowFilter`
- All compiled to `[native code]` in production

### list-warp (.list-warp)
- Methods: `handleClick(index)`, `handleChangeType`, `handleBroadcastBossDelete`, `changeListType`

### user-list-content (.user-list-content)
- Virtual scroller methods: `scrollToIndex`, `scrollToOffset`, `getSize`, `scrollToBottom`

## Key Selectors for JS

| Purpose | Selector |
|---------|----------|
| First conversation item | `.friend-content-warp` |
| Click trigger element | `.friend-content` |
| Avatar | `.figure > .image-circle` |
| Name | `.name-box` |
| Last message preview | `.last-msg-text` |
| Time | `.time` |
| Virtual list container | `ul[role="group"]` |
| Right panel (chat view) | `.chat-conversation` |
| Right panel (empty state) | `.chat-no-data` |
| Chat input | `div.chat-input[contenteditable="true"]` |

## Message Classification (from page text)

When reading `document.body.innerText`, conversation entries look like:

```
[badge_count\newline]
[time\newline]
[name][company][title]\newline
[last_message_preview]
```

Examples:
```
02:41
<HR>女士杭州萧山王波美甲...招聘者
<HR>女士的微信号：<WECHAT_ID>
```
↑ HR message — sharing WeChat contact

```
1
昨天
<HR_NAME>COMPANY_5经理
你好，我们急招抖音短视频拍剪，如有兴趣希望可以深聊
```
↑ HR message — recruitment (needs classification)

```
昨天
<HR_NAME>COMPANY_6猎头顾问
[送达]
您好，感谢联系...
```
↑ User's own message (marked [送达])

## Critical Notes

1. **`d-c="62001"` is NOT a session ID** — All conversation items share this same value. It's a Vue directive attribute, not an identifier.

2. **Virtual scroller padding** — `ul[role="group"]` has `padding-bottom: 4680px` which means the list has ~60 items but only ~11 are rendered in the DOM at any time.

3. **`.friend-content-warp` vs `.friend-content`** — The warp is the outer wrapper (includes padding/margins), the content is the inner element. Vue event handlers bind to `.friend-content` in this version.

4. **Page does NOT change URL** when opening a conversation — The URL stays at `https://www.zhipin.com/web/geek/chat`. Cannot rely on URL hash or pathname to identify active conversation.
