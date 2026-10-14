# 2026-07-13 HR要简历回复场景 (14:00-14:40)

## 场景描述
HR<HR_NAME>（COMPANY_6猎头顾问）发送消息：
"为了后续更好的沟通，方便发一份你的简历过来吗？"

这是一个 **HR主动要附件简历** 的场景。规则：同意 + 发送附件简历（YOUR_NAME.pdf）+ 附作品集链接。

## 处理步骤

### 1. 导航到聊天页面
```python
python3 safari_boss_runner.py navigate "https://www.zhipin.com/web/geek/chat" --wait 3
```

### 2. 检查未读对话
初始检查：所有对话 `hasUnread: false`，`unreadCount: 0`。但从 `document.body.innerText` 扫描可见 <HR_NAME> 对话有 `[送达]` 状态的仅为我方消息。

**扫描方法**：用 `document.body.innerText` 提取全部对话文本，按格式解析：
- `[送达]` / `[已读]` + 前缀 → 我方最后发出的消息
- 无标记且非系统消息 → HR消息
- 系统通知（"您的附件简历已发送"、"对方已同意"）→ 跳过

### 3. 打开对话
```javascript
// 找到目标对话项
const items = document.querySelectorAll('.friend-content');
const target = Array.from(items).find(el => el.innerText.includes('<HR_NAME>'));
// 确保可见
target.scrollIntoView({block: 'center'});
// 触发 click（MouseEvent dispatch 有效）
target.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
// 等待 2-3 秒
```

验证 `chat_state_value().result.hasChatInput === true` 确认聊天窗已打开。

### 4. 发送回复文本
```python
# 方法一：send_text_value (内置 Enter + pyautogui)
from safari_boss_runner import send_text_value
send_text_value("好的，这是我的附件简历，请您查收...")

# 方法二：如果上述方法文本未发送（inputInfo[0].text 不为空）
# 手动 dispatch Enter 事件
```

### 5. 发送附件简历（YOUR_NAME.pdf）
- 找到"发简历"按钮：`.toolbar-btn-content`（文本"发简历"）
- 用 pyautogui 点击按钮位置
- 系统文件对话框弹出后：
  1. Cmd+Shift+G（前往文件夹）
  2. 粘贴路径 `/Users/YOUR_NAME/Desktop/YOUR_NAME.pdf`
  3. Enter（前往文件夹）
  4. Enter（选择文件）
  5. Enter（确认）
- **⚠️ 不可靠**：文件对话框在后台 Safari 窗口时交互复杂，成功率低

### 6. 验证发送成功
检查 `.text-content` 元素列表，确认回复文本出现在最新消息中。

## 遇到的坑

### 坐标不一致问题
safari_bounds() 返回的窗口尺寸与 JS 报告的 window dimensions 不一致：
- safari_bounds: `{left: 48, top: 39, width: 600, height: 757}`
- JS: `{screenX: 0, screenY: 38, outerWidth: 1430, outerHeight: 751}`
- **原因**：存在多个 Safari 窗口，safari_bounds 读取了非当前窗口的 bounds
- **解决**：优先使用 JS 报告的 screenX/screenY 计算物理点击坐标
  ```python
  chrome_top = outerHeight - innerHeight  # 80px
  screen_x = screenX + js_center_x
  screen_y = screenY + chrome_top + js_center_y
  ```

### send_text 未实际发送
- `send_text_value()` 返回 `sent: true` 但文本仍留在输入框中
- 需要额外 dispatch KeyboardEvent('keydown', {key: 'Enter'})
- 发送后检查 input 的 text 是否为空来确认

### 新消息在处理后出现
- 初始扫描无未读（全部为 0）
- 处理完<HR_NAME>后回到列表，出现 `未读(1)`（王玉博的新消息）
- 说明 BOSS 直聘的 WebSocket 推送可能延迟，需要每次处理完后重新检查

## 代码片段

### 获取屏幕坐标用于 pyautogui 点击
```python
from safari_boss_runner import json_js

js = '''
const items = document.querySelectorAll('.friend-content');
const target = Array.from(items).find(el => el.innerText.includes('目标HR名称'));
const r = target.getBoundingClientRect();
return {
  centerX: Math.round(r.left + r.width / 2),
  centerY: Math.round(r.top + r.height / 2),
  screenX: window.screenX,
  screenY: window.screenY,
  outerHeight: window.outerHeight,
  innerHeight: window.innerHeight
};
'''
info = json_js(js)['result']
chrome_top = info['outerHeight'] - info['innerHeight']
screen_x = info['screenX'] + info['centerX']
screen_y = info['screenY'] + chrome_top + info['centerY']
click_screen_point(screen_x, screen_y, pause=2)
```

### 手动 dispatch Enter 发送
```python
from safari_boss_runner import json_js
json_js('''
const input = document.querySelector('div[contenteditable="true"].chat-input');
if (input) {
  input.dispatchEvent(new KeyboardEvent('keydown', {
    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
    bubbles: true, cancelable: true
  }));
}
return 'sent';
''')
```

## 相关对话
- <HR_NAME>：HR要简历 → 同意 + 发作品集链接 + 尝试发附件简历
- 王玉博（下一轮需处理）："拍摄这边你擅长吗" — 询问拍摄技能
