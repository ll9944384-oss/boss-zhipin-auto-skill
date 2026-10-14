# BOSS直聘 SPA 交互模式与关键发现

## 页面架构

BOSS直聘聊天页面 (`/web/geek/chat`) 使用自研组件框架（非纯Vue），特点：
- `data-v-*` 属性标识组件实例
- `d-c` 属性标识组件类型（如 `d-c="62001"` = 好友列表）
- 虚拟滚动列表：`ul[role="group"]` 带大 `padding-bottom`
- SVG sprite 图标系统

## CSS 选择器参考

| 目标 | 选择器 |
|------|--------|
| 聊天列表 | `.list-warp.v2` |
| 聊天容器 | `.chat-container.page-container` |
| 列表区 | `.chat-content > .user-list > .user-list-content` |
| 好友项 | `li[role="listitem"]` |
| 好友内容 | `.friend-content-warp > .friend-content` |
| 对话面板 | `.chat-conversation` |
| 对话输入框 | `div.chat-input[contenteditable]` |

## 可用全局变量

| 变量 | 用途 | 关键属性 |
|------|------|----------|
| `chatStore` | 聊天数据存储 | `friendInfos` (所有好友信息), `friends` (排序列表), `getFriendInfoById(id)` |
| `iGeekRoot` | 主应用根对象 | `chat`, `router`, `open()`, `sendAction()`, `bossDialog` |
| `_PAGE` | 页面配置 | `userId`, `encryptUserId`, `name`, `token` |

### friendInfos 数据结构

每个好友条目以 `"{friendId}-{source}"` 为 key，关键字段：
- `name`, `brandName`, `positionName`, `jobName` — HR/公司/岗位信息
- `lastText` — 最后一条消息内容
- `lastIsSelf` — 最后一条是否为自己发的
- `unreadCount` — 未读数
- `lastTS` — 最后消息时间戳
- `lastMsgStatus` — 0=未读, 1=已送达, 2=已读
- `encryptBossId`, `encryptJobId`, `jobId` — 加密标识

## ⚠️ 关键问题：无法可靠打开会话

截至 2026-07-13，以下方法均无法打开 BOSS直聘 SPA 聊天会话：

- **pyautogui 屏幕坐标点击** — 点击坐标正确（计算了 Safari 工具栏偏移），但 Vue 事件被忽略
- **JavaScript `.click()`** — DOM 原生点击不触发框架事件
- **jQuery `.trigger('click')`** — 无效
- **MouseEvent 分发** — `dispatchEvent(new MouseEvent('click', ...))` 无效

**原因分析**：BOSS直聘的自研框架通过事件代理在容器级别处理点击，不是监听单个 LI 元素。框架内部可能使用 `mousedown` + `mouseup` 序列或自定义手势识别，单纯的 `click` 事件不足以触发会话切换。

**推荐的排查方向**：
- 通过 `iGeekRoot.chat` 或 `iGeekRoot.sendAction` 编程式打开会话
- 探索 `iGeekRoot.router` (Vue Router) 是否能通过 query 参数导航到特定会话
- 探索 `iGeekRoot.bossDialog` 的 API

## 检测会话是否已打开

```javascript
var inputs = document.querySelectorAll('div.chat-input[contenteditable], textarea');
var hasInput = inputs.some(function(el) {
  var r = el.getBoundingClientRect();
  return r.width > 20 && r.height > 10;
});
```

`hasChatInput === true` 表示右侧会话面板已打开且有输入框。默认未打开时右侧显示 "与您进行过沟通的 Boss 都会在左侧列表中显示"。

## safari_boss_runner.py 已知问题

### `json_js()` 函数

`json_js()` 使用 Python f-string 包装 JS 代码，在插入 `js_body` 参数时：
- `js_body` 已作为原始字符串传入，f-string 不会再次解析其内部的 `{}`
- **但如果 `js_body` 是一个自执行函数 (IIFE) 如 `(function(){...})()`，外层包装器 `(function(){{ {js_body} }})()` 不会自动 return IIFE 的结果**
- 正常写法：`js_body` 应以 `return {...}` 结尾，不要包含外层 IIFE

**正确用法**：
```python
js = '''  # NOT a raw string — f-string handles {{}}
var items = document.querySelectorAll('...');
return {result: items.length};
'''
result = r.json_js(js)  # Returns {ok: true, result: {result: N}}
```

**错误用法**：
```python
js = r'''  # raw string with IIFE
(function() {
  return {result: ...};
})()
'''
result = r.json_js(js)  # Returns {ok: true} — result is undefined!
```

如果需要对 IIFE 风格的 JS 代码使用 `json_js`，需要使用 `safari_js()` 手动包装 JSON.stringify。
