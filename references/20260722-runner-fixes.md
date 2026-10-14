# 2026-07-22 Runner修复记录

## CONTACT_BUTTON_JS 评分修复

**问题**："感兴趣"和"立即沟通/继续沟通"的原始得分相同（239.325），但"感兴趣"在DOM中排在前面，导致pyautogui优先点击"感兴趣"而非"立即沟通"。

**修复**：在评分函数中增加：
```js
if (/^(立即沟通|继续沟通)$/.test(text)) score += 300;
```
修复后：立即沟通=539.325，感兴趣=239.325。

**修复位置**：`scripts/safari_boss_runner.py` 的 `CONTACT_BUTTON_JS` 常量。

## FIND_SEND_BUTTON_JS + click-send 命令

**新增常量** `FIND_SEND_BUTTON_JS`：动态查找"发送"按钮（文本为"发送"、可见、非disabled）。

**查找逻辑**：
1. 遍历所有 `button, a, div, span` 元素
2. 过滤出 innerText.trim() === '发送'、尺寸>20x15、非disabled、class不含'disable'/'subscribe'
3. 选择面积最小的元素（排除父容器）
4. 返回 rect（left, top, width, height）+ screen 信息

**适配两种UI**：
- 初始textarea对话框：`div.send-message:not(.disable)` 约 68x28
- 完整聊天页：`button.btn-v2.btn-sure-v2.btn-send` 约 62x28

**新增函数**：
- `find_send_button_screen_coord()` → 返回屏幕坐标 (x, y) 或 None
- `try_click_send(pause=1.0)` → 调用pyautogui点击发送按钮
- `cmd_click_send` → 注册为 `click-send` 命令

## send_text_value pyautogui后备

在 `send_text_value()` 末尾追加 `try_click_send()` 调用，确保JS事件不触发React时pyautogui能补点发送按钮。

返回结果中新增 `pyautogui_send_click` 字段，包含坐标和点击状态。

## cmd_send_bundle 自动导航

在发送首条消息后，检查 `chat_state_value().result`：
- 如果 `hasChatInput: true` 但 `hasChatControls: false` → 仍在初始textarea
- 自动执行 `run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")`
- 等待后重试图片上传

## 按钮坐标兼容性

修复前后的窗口尺寸变化（1512x945 → 1430x884）不影响功能，因为坐标是动态计算的。
