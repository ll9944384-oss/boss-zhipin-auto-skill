# 2026-07-12 Session: send-text React SPA 发送修复 + 全自动流程验证

## 问题
`send-text` 的 JS 事件派发 (`dispatchEvent` + `send.click()`) 无法触发 BOSS直聘 React SPA 的发送。
文本填入输入框后卡住，按钮显示"发送中"但实际未送达。

## 修复（已应用）

### 1. FIND_SEND_BUTTON_JS — 动态查找发送按钮
找到最小面积的"发送"按钮坐标，适配两种 UI：
- **初始对话框 (textarea)**: `div.send-message` 坐标约 (776, 652, 68, 28)
- **完整聊天页 (div.chat-input)**: `button.btn-v2.btn-sure-v2.btn-send` 坐标约 (1256, 811, 62, 28)

### 2. click-send 命令
```bash
./safari_boss_runner.py click-send
```
用 JS 实时查找"发送"按钮 → `screen_click_points()` 转屏幕坐标 → `pyautogui.click()` 点击。
返回 `{ok, coord: {x, y}, click: {ok}}`。

### 3. send_text_value 集成 pyautogui fallback
每次 JS 填充文本后自动调用 `try_click_send(pause=1.0)`，结果记录在 `result["pyautogui_send_click"]`。

### 4. cmd_send_bundle 首次发送后导航
新公司首次发送后在 `send_text_value` → 检测 `hasChatControls: false` → 自动 `run_bridge("navigate", "/web/geek/chat")` → 重试图片上传。

### 5. CONTACT_BUTTON_JS 评分修复
"感兴趣"和"立即沟通/继续沟通"原始得分相同（239.325）。"感兴趣"排在 DOM 前面被优先点击。
修复：`if (/^(立即沟通|继续沟通)$/.test(text)) score += 300;` 确保沟通按钮优先。

## 验证通过的完整流程（新公司）
```python
1. navigate → job detail page
2. click-chat → 点击"立即沟通"，系统发自动招呼，显示 textarea
3. send-text 填写自定义招呼+作品集 → pyautogui 自动点发送
4. send_bundle 检测到仍为初始 textarea → navigate 到聊天页
5. upload-image ×2 → 文件对话框自动上传
6. send-text 作品集链接 → click-send 点发送按钮
7. verify-message 验证"送达"
```

## 已验证公司（全流程通过）
- 恒彩装饰 — 后期特效剪辑师 ✅
- 杭州霖禾文化创意 — 视频剪辑师 ✅
- 华普永明 — 视频剪辑专员 ✅
- COMPANY_10 — 视频剪辑师 ✅
- COMPANY_11发展 — 拍摄剪辑师 ✅

## 注意事项
- `click-send` 会自动找最小面积的"发送"按钮（排除父容器误匹配）
- 全自动执行：不允许中途停下来让用户手动操作
- 异常时输出完整 JSON 后继续下一个岗位
