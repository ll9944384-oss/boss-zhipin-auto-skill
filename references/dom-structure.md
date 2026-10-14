# BOSS直聘 DOM 结构参考

> 从实际 Safari + AppleScript 自动化会话中提取的页面结构信息。
> 最后验证日期：2026-07-11

## 职位列表页 (`/web/geek/job?query=...&city=...`)

```
.job-card-wrap                     ← 每个职位的容器
  .job-info
    .job-title
      .job-name                   ← 职位名称 (也是链接 a[href])
    .tag-list
      li                          ← 经验要求、学历要求
  .job-card-footer
    .boss-info                    ← a[href] 公司链接
      .boss-name                  ← 公司名称
    .company-location             ← 地点 (如 "杭州·上城区·四季青")
```

**薪资字段**：`span.job-salary` 存在于 DOM 但**内容为空**。
BOSS 直聘不在此页面展示薪资，必须进入详情页。

**提取代码示例**：
```js
var cards = document.querySelectorAll('.job-card-wrap');
cards.forEach(function(c) {
    var title = c.querySelector('.job-name').innerText.trim();
    var href = c.querySelector('.job-name').getAttribute('href');
    var company = c.querySelector('.boss-name').innerText.trim();
    var location = c.querySelector('.company-location').innerText.trim();
    var tags = Array.from(c.querySelectorAll('.tag-list li'))
        .map(function(t) { return t.innerText.trim(); });
});
```

## 职位详情页 (`/job_detail/xxx.html`)

```
.job-salary                       ← 详情页有薪资文本（如 "11-13K"）
.job-sec-text                     ← JD 描述正文
.company-name                     ← 公司名
.btn-startchat (.btn.btn-startchat) ← "立即沟通" 按钮
```

**"立即沟通" 按钮**：
- 主要选择器：`.btn-startchat`、`.btn.btn-startchat`
- 已沟通过的职位按钮文本变为 "继续沟通"
- 找不到按钮的常见原因：登录丢失（检查导航栏是否有用户名）

## 聊天页面 (`/web/geek/chat`)

```
左侧对话列表：
  li [包含联系人信息]
    文本格式: "时间\n姓名+公司+角色\n[送达/已读]\n最新消息预览"

右侧聊天面板（职位详情页打开聊天时）：
  DIV.message-controls
    DIV.chat-im chat-editor
      DIV.chat-controls
        DIV.toolbar-btn-content
          DIV.toolbar-btn-content icon btn-sendimg too  ← 图片上传按钮
            input[type="file"][0]  ← 可见，accept=image/gif,jpeg,jpg,png
          ...其他toolbar按钮...
      DIV.chat-input               ← 文字输入区
      button.btn-send              ← 发送按钮（disabled 状态时文字为灰色）
```

**图片上传**：
- 可见的 `<input type="file">` 是第 0 个（共 3 个，另外 2 个不可见，用于简历上传）
- accept 属性：`image/gif,image/jpeg,image/jpg,image/png`
- JS `.click()` 无法触发原生文件对话框（浏览器安全限制）
- 父元素类名含 `btn-sendimg tool`

**输入框选择器**：
```js
document.querySelector('textarea, [contenteditable="true"], .ql-editor, .input-area, div.chat-input')
```

**发送按钮选择器**：
```js
// 扫描所有按钮找文本 "发送"
// 或: button:last-of-type, [class*="send"]
```

## 导航栏登录状态检测

```
导航栏右侧显示：
  - "YOUR_NAME" + "消息N" + "简历" → 已登录 ✅
  - "登录/注册" → 未登录 ❌（需用户手动重新登录）
```

检测代码：
```js
document.body.innerText.includes('YOUR_NAME')  // 或其他用户名
// 或 document.body.innerText.includes('登录/注册')
```

## 已知限制

1. **`do JavaScript` 返回值为空**：base64 编码的 AppleScript 文件方式返回常为空，
   内联 `osascript -e` 更可靠但对复杂 JS 转义困难
2. **VLM 不可用**：DeepSeek V4 不支持视觉，截图需用 OCR/页面文本代替
3. **图片上传需手动**：浏览器安全限制，推荐用户手动拖拽
4. **SPA 加载延迟**：每次导航后 `sleep(4)` 等待渲染