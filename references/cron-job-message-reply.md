# BOSS直聘 Cron Job 消息回复技术备忘

> 记录于 2026-07-13 会话。下次执行前先读此文件。

## Vue SPA 点击失效解决方案

**问题**：在 BOSS直聘聊天页面（Vue SPA），`el.click()` 或单次 `dispatchEvent(new MouseEvent('click'))` 
无法触发 Vue 的事件处理函数。表现为：JS 代码返回 `clicked: true`，但右侧聊天面板仍然显示
"与您进行过沟通的 Boss 都会在左侧列表中显示"。

**解决方案**：必须依次触发 `mousedown` → `mouseup` → `click` 三个事件：

```javascript
const el = document.querySelector('.friend-content');
const rect = el.getBoundingClientRect();

['mousedown', 'mouseup', 'click'].forEach(type => {
  el.dispatchEvent(new MouseEvent(type, {
    bubbles: true, cancelable: true, view: window,
    clientX: rect.left + rect.width / 2,
    clientY: rect.top + rect.height / 2
  }));
});
```

**验证**：点击后等待 2-3 秒，调用 `chat_state_value()` 检查 `hasChatInput: true`。

## 扫描全部对话（不逐个打开）

用 `document.body.innerText` 一次性获取全部文本，在 cron job 模式下避免逐个打开对话：

```python
# Python 端调用
js = 'return (document.body.innerText || "").slice(0, 5000);'
result = safari_boss_runner.json_js(js)
```

返回文本的格式说明：
- 对话条目文本格式：`[时间]\n[姓名][公司][职位]\n[消息预览]`
- `[送达]` / `[已读]` / `[图片]` 标记的是我方发出或已读的消息
- 无标记的最近消息可能是 HR 消息
- `"您正在与Boss Xxx沟通"` 是系统通知（对话创建），不是 HR 消息
- 未读标记 "1"、"2" 可能出现在对话条目前后

## WeChat 交换卡片处理

系统卡片出现在聊天面板中，文本为 "我想要和您交换微信，您是否同意"，下方有"拒绝"和"同意"按钮。

**处理步骤**：

1. 用 `document.querySelector('.message-card-buttons')` 找到按钮容器
2. 找到 `同意` 按钮：`agreeBtn = document.querySelector('.message-card-buttons button')` 
   或在容器内找 `textContent === '同意'` 的元素
3. **必须用 mousedown+mouseup+click 序列**触发（同上方 Vue SPA 点击方案）
4. 等待 1-2 秒
5. 读取 `.chat-conversation` 文本确认微信号：
   - 成功后的文本包含 `微信号`、`复制微信号` 按钮
   - 格式示例：`<WECHAT_ID>\n<HR>女士的微信号\n<WECHAT_ID>\n复制微信号`
6. 发送回复消息告知已添加微信，附上作品集链接

## send_text_value 行为说明

`safari_boss_runner.send_text_value(text)`：
1. 用 JS 查找聊天输入框（`[contenteditable]` 或 `textarea.input-area`）
2. 往输入框填入 base64 编码的文本
3. 触发 `InputEvent`
4. JS 端触发 `KeyboardEvent('keydown', {key: 'Enter'})` 尝试发送
5. Python 端再用 pyautogui 点击"发送"按钮作为备用

**不需要**额外调用 `click-send`，但调用一次也无害。

## 验证回复成功

发送回复后，使用 `verify_message_value(contains_text)` 或直接读 `.chat-conversation` 文本：

```python
result = safari_boss_runner.verify_message_value('已添加微信')
# result.result.verified === true 表示消息出现在最近聊天中
```

## 注意事项

- **pyautogui 限制**：在 Hermes 桌面终端中，`pyautogui.click()` 返回 `ok: true` 但坐标映射
  可能不准（取决于 VM 显示与 macOS 桌面之间的映射关係）。优先使用 JS 事件模拟方案。
- **Vue 渲染延迟**：每次点击或导航后等待至少 2-3 秒让 Vue 完成渲染。
- **AppleScript bounds 命令**：`safari_boss_bridge.applescript` 的 `bounds` 命令返回 Safari
  窗口位置，格式 `left,top,right,bottom`，可用于计算屏幕坐标。
- **System Events click 权限**：`tell application "System Events" to click` 需要 macOS
  辅助功能权限（隐私→辅助功能），没有授权时会返回 `-25200` 错误。
