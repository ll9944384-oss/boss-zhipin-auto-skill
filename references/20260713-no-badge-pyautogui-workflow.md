# 2026-07-13 Cron Job: 无未读角标场景 + pyautogui打开对话 + HR送微信号回复

## 场景概述

HR消息回复 cron job 执行。发现 BOSS直聘聊天列表无任何未读角标，但仍有大量HR消息需要回复。成功使用 pyautogui 物理点击打开对话（JS dispatchEvent 全部失效），回复了<HR>女士发来的微信号消息。

## 核心发现

### 1. 无未读角标（2026-07-13 首次验证）

40+条对话中 **0条有未读角标**。未读角标不应作为筛选条件。

**替代方案**：直接用 `document.body.innerText` 获取全部对话文本，根据消息预览前缀判断：

| 预览前缀 | 判定 |
|----------|------|
| `[送达]` / `[已读]` / `[图片]` | 我方最后发出的消息 |
| 无标记的纯文本 | 可能是HR发来的新消息 |
| `您的附件简历 已发送` / `对方已同意` | 系统通知 |

### 2. pyautogui 物理点击成功打开对话（JS dispatch 全部失效）

**失效方案**（Vue 虚拟滚动器忽略）：
- `el.click()`
- `dispatchEvent(new MouseEvent('click', ...))`
- `mousedown + mouseup + click` 三事件序列
- `PointerEvent` 合成事件

**成功方案**：`pyautogui.click(x, y)` 配合 Safari bounds 坐标映射

```python
from scripts.safari_boss_runner import safari_bounds, click_screen_point

bounds = safari_bounds()
# 假设 JS 返回的元素位置: {left: 123, top: 167, width: 364, height: 78}
# 目标对话在 Safari 窗口内（逻辑像素）

toolbar_top = max(bounds['height'] - 865, 70)
screen_x = int(bounds['left'] + 123 + 364 / 2)
screen_y = int(bounds['top'] + toolbar_top + 167 + 78 / 2)

result = click_screen_point(screen_x, screen_y, pause=1.5)
# 返回: {'ok': True, 'click': {'x': 305, 'y': 314}}
```

**关键**：`runner navigate` 已激活 Safari 为前台应用。pyautogui 直接发送点击到屏幕坐标，与前台应用无关。

### 3. 对话DOM位置批量获取

```python
from scripts.safari_boss_runner import json_js

items = json_js('''
var lis = document.querySelectorAll('li');
var list = [];
for (var i = 0; i < lis.length; i++) {
  var el = lis[i];
  var r = el.getBoundingClientRect();
  if (r.width > 300 && r.height > 30) {
    list.push({
      idx: i, w: Math.round(r.width), h: Math.round(r.height),
      left: Math.round(r.left), top: Math.round(r.top),
      text: (el.innerText || '').trim().slice(0, 100)
    });
  }
}
return list;
''')
```

过滤条件：`w > 300 && h > 30` 排除导航栏，只保留对话 `<li>`。

已知尺寸特征：每条对话元素 ≈ **364×78px**，位置 **left≈123**。

### 4. HR发微信号消息后的回复策略

**场景**：HR先发了微信交换请求卡片 → 用户之前已点击"同意" → 现在HR又单独发了微信号文本（"<WECHAT_ID>"）作为新消息。

**判定**：这不是系统通知，而是HR主动发的消息。需要友好回复。

**回复内容**：
- 确认已添加微信
- 附作品集链接
- 模板："好的，感谢！已添加您的微信，请通过一下～这是我的作品集，您也可以先看看：[作品集链接]"

**验证**：send-text + click-send 后，用 verify-message "已添加您的微信" 确认成功。

### 5. `sys.path.insert` 导入 runner

在 `python3 -c` 内调用 runner 函数：

```python
import sys
sys.path.insert(0, 'scripts')
from safari_boss_runner import json_js, safari_bounds, click_screen_point, chat_state_value
```

注意：`scripts/` 相对于技能目录 `/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/`。

### 6. 首次进入对话后读取消息内容

打开对话后（hasChatInput=true），用 `json_js` 读取右侧消息面板：

```python
result = json_js('''
var candidates = Array.from(document.querySelectorAll('div'))
  .filter(function(d) {
    var cls = d.className || '';
    var r = d.getBoundingClientRect();
    return r.width > 200 && r.height > 100 && /msg|message|dialog|chat-view/i.test(cls);
  });
return candidates.map(function(d) {
  return {
    cls: (d.className || '').slice(0, 80),
    w: Math.round(d.getBoundingClientRect().width),
    h: Math.round(d.getBoundingClientRect().height),
    text: (d.innerText || '').trim().slice(0, 500)
  };
}).slice(0, 5);
''')
```

查找 `class="chat-message"` 或 `class="message-content"` 的元素，读取 `innerText` 获得完整对话历史。

## 本次处理摘要

| 项目 | 内容 |
|------|------|
| 处理对象 | <HR>女士（AN日式美甲美睫美肌/杭州萧山王波美甲） |
| 最新消息 | 微信号 <WECHAT_ID> |
| 回复 | "好的，感谢！已添加您的微信..." + 作品集链接 |
| 验证方式 | verify-message "已添加您的微信" → verified:true |
| 其他未处理 | <HR_NAME>（抖音短视频→排除）、<HR>女士（拍剪为主→待下次）、<HR>女士（喜予文化后期→待下次）等 |
