# 2026-07-22 Session: Runner 修复 & 完整投递流程

## 核心问题: JS 事件不触发 React SPA 发送

BOSS直聘聊天页面的"发送"按钮由 React 控制。`element.dispatchEvent(KeyboardEvent)` 和 `element.click()` 均不能触发 React 的合成事件绑定。文字可填入输入框但不会真正发送。

**解决方案**: 用 JS 找到发送按钮在 viewport 中的坐标，再用 `pyautogui` 在屏幕坐标上执行物理点击。

---

## Runner 修改清单

### 1. CONTACT_BUTTON_JS 评分修复
- **症状**: "感兴趣"和"立即沟通"按钮原始得分相同(239.325)，"感兴趣"在 DOM 中排前，pyautogui 优先点击"感兴趣"而非"立即沟通"
- **修复**: 在评分函数中增加 `if (/^(立即沟通|继续沟通)$/.test(text)) score += 300;`
- **效果**: "立即沟通"得分 539.325 >> "感兴趣" 239.325

### 2. 新增 FIND_SEND_BUTTON_JS
- 动态查找页面上最小的可见"发送"按钮
- 排除 disabled、包含 "disable"/"subscribe" class 的元素
- 返回按钮在 viewport 中的 rect + 屏幕信息

### 3. 新增函数
| 函数 | 说明 |
|------|------|
| `find_send_button_screen_coord()` | 用 FIND_SEND_BUTTON_JS 找到按钮，调用 screen_click_points 计算屏幕坐标 |
| `try_click_send(pause)` | 调用 find_send_button_screen_coord → pyautogui.click |
| `cmd_click_send` | click-send 命令行入口 |

### 4. send_text_value 改造
原函数只做 JS 填充和 JS 点击。改造后在返回前自动调用 `try_click_send()` 用 pyautogui 补点发送按钮。结果中增加 `pyautogui_send_click` 字段。

### 5. cmd_send_bundle 改造
在 send_text 后检查 page state：如果仍在初始 textarea（hasChatControls=false），自动 navigate 到聊天页再继续上传图片和验证。

### 6. 新增 click-send 命令
独立命令，可在 send-text 之后调用确保发送。
```bash
runner.py click-send
```

---

## 完整投递流程（新公司）

### 第一步: 打招呼 + 作品集
```
navigate job_detail_url → click-chat → 
send-text '您好...百度网盘链接...' → 
[pyautogui_send_click 自动触发]
```

### 第二步: 进入聊天页发图片
```
navigate /web/geek/chat → 
查找公司名 → pyautogui.click 列表项 →
upload-image resume.jpg
```

### 第三步: 发作品集链接
```
send-text '这是我的作品集...请查收~' →
click-send
```

---

## 聊天列表点击

聊天页左侧列表是 SPA 渲染，JS click() 不触发 React 路由切换。

**方案**: 用 JS 找到包含目标公司名的 div，获取其 viewport rect，用 pyautogui 在屏幕坐标点击。

```python
js = '''(function() {
  const found = Array.from(document.querySelectorAll('div')).filter(el => {
    const r = el.getBoundingClientRect();
    return r.width > 200 && r.height > 30 && r.width < 500 
      && (el.innerText||'').includes('公司名');
  });
  found.sort((a,b) => (a.rect.w*a.rect.h) - (b.rect.w*b.rect.h));
  const r = found[0].getBoundingClientRect();
  return {found: true, l: r.left, t: r.top, w: r.width, h: r.height};
})()'''
# 用 safari_bounds 计算屏幕坐标 → pyautogui.click
```

---

## HR消息自动回复

### 处理规则
1. HR主动要附件简历 → 点击"同意"按钮 → 选择第一个 PDF → 点击对话框"发送"
2. HR提问/邀请面试 → 友好回复 + 作品集链接
3. 无关广告（AI抽卡师、经纪人等）→ 跳过

### 同意发送简历
```python
# 找到"同意"按钮位置
js = '''Array.from(document.querySelectorAll('span,div,button'))
  .filter(el => (el.innerText||'').trim()==='同意' 
    && el.getBoundingClientRect().width > 20 
    && el.getBoundingClientRect().height > 15)'''
# pyautogui.click → 弹出文件选择对话框 → 
# 点击第一个 .pdf 文件 → 点击对话框"发送"按钮
```

### 附件简历对话框
点击"同意"后会弹出对话框显示已上传的 PDF 列表。对话框的"发送"按钮在 viewport 坐标约 (928, 565)，不是主页面的发送按钮 (1256, 811)。
