# 2026-07-22 Cron 会话记录：MouseEvent dispatch 打开对话

## 问题

Cron定时检查HR消息时，`open_recent_chat_value()` 永远返回 `ok: false`（选择器不匹配当前DOM），`.friend-content[d-c].click()` 在部分场景下无法打开对话。

## 实际工作流

### 1. 读取对话列表（提取所有HR消息）

通过 `json_js()` 获取 `document.body.innerText` 的全量文本，从中解析所有对话。对话列表按时间倒序排列：

```
15:20 <HR>女士COMPANY_2招聘者
14:17 <HR>女士COMPANY_3hr
13:31 <HR>女士COMPANY_1招聘者
...
```

**识别规则**（页面文本启发式）：
- **HR主动消息**：无前缀，直接"时间\nHR名\n消息内容"
- **自己发的消息**：带 `[已读]` 或 `[送达]` 前缀
- **系统通知/拒绝**：无前缀但含"不够匹配"

### 2. 打开特定HR的对话

找不到 `__vue__` 属性（LI元素上没有），也无法用 Vue 组件直接访问。`.friend-content[d-c].click()` 单次调用不生效。

**成功方案**：对4个DOM元素同时dispatch完整MouseEvent序列：
- `<li>`
- `<div class="friend-content-warp">`
- `<div class="friend-content" d-c="62001">`
- `<div class="text">`

事件序列：`pointerdown → mousedown → pointerup → mouseup → click`

关键参数：`bubbles: true`, `cancelable: true`, 正确的 `clientX/clientY`。

### 3. 发送回复

```python
from safari_boss_runner import send_text_value, try_click_send

text_result = send_text_value('回复内容...')
time.sleep(1)
click_result = try_click_send(pause=1.0)
```

`send_text_value` 内置四层保障（JS填入+JS Enter+JS点击发送+pyautogui），但额外调用 `try_click_send()` 确保消息发出。

### 4. 验证

发送后页面文本中应出现我们的回复消息。检查方法：
```python
from safari_boss_runner import json_js
result = json_js("return (document.body.innerText || '').trim().slice(-2000);")
print(result.get('result', '')[-1500:])
```

### 5. 规则：每次只处理最新1条

每次cron触发只处理**最上面最新的1条**HR消息，处理完即停止。其他未处理消息留到下次cron触发。

## 本次会话的待处理列表

| 时间 | HR | 消息 | 判断 |
|------|-----|------|------|
| 15:20 | <HR>女士·COMPANY_2 | 短视频拍摄剪辑邀请 | 排除（纯短视频） |
| 14:17 | **<HR>女士·COMPANY_3** | "hello现在是离职状态吗？" | **已回复** ✅ |
| 13:31 | <HR>女士·COMPANY_1 | MCN达人孵化 | 排除 |
| 11:29 | <HR>女士·COMPANY_4 | "请问在考虑新的工作机会吗？" | 待处理（下次cron） |
| 10:56 | <HR_NAME>·COMPANY_18 | 短剧相关问题 | 最后考虑，待处理 |

## 关键经验

1. **不要依赖 `__vue__`** — LI元素上没有Vue内部属性暴露
2. **`.friend-content[d-c].click()` 可能失效** — 备选方案是MouseEvent dispatch
3. **`send_text_value()` + `try_click_send()` 组合可靠** — 本轮验证成功
4. **`json_js()` 在返回复杂嵌套结构时可能丢失 `result` 字段** — 优先返回简单扁平对象
