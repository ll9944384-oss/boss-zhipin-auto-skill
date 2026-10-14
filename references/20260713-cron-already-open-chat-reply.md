# 2026-07-13 Cron Job: 已有打开对话中回复HR

## 场景

Cron job 触发时，聊天页面已停留在某个对话中（上一次手动操作或cron运行留下的打开状态），不需要点击左侧对话列表。

## 与参考文档的区别

| 维度 | 此场景 | 20260713-hr-ask-resume-worked-example |
|------|--------|--------------------------------------|
| 对话状态 | 已打开 | 需从列表点击 |
| 前置步骤 | 无 | navigate → click conversation |
| 消息读取 | `.message-item` 直接扫描 | 同上 |
| 回复方式 | 相同：send-text + click-send | 相同 |

## 执行步骤

### 1. 确认聊天状态

```python
from safari_boss_runner import chat_state_value
state = chat_state_value()
# 期望: isChatPage=True, hasChatInput=True
```

### 2. 读取当前对话的全部消息

```python
from safari_boss_runner import json_js
msgs = json_js(r'''
  const items = document.querySelectorAll('.message-item');
  return Array.from(items).map(el => {
    const text = (el.innerText || '').trim().slice(0, 300);
    const cls = (el.className || '').slice(0, 60);
    const isSelf = cls.includes('item-myself');
    return {isSelf, text: text.slice(0, 200)};
  });
''')
```

- `isSelf: false` = HR 消息
- `isSelf: true` = 我方消息
- 取最后一个 `isSelf: false` 的消息 = 最新 HR 消息

### 3. 判断规则

| HR消息内容 | 规则 | 行动 |
|-----------|------|------|
| 要简历 | #1 | 同意 + 作品集链接 |
| 提问（面试/技能/薪资） | #2 | 友好回复 + 作品集链接 |
| 广告（AI抽卡师/经纪人） | #3 | 跳过不回复 |
| 短剧/AIGC方向 | #4 | 最后考虑，但用户已主动回复过的继续 |

### 4. 回复

```bash
python3 safari_boss_runner.py send-text "【回复内容，含作品集链接】"
python3 safari_boss_runner.py click-send     # 保险冗余点击
```

**注意**：`send-text` 内部已包含 JS Enter 提交 + pyautogui 点击发送按钮的 fallback 逻辑。额外 `click-send` 作为双重保险，非必需。

### 5. 验证

```bash
python3 safari_boss_runner.py verify-message "回复内容的前几个字"
```

## 常见问题

### Q: send-text 成功但消息未出现在对话中？
A: 等待 1-2 秒后重新 verify。如果仍失败，检查 pyautogui 是否有权限（macOS 辅助功能权限）。

### Q: 如何判断对话是否已打开？
A: `chat_state_value().result.hasChatInput == true` 且当前在 `/web/geek/chat` 路径。

### Q: 简历文件发送失败？
A: BOSS直聘网页版「发简历」按钮绑定在Vue深层闭包中，JS dispatch 和 pyautogui 物理点击均无法触发。文字回复 "好的，这是我的简历" + 作品集链接 是目前可行的自动化方案。实际PDF附件发送需用户手动操作或通过BOSS直聘App。
