# 2026-07-22 Cron HR消息回复 — V2 实战记录

## 场景
Cronjob 定时检查BOSS直聘聊天页（`/web/geek/chat`），回复HR提问。

## 本次处理经过

### 发现的HR消息（按时间倒序）

| 时间 | HR/公司 | 内容 | 处理结果 |
|------|---------|------|----------|
| 15:20 | <HR>女士 - COMPANY_2 | 找短视频拍摄剪辑 | ⏭️ 跳过（纯短视频方向，排除规则） |
| **14:17** | **<HR>女士 - COMPANY_3** | "hello现在是离职状态吗？" | **✅ 已回复** |
| 13:31 | <HR>女士 - COMPANY_1 | MCN达人孵化 | ⏭️ 跳过（不相关） |
| 11:29 | <HR>女士 - COMPANY_4 | "请问在考虑新的工作机会吗？" | ⏭️ 未处理（每次只处理1条） |

### 回复内容
> 你好~ 目前是离职状态，可以随时到岗。我熟练使用PR、AE、达芬奇等剪辑工具，有丰富的视频剪辑和后期制作经验。这是我的作品集，百度网盘链接：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>，请查收~ 期待进一步沟通！

### 验证
`verify-message "目前是离职状态"` → verified: true，消息确认发送成功。

## 🔧 操作模式（Safari runner）

### 1. 导航到聊天页
```bash
python3 safari_boss_runner.py navigate "https://www.zhipin.com/web/geek/chat"
# 用 navigate 的 --wait 参数或单独 sleep
```

### 2. 读取页面内容（找HR消息）
```bash
python3 safari_boss_runner.py extract-detail
```
`extract-detail` 返回 `document.body.innerText` 的前5000字符，包含聊天列表所有对话预览。
对话列表按时间倒序排列。

**HR消息识别规则**：
- 我方消息标记：`[已读]` 或 `[送达]` 前缀
- HR消息标记：无前缀，显示 HR名 + 公司名 + 职位 + 时间
- 新消息出现在列表最上方，按时间倒序

### 3. 打开指定对话

React SPA 不响应 LI 元素的 `.click()`。需要找到目标HR的LI，然后点击其内部的 `.friend-content` 子元素。

**DOM结构**：
```html
<li role="listitem">
  <div data-v-3d67f5a8="" class="friend-content-warp">
    <div data-v-3d67f5a8="" d-c="62001" class="friend-content">
      <div class="text">
        <span class="name-text"><HR>女士</span>
        <span class="last-msg-text">hello现在是离职状态吗？</span>
      </div>
    </div>
  </div>
</li>
```

**点击脚本（Python + json_js）**：
```python
from safari_boss_runner import json_js

result = json_js('''
const items = document.querySelectorAll('ul li');
let target = null;
for (const item of items) {
  if ((item.innerText || '').includes('<HR>女士') && (item.innerText || '').includes('COMPANY_3')) {
    target = item;
    break;
  }
}
if (!target) return {found: false};
const friendContent = target.querySelector('.friend-content');
if (!friendContent) return {found: false};
friendContent.click();
return {found: true};
''')
```

### 4. 发送文字回复
```bash
python3 safari_boss_runner.py send-text "回复内容"
```
⚠️ `send-text` 已内置发送逻辑：JS填入文本 → JS触发Enter → pyautogui点击发送按钮。**不需要额外调用 `click-send`**，但调了也无害。

### 5. 验证发送
```bash
python3 safari_boss_runner.py verify-message "关键词"
```
返回 `verified: true` 即发送成功。

## 📋 回复规则

| HR提问类型 | 回复策略 |
|-----------|---------|
| 问离职状态 | "目前是离职状态，可以随时到岗。熟练使用PR、AE、达芬奇等剪辑工具" |
| 问技能/工具 | 强调PR、AE、达芬奇，**不提Final Cut Pro**（用户不会） |
| 问薪资 | 期望7000元/月 |
| 约面试 | 表达兴趣，不承诺具体时间，问清线上/线下 |
| 要作品集 | 发百度网盘链接+提取码 |
| 要附件简历 | 同意并发送YOUR_NAME.pdf |
| 无关广告（AI抽卡师、经纪人等） | 跳过不回复 |

**所有回复必须附带作品集链接**：
> 百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>

## ⚠️ 排除规则
- 纯短视频/抖音/快手方向 → 跳过
- AI抽卡师、经纪人等无关岗位 → 跳过
- MCN达人孵化 → 跳过
- 短剧、AIGC方向 → 最后考虑

## 💡 最佳实践（Cron模式）
1. 每次只处理最上面最新的1条未读消息
2. 处理完即停止，等下次触发
3. 如果在验证时发现消息还在输入框（没发送成功），重试 `send-text`
4. 如果打开对话后隐私协议弹出（首次聊天的新HR），先JS点击"确定"关闭对话框
