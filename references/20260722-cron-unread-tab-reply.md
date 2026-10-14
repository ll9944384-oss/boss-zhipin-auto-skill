# 2026-07-22 Cron Job: 未读标签筛选 + 海外素材剪辑师回复

## 场景

Cron job 定时检查 BOSS直聘聊天页面（`/web/geek/chat`），发现 1 条未读消息，识别并回复。

## 关键发现

### 1. "未读" 标签筛选简化流程

代替全文扫描的复杂方法，可以直接点击"未读(1)"标签筛选对话列表：

```javascript
const labels = document.querySelectorAll('.label-list a, .label-list span, .label-list li');
const unread = Array.from(labels).find(l => /未读/.test(l.innerText || l.textContent));
if (unread) unread.click();
```

筛选后 `.chat-content` 仅显示未读对话，大幅简化内容分析。

### 2. 单 `.click()` 可打开对话（无需三事件序列）

本会话中，`document.querySelector('.friend-content').click()` 就成功打开了对话——**不需要 mousedown+mouseup+click 三事件序列**。

前提条件：虚拟滚动器未激活（对话数量较少时）。如果对话数量多（200+），虚拟滚动器激活后合成事件仍可能被忽略。

**推荐尝试顺序**：
1. 先试普通 `.click()`（最简单）
2. 无效再试 mousedown+mouseup+click 三事件序列
3. 仍无效则回退 pyautogui 物理点击

### 3. `send-text` 一次调用即可发送

本会话中，`send_text_value(msg)` 一次调用直接发送成功——消息出现在对话中，无需额外 `click-send`。

验证方式：发送后检查 `chat_state_value().result.hasChatInput`（应为 true，且 inputInfo[0].text 应为空表示已发送）。

### 4. 未读清空验证

发送后检查 `nav-chat-num` 角标元素是否存在：

```python
from scripts.safari_boss_runner import json_js
js = r'''
const badges = Array.from(document.querySelectorAll('.nav-chat-num, [class*="unread"], [class*="badge"]'));
return badges.filter(b => b.offsetParent !== null).map(b => b.innerText || b.textContent);
'''
result = json_js(js)
# 空数组 = 无未读
```

### 5. DOM 结构确认

聊天列表结构（2026-07-22 确认）：
- 左侧列表容器：`.user-list` → `.user-list-content` → `ul > li`
- 每项对话：`li > .friend-content-warp > .friend-content`（`d-c="62001"` 固定属性）
- 筛选标签容器：`.label-list`
- 对话文本：`.text` 子元素
- 未读角标：`.figure > .notice-badge` 文字"1"

### 6. 本次回复的HR消息

| 发送者 | 时间 | 消息 | 岗位 | 判定 |
|--------|------|------|------|------|
| <HR>女士·COMPANY_19·HR | 07月20日 | "你好，我们正在诚聘海外素材剪辑师，有兴趣聊聊吗" | 海外素材剪辑师（8-12K·14薪） | ✅ 相关岗位，HR提问，需回复 |

已发送回复含技能介绍（PR、AE、达芬奇）+ 作品集链接。
