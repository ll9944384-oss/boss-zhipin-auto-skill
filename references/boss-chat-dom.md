# BOSS直聘 聊天DOM结构与React兼容性

> 2026-07-11 会话记录

## 页面结构

### 1. 职位详情页（Startchat 弹窗）
```
URL: /job_detail/xxx.html

div.dialog-wrap.startchat-dialog  (弹窗覆盖层)
  div.startchat-title              → "<HR>女士 · <HR_NAME>·人事经理"
  div.startchat-content            → 消息区域
    div.left
      div.message
        span.status.success        → "已发送"
        text                       → "你好~ 我对 高级视频剪辑师 很感兴趣..."
    div.edit-area
      textarea.input-area          ← 聊天输入框（可见）
      div.send-message.disable     ← 发送按钮（带 .disable class）
```

**关键点**：
- 输入框是 `textarea.input-area`，不是 contenteditable div
- 发送按钮是 DIV 带 class `send-message disable`（注意 class 名是 "disable" 不是 "disabled"）
- `!b.disabled` 对 DIV 返回 `true`（DIV 无 disabled 属性），所以按钮会被误认为可点击
- 必须用 `classList.contains('disable')` 检查

### 2. 完整聊天页（/web/geek/chat）
```
URL: /web/geek/chat

div.chat-container
  ul.chat-list                      → 左侧对话列表
    li                              → 每个 LI 是一个对话
      text                          → "22:48\n<HR>女士<HR_NAME>人事经理\n[送达]\n你好~..."
  div.chat-conversation             → 右侧当前对话
    div.top-info-content            → 对话头部信息
    div.message-content             → 消息列表
      div.message-item              → 每条消息
        span.message-status.status-delivery → "送达" / "已读"
    div.chat-input[contenteditable] ← 聊天输入框（contenteditable div）
    button.btn-v2.btn-sure-v2       ← 发送按钮（可能带 .disabled class）
    div.message-controls            → "发简历 换电话 换微信" 按钮区域
      input[type="file"][accept*="image"] ← 图片上传文件选择器（可见）
```

**关键点**：
- 输入框是 `div.chat-input[contenteditable]`，不是 textarea
- 发送按钮是 `button.btn-v2.btn-sure-v2`，class 含 `.disabled`（与 startchat 的 "disable" 不同）
- 有文件输入用于图片上传（accept=image/gif,jpeg,jpg,png）
- 对话列表项是 `li` 元素，不是 `div.chat-item`

## React 事件处理

### 无效的输入方式
```javascript
// ❌ 不触发 React 变化检测
input.innerText = text;
input.value = text;
input.dispatchEvent(new Event('input', {bubbles: true}));
```

### 有效的输入方式
```javascript
// ✅ 触发 React 合成事件（contenteditable div 和 textarea 都支持）
input.focus();
document.execCommand('selectAll', false, null);
document.execCommand('delete', false, null);
document.execCommand('insertText', false, text);

// ✅ 发送（按 Enter 键比点击按钮更可靠）
var enterEvent = new KeyboardEvent('keydown', {
    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
    bubbles: true, cancelable: true
});
input.dispatchEvent(enterEvent);

// 回退：点击发送按钮
var sendBtn = document.querySelector('.btn-send, .btn-v2.btn-sure-v2');
// 按钮可能是 DIV 或 BUTTON，DIV 没有 .disabled 属性
// 必须检查 class
if (sendBtn && !sendBtn.classList.contains('disabled') && !sendBtn.classList.contains('disable')) {
    sendBtn.click();
}
```

## 消息验证

`verify-message` 使用 `document.body.innerText` 搜索关键词。但在 startchat 弹窗中，弹窗内容可能不在 `body.innerText` 中（或在不同层级）。

### 可靠验证方式
在完整聊天页中，直接读取 `div.chat-conversation` 的 `innerText`：
```javascript
var convText = document.querySelector('.chat-conversation').innerText;
var hasLink = convText.includes('pan.baidu.com');
// 查找消息状态标记
var statuses = Array.from(document.querySelectorAll('.message-status'));
// 查找每条消息文本
var messages = Array.from(document.querySelectorAll('.message-content .message-item'));
```

## 发言流程（已验证工作流）

1. 导航到职位详情页
2. 点击 `a.btn-startchat`（含文本"立即沟通"）
3. 等待 2-3 秒，BOSS 自动发送默认招呼语，按钮变为"继续沟通"
4. **此时不要在 startchat 弹窗中发送自定义消息**（React 事件处理不一致，容易失败）
5. 导航到聊天列表页 `/web/geek/chat`
6. 在对话列表中找到对应公司（查找含公司名的 `li` 元素）
7. 点击 `li` 打开对话
8. 在 `div.chat-input[contenteditable]` 中用 `execCommand('insertText')` 输入消息
9. 用 `KeyboardEvent('keydown', {key: 'Enter'})` 发送
10. 验证 `div.chat-conversation` 中有关键词和送达状态
