# 2026-07-22 Cron 回复会话：dispatchEvent 后备方案验证

## 场景

Cron job 检查 BOSS 直聘聊天页，发现 `_PAGE.isLogin` 无法获取（SPA 会话标记可能过期），
Vue 组件 `.__vue__` 不可用。需要回退到 DOM 交互方式打开对话。

## 关键发现：dispatchEvent 有效打开 SPA 对话

当 Vue 组件不可用时，以下方法成功打开了 HR 对话：

```python
from scripts.safari_boss_runner import json_js
import time

result = json_js('''
const firstItem = document.querySelector('ul[role="group"] li[role="listitem"]');
if (firstItem) {
  const fc = firstItem.querySelector('.friend-content');
  if (fc) {
    fc.dispatchEvent(new MouseEvent('click', {
      bubbles: true, cancelable: true, view: window
    }));
    return {clicked: true, d_c: fc.getAttribute('d-c')};
  }
}
return {clicked: false};
''')
# 结果: {"clicked": true, "d_c": "62001"}
time.sleep(3)
```

### 后续聊天面板结构

点击后 `.chat-wrap` 包含两个子元素：
1. `.list-warp.v2` (368px) — 左侧对话列表
2. `.chat-conversation` (812px) — 右侧聊天面板（之前为空状态，点击后填充内容）

聊天面板文本：
```
<HR>女士
COMPANY_3
hr
更多
剪辑师
8-12K
杭州
查看职位
14:17
hello现在是离职状态吗？
发简历
换电话
换微信
按Enter键发送，按Ctrl+Enter键换行发送
```

关键确认：`document.querySelector('div[contenteditable="true"]')` 存在 → 成功打开对话。

## 对话列表 DOM 结构（确认）

```
DIV.chat-wrap
  DIV.list-warp.v2                  ← 左侧栏
    DIV.chat-user.v2  
      DIV.boss-search-top           ← 搜索框
      DIV.label-list                ← 筛选标签：全部/未读/新招呼/仅沟通/更多
        UL > LI.selected > SPAN.label-name "全部"
        UL > LI > SPAN.label-name "未读"
        UL > LI > SPAN.label-name "新招呼"
        UL > LI > SPAN.label-name "仅沟通"
        LI > DIV.ui-dropmenu-v1 "更多"
      DIV.chat-content
        DIV.user-list
          DIV.user-list-content
            UL[role="group"] (style="padding: 0px 0px 4680px;")
              LI[role="listitem"] (class="")
                DIV.friend-content-warp
                  DIV.friend-content[d-c="62001"]
                    DIV.figure > IMG
                    DIV.text
                      SPAN.time "14:17"
                      DIV.title-box
                        SPAN.name-box
                          SPAN.name-text "<HR>女士"
                          SPAN "COMPANY_3"
                          I.vline
                          SPAN "hr"
                      DIV.gray.last-msg
                        SPAN.last-msg-text "hello现在是离职状态吗？"
  DIV.chat-conversation             ← 右侧聊天面板（812px）
```

## 未读检测

**"未读"标签页**（点击后）：显示 "30天内暂无联系人" → 确实无未读角标
**"全部"标签页**：显示所有对话，含已回复和未回复的

重要：即使"未读"标签为空，"全部"标签下仍有需要回复的 HR 消息（消息已被点击过所以不算"未读"，但 HR 在等回复）。

## Cron 回复流程（已验证可工作）

```python
import time, json, sys
sys.path.insert(0, '/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto')
from scripts.safari_boss_runner import (
    json_js, send_text_value, try_click_send, verify_message_value
)

# 1. 导航到聊天页
import subprocess
subprocess.run([
    'python3', '-m', 'scripts.safari_boss_runner', 
    'navigate', 'https://www.zhipin.com/web/geek/chat', '--wait', '3.0'
])

# 2. 检查"全部"标签页对话列表
body_text = json_js("return (document.body.innerText || '').trim().slice(-10000);")

# 3. 分析文本找到 HR 消息（无 [送达]/[已读]/[图片] 标记的最近消息）
#    从顶部开始扫描，第一个 HR 消息即为最新

# 4. 用 dispatchEvent 打开对话
json_js('''
const firstItem = document.querySelector('ul[role="group"] li[role="listitem"]');
if (firstItem) {
  const fc = firstItem.querySelector('.friend-content');
  if (fc) fc.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
}
''')
time.sleep(3)

# 5. 读取对话内容
chat_text = json_js("""
const conv = document.querySelector('.chat-conversation');
return conv ? conv.innerText.slice(-5000) : '';
""")

# 6. 发送回复
reply = """回复内容"""
send_result = send_text_value(reply)
time.sleep(2)
send_click = try_click_send(pause=1.5)

# 7. 验证
verify = verify_message_value('百度网盘链接')
print(json.dumps(verify, ensure_ascii=False))
```

## send_text_value + click-send 双重保险有效

`sned_text_value()` 此会话中返回 `sent: true`（JS 填入+发送），
然后 `try_click_send()` 返回 `ok: true`（pyautogui 兜底）。

验证：`verify_message_value('百度网盘链接')` 返回 `verified: true`，
且对话文本中能看到回复消息已出现在聊天中。

## 本会话处理的 HR 消息

| HR | 公司 | 时间 | 内容 | 处理 |
|----|------|------|------|------|
| <HR>女士 | COMPANY_3 | 14:17 | "hello现在是离职状态吗？" | 回复：已离职在看机会，附作品集链接 |

## 其他 HR 消息状态

| HR | 类型 | 判定 |
|----|------|------|
| <HR>女士·COMPANY_1 (13:31) | MCN达人孵化 | 排除（无关岗位） |
| <HR>女士·COMPANY_4hr (11:29) | "请问在考虑新的工作机会吗？" | 需回复，等下轮触发 |
| <HR>女士·COMPANY_20招聘专员 (11:46) | 拒绝通知 | 无需回复 |
