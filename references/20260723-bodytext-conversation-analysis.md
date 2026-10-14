# 2026-07-23 Session: Body-Text Conversation List Analysis

## 场景
Cron job 定时检查 BOSS直聘聊天页，通过读取 `document.body.innerText` 分析对话列表，识别未读HR消息。此方法比 DOM 选择器更可靠，因为 BOSS 直聘的 React/Vue SPA 动态渲染让传统 DOM 查询经常返回空结果。

## 核心发现

### 1. 对话列表在 body.innerText 中的结构

导航到 `https://www.zhipin.com/web/geek/chat` 后等待 3-4 秒，`document.body.innerText` 中包含聊天页所有可见文本。列表区域位于 "全部" 和 "滚动加载更多" 之间：

```
全部
未读(N)
新招呼
仅沟通
更多

15:39
<HR>女士星河智耀行政主管
[送达]
这是我的作品集...

15:36
<HR>女士明全文化人力主管
[送达]
这是我的作品集...

1
13:38
<HR>女士COMPANY_9人事
非常感谢您的应聘...

(更多条目...)
滚动加载更多
```

### 2. 解析技巧

```python
body = document.body.innerText
idx1 = body.index('全部')
idx2 = body.index('滚动加载更多')
list_area = body[idx1:idx2]
```

每条对话的格式：
```
时间
联系人公司职位
[送达/已读/无标记]
消息内容
```

### 3. 判断消息来源和状态的规则

| 体 文本中的标记 | 含义 | 是否需要处理 |
|------|------|------|
| `[送达]` 在对话预览中 | 最新消息是我们发出的，已送达HR | ❌ 不用处理 |
| `[已读]` 在对话预览中 | 最新消息是我们发出的，HR已读 | ❌ 不用处理 |
| **无 `[送达]`/`[已读]` 标记** | **最新消息是HR发来的** | ✅ 需要处理 |
| `[草稿]` | 我们的草稿消息 | ❌ 不用处理 |
| `[图片]` | 消息是图片 | 视上下文判断 |

### 4. 对话列表排序

- 按时间倒序，最新在顶部
- 未读对话会显示在顶部区域（优先在"未读(N)"标签页下）
- `未读(N)` 中的 N 是未读对话数
- **重要**：对话预览文本会动态更新为对话中最后一条消息的内容（无论谁发的）

### 5. 页面稳定性问题

**页面会自发跳转到职位详情页**：在执行 JS 导航或交互后，页面 URL 可能从 `/web/geek/chat` 变为 `/job_detail/xxx.html`。所有交互后必须验证当前 URL：

```python
js = 'return {url: location.href, pathname: location.pathname};'
result = json_js(js)
assert result['result']['pathname'] == '/web/geek/chat', f"Not on chat page: {result}"
```

如果页面跳走了，重新导航：
```python
window.location.href = 'https://www.zhipin.com/web/geek/chat';
```

### 6. 可靠的状态验证

用 `chat_state_value()` (来自 `safari_boss_runner`) 验证聊天页状态：

```python
state = chat_state_value()
# 确认在聊天页
assert state['result']['isChatPage'] == True
# 确认有输入框（已打开某个对话）
assert state['result']['hasChatInput'] == True
```

### 7. HR消息分类规则（Cron模式）

当从 body text 中找到未读HR消息后，按以下优先级分类：

#### 情况A：群发广告/无关岗位 → 跳过
识别特征：
- 语言模式：`无责保底` + `酒店式住宿/保姆级陪跑` — 自媒体/经纪人类招聘
- `MCN达人孵化`、`颜值美拍` — 达人经纪方向
- `AI抽卡师`、`经纪人` — 明确排除
- 关键词：`自媒体`、`达人`、`孵化` — 短视频方向

#### 情况B：短视频/抖音/快手方向 → 跳过
- 职位或消息中包含 `短视频`、`抖音`、`快手`、`信息流`、`口播`、`直播切片`

#### 情况C：HR提问/约面试 → 友好回复 + 附作品集
回复模板见 SKILL.md 阶段四 AI分析HR消息并生成回复。

#### 情况D：HR拒绝 → 不回复
- `不匹配`、`不符合`、`不合适` 等

### 8. 对话列表的纯文本提取示例 (Python)

```python
def parse_conversation_list(body_text):
    """从 body.innerText 解析对话列表，返回未读HR消息"""
    try:
        start = body_text.index('全部')
        end = body_text.index('滚动加载更多')
    except ValueError:
        return []
    
    area = body_text[start:end]
    lines = area.split('\n')
    
    conversations = []
    current = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 检测时间模式（如 "15:39" 或 "昨天" 或 "07月21日"）
        if re.match(r'^\d{1,2}:\d{2}$', line) or line in ('昨天',) or re.match(r'^\d{2}月\d{2}日$', line):
            if current.get('time'):
                conversations.append(current)
            current = {'time': line}
        elif '[' in line and ']' in line:
            current['status'] = line
        elif current.get('time') and 'time' in current:
            if 'name' not in current:
                # 包含联系人和职位信息
                current['name'] = line
            else:
                current['message'] = line
    
    if current.get('time'):
        conversations.append(current)
    
    # 筛选未读（无 [已读] 或 [送达] 标记）
    unread = [c for c in conversations if not c.get('status') in ('[已读]', '[送达]')]
    return unread
```

注意：上述简化版解析可能因为 BOSS 直聘的格式变化而失效。推荐直接用 `body.includes('关键词')` 做关键词匹配，比精确解析更可靠。
