# 2026-07-13 Cron Job: JS Dispatch 成功打开对话 + 分类逻辑修正

## 场景

Cron job 检查 BOSS直聘聊天页面，处理HR主动发来的消息。成功回复了<HR>先生（COMPANY_16·动画剪辑·合肥办公）的邀请消息。

## 核心发现

### 1. JS dispatch 可打开对话（2026-07-13 验证）

**之前认为**（2026-07-12）：Vue 虚拟滚动器（`vue-virtual-scroller`）忽略所有 JS 合成事件，只有 pyautogui 物理点击可靠。

**本次验证**：JS dispatch 三事件序列 **成功打开了对话**（`hasChatInput: True`），优先级应排在 pyautogui 之前。

**推荐方案**（先 JS dispatch，失败再 pyautogui）：

```python
# 方案1：JS dispatch（优先）
js = r'''
(function() {
  var items = document.querySelectorAll('.friend-content');
  if (items.length > 0) {
    var target = items[%d];  // 索引或按位置匹配
    var r = target.getBoundingClientRect();
    ['mousedown', 'mouseup', 'click'].forEach(function(type) {
      target.dispatchEvent(new MouseEvent(type, {
        bubbles: true, cancelable: true, view: window,
        clientX: r.left + r.width/2, clientY: r.top + r.height/2
      }));
    });
    return {method: 'js_dispatch', found: true};
  }
  return {method: 'js_dispatch', found: false};
})()
'''

# 方案2：pyautogui 物理点击（备用）
from scripts.safari_boss_runner import safari_bounds, click_screen_point
bounds = safari_bounds()
inner_h = json_js("return {innerHeight: window.innerHeight}").result.innerHeight
toolbar_top = max(bounds['height'] - inner_h, 70)
screen_x = bounds['left'] + left + w/2
screen_y = bounds['top'] + toolbar_top + top + h/2
click_screen_point(screen_x, screen_y, pause=3.0)
```

### 2. 对话分类逻辑修正

**错误做法**：用 `extract_hr_message()` 提取最后一行对话文本，然后检查是否包含 `[送达]`/`[已读]`。

**问题**：对话 `<li>` 的 `innerText` 格式：
```
[送达]
这是我的作品集，百度网盘链接：...，请查收~
```
最后一行是 "这是我的作品集..."，不含 `[送达]` 前缀，导致被误判为 HR 消息（`reply`）。

**正确做法**：检查完整 `conv.text`（即 `<li>.innerText`）的**第一行**：
```python
first_line = conv_text.split('\n')[0].strip()
if first_line.startswith("[送达]") or first_line.startswith("[已读]") or first_line.startswith("[图片]"):
    return "our_message"
```

也检查 `[送达]`/`[已读]` 是否出现在文本任意位置（某些页面布局可能将标记嵌在中间）：
```python
if "[送达]" in text or "[已读]" in text:
    return "our_message"
```

### 3. 无未读角标场景确认

40+条对话中 0 条有未读角标（红色数字/红点）。验证了 2026-07-12 的发现：**未读角标不应作为筛选条件**。

**替代方案**：直接用 `document.body.innerText` 或 `querySelectorAll('li')` 尺寸过滤扫描全部对话，按预览文本前缀判断。

### 4. 聊天列表转换流程（简化版）

```
1. navigate → /web/geek/chat
2. sleep 3-4s (Vue SPA 渲染)
3. querySelectorAll('li') + 尺寸过滤 (w>300, h>30)
4. 遍历对话列表，对每条 conv.text 分类：
   a. 首行 [送达]/[已读]/[图片] → our_message (我方最后发出)
   b. 含系统通知关键词 → system_skip
   c. 含排除关键词(抖音/经纪人/AI抽卡师等) → excluded
   d. 含微信号+冒号 → wechat_skip
   e. 含提问/面试关键词 → reply (需要回复)
   f. 含"发一份简历" → send_resume
5. 找到第一个 reply/send_resume 对话：
   a. JS dispatch (mousedown+mouseup+click on .friend-content)
   b. 等待 2-3s
   c. 检查 hasChatInput
   d. 若失败 → pyautogui 物理点击
6. send_text_value(回复) → try_click_send() 确认
7. 处理完 1 条即停止
```

### 5. 回复模板速查

| HR消息特征 | 回复要点 |
|-----------|---------|
| 动画剪辑/合肥办公 | 表达兴趣 + 问是否支持远程/杭州办公 + 作品集 |
| 拍摄剪辑/女装工装 | 有经验 + 作品集 |
| 邀请面试 | 感谢 + 确认时间 + 作品集 |
| 问技能(会达芬奇?) | 会 + 具体技能 + 作品集 |
| 问薪资 | 7000元/月 + 作品集 |
| 要作品集 | 直接发链接+提取码 |
| 要简历 | 好的，已发送 + 作品集 |
| 猎头/泛邀请 | 简介自己 + 薪资期望 + 作品集 |

### 6. 已处理消息摘要

| 项目 | 内容 |
|------|------|
| HR | <HR>先生·COMPANY_16·动画剪辑（合肥办公） |
| 消息 | "你好，我们正在诚聘动画剪辑（合肥办公），有兴趣聊聊吗" |
| 回复 | 表达兴趣 + 问远程/杭州办公可行性 + 作品集链接 |
| 打开方式 | JS dispatch (mousedown+mouseup+click) ✅ |
| 发送方式 | send_text_value + try_click_send ✅ |
| 验证 | 页面确认包含作品集链接 ✅ |
