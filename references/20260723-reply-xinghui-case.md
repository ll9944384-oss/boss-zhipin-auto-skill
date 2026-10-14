# 2026-07-23 回复案例：<HR>女士COMPANY_4hr

## 场景

- **HR**：<HR>女士 · COMPANY_4 · hr
- **职位**：医美案例拍摄剪辑师（8-13K，杭州）
- **HR 消息**（昨天 11:29）："请问在考虑新的工作机会吗？"
- **状态**：第一轮接触，此前未回复

## 处理流程

### 1. 发现目标对话

通过 `document.body.innerText` 解析对话列表，定位到：

```
昨天
<HR>女士COMPANY_4hr
请问在考虑新的工作机会吗？
```

特征：无 `[已读]`/`[送达]` 前缀 → 最后一条消息是HR主动发出的，未回复。

### 2. 排除判断

- ✅ 不是纯短视频/抖音/快手方向
- ✅ 不是AI抽卡师/经纪人等无关岗位
- ✅ HR在主动提问（不是群发广告）
- ✅ 职位是视频拍摄剪辑，相关岗位

### 3. 打开对话 — dispatchEvent 方式

用 `dispatchEvent(new MouseEvent('click'))` 在 `.friend-content[d-c]` 元素上触发：

```javascript
var lis = document.querySelectorAll('ul > li');
var target = lis[31];  // index 31/40+ 条对话
var content = target.querySelector('.friend-content, [d-c]');
if (content) {
  var event = new MouseEvent('click', {
    bubbles: true, cancelable: true, view: window
  });
  content.dispatchEvent(event);
}
```

**验证**：`chat_state_value().result.hasChatInput === true` ✅

> **注意**：对话列表 `<li>` 的索引会随新对话插入而变化，切勿硬编码。可用 `.innerText.includes('关键词')` 定位。

### 4. 发送回复

```python
from safari_boss_runner import send_text_value, try_click_send

reply = '''你好~ 目前正在看新的机会。我熟练使用PR、AE、达芬奇等软件，有丰富的视频剪辑和后期制作经验，期望薪资7000元/月。这是我的作品集，您有空可以看一下：
百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>
期待您的进一步沟通！'''

result = send_text_value(reply)
# result.sent === true
send_result = try_click_send(pause=1.5)  # 保底
```

### 5. 验证

读取对话面板确认回复已出现：

```javascript
var wrap = document.querySelector('.chat-wrap');
var detail = wrap.children[1];
detail.innerText  // 包含刚发送的文字
```

**对话记录**：
```
<HR>女士 · COMPANY_4 · hr
医美案例拍摄剪辑师 8-13K 杭州

昨天 11:29
请问在考虑新的工作机会吗？

[我们的回复]
你好~ 目前正在看新的机会。我熟练使用PR、AE、达芬奇等软件...
百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>
期待您的进一步沟通！
```

## 关键经验

| 步骤 | 方法 | 是否可用 |
|------|------|---------|
| 打开对话 | `Element.click()` 在 `.friend-content[d-c]` | ✅ 可用（本次未测试，但此前已验证） |
| 打开对话 | `dispatchEvent(new MouseEvent('click'))` | ✅ **本次确认可用** |
| 打开对话 | `pyautogui.click(x, y)` | ❌ 无效（Vue SPA事件绑定） |
| **打开对话** | **对话已在右侧面板打开（无需点击）** | ✅ **2026-07-23 第二次cron确认**：当cron触发时，如果上次cron或用户操作已将目标对话选中在右侧面板，`hasChatInput === true` 可直接回复，无需任何点击操作 |
| 发送消息 | `send_text_value(text)` | ✅ 返回 `sent: true`，消息发出 |
| 保底发送 | `try_click_send()` | ✅ 作为 fallback 调用。**注意**：若 `send-text` 已成功发送，`click-send` 会返回 `send_button_not_found`（发送按钮消失），这是**正常行为** —— 用 `verify_message_value()` 验证即可 |
| 验证发送 | 读取 `.chat-wrap > div:last-child` | ✅ 文本包含回复内容 |

## 未回复的其他HR（本轮跳过，等下次cron）

| HR | 排除原因 |
|----|---------|
| <HR>女士·COMPANY_2 | 短视频拍摄剪辑 → 排除（纯短视频方向） |
| <HR>女士·COMPANY_1 | MCN达人孵化 → 排除（无关岗位） |
| <HR_NAME>·COMPANY_17总监 | [已读] 后回复 "对后期制作感兴趣" → 留待下次 |
| <HR_NAME>·COMPANY_18总经理 | 短剧相关提问 → 最后考虑 |
