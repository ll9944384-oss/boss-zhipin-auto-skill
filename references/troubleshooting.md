# Troubleshooting: 会话无法打开

## 问题描述

在 BOSS直聘 SPA 聊天页面 (`/web/geek/chat`)，试图通过点击聊天列表项打开右侧会话面板时，以下方法均无效：

- pyautogui.click({x, y}) — 屏幕坐标点击
- element.dispatchEvent(new MouseEvent('click')) — 原生 JS 事件分发
- jQuery(element).trigger('click') — jQuery 事件触发
- element.click() — DOM 原生 click

## 页面布局

左右分栏布局：
```
.list-warp.v2 (左栏, 368px)  |  .chat-conversation (右栏, 812px)
```

默认未选中任何会话时，右栏显示："与您进行过沟通的 Boss 都会在左侧列表中显示"

## 如何检测会话是否打开

检查是否有可交互的输入框出现：
```javascript
var inputs = document.querySelectorAll('div.chat-input[contenteditable], textarea');
var hasChatInput = Array.from(inputs).some(function(el) {
  var r = el.getBoundingClientRect();
  return r.width > 20 && r.height > 10;
});
```

## 确认的可用 API

无需打开会话也能获取消息数据：

```javascript
// 获取所有好友信息
chatStore.friendInfos   // key: "{friendId}-{source}"

// 检查未读
chatStore.friendInfos[friendId].unreadCount

// 检查最后消息
chatStore.friendInfos[friendId].lastText
chatStore.friendInfos[friendId].lastIsSelf

// 排序列表
chatStore.friends   // 按 lastTS 降序排列的 friendId 数组
```

## 待探索的解决方向

1. **iGeekRoot 对象**：可能有编程式打开会话的方法
   - `iGeekRoot.chat` — 聊天对象
   - `iGeekRoot.sendAction({...})` — 发送动作
   - `iGeekRoot.router.push(...)` — 路由导航

2. **Vue 组件方法**：`GeekChat.default` 是一个 Vue 组件实例，其 `$options.methods` 中可能有会话选择方法。

3. **URL 路由参数**：当前路由只有 `/web/geek/chat`，尝试通过 router.push 添加 query params。
