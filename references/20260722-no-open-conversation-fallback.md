# 2026-07-22 Cron: 聊天页对话打开失败记录 — 降级为报告模式

## 场景

Cron job 定时检查 BOSS直聘聊天页面，发现新 HR 消息但**无已打开的对话窗口**。

## 现象总结

1. **无对话打开** (`hasChatInput: false`) — 聊天面板显示空状态文字：
   「与您进行过沟通的 Boss 都会在左侧列表中显示」

2. **无法程序化打开对话** — 三项尝试均失败：
   - JS `dispatchEvent(new MouseEvent('click'))` + `mousedown/mouseup/click` 序列 → React SPA 可信事件屏障拦截
   - `pyautogui.click(x, y)` → Hermes VM 与 macOS Safari 坐标映射不对齐，点击落在错误位置或无响应
   - AppleScript `tell application "System Events" to click at {x,y}` → 错误 `-25200`（macOS 辅助功能权限被拒绝）

3. **AppleScript Bridge 不稳定** — 多次 JS 操作后 bridge 丢失 `jsResult` 变量，需重新 `navigate` 恢复

## DOM Selectors 确认（2026-07-22）

| 元素 | 选择器 | 尺寸 | 位置 (left, top) |
|------|--------|------|------------------|
| 对话列表容器 | `.friend-content-warp` | 364×78 | (123, 167+) |
| 对话列表内框 | `.friend-content` | 348×75 | (131, 169+) |
| 聊天面板（空） | `.chat-conversation` | 812×715 | — |

对话项在 `<li>` 元素中，但 `<li>` 本身没有有用的 class。
`.[class*="friend"]` 是可靠的对话项选择器。

## 正确降级流程

当 `chat_state_value()` 返回 `hasChatInput: false` 时：

1. 用 `document.body.innerText` 读取全部聊天列表文本
2. 解析出所有未回复的 HR 消息（无 `[已读]`/`[送达]` 标记、无我方回复）
3. 按时间排序（最新的在最上面），按规则过滤排除项
4. **输出报告**而不是尝试发送回复
5. 报告格式：
   - 最新待回复消息（谁、时间、消息内容、判定为由）
   - 其他待处理消息
   - 已排除消息及原因
   - 建议：用户手动打开相关对话，下一次 cron 即可自动回复

## 消息源头判断规则（补充）

从 `document.body.innerText` 解析对话列表时，格式为：
```
[时间]
[姓名][公司][职位]
[消息内容]
```

- `[已读]` / `[送达]` 前缀 → 我方发送或已读标记，非 HR 新消息
- 无前缀 + 姓名+公司+职位格式 → 可能是 HR 新消息
- 「匹配」+「不」→ 系统拒信，跳过
- 「面试时间已过」→ 已过期，跳过

## 已知限制

- 无法在 cron 模式下打开新对话
- 只能回复**已有已打开对话**的 HR 消息
- 每次导航到聊天页后，Vue SPA 可能丢失上次打开的对话状态
