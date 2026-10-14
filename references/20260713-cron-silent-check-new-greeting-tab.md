# 2026-07-13 Cron Job Silent Check: 新招呼 Tab Discovery

## 场景

Cron job 检查 BOSS直聘聊天页面，寻找 HR 发来的新消息。此会话最终无未读消息，输出 `[SILENT]`。

## 关键验证

### 1. 三个标签页的差异

| 标签 | 返回内容 | 用途 |
|------|----------|------|
| **未读** | 仅有未读角标的对话 | 判断是否有**当前未读**的新消息。空 → "30天内暂无联系人" |
| **新招呼** | HR 曾主动发起首条消息的全部对话 | 查看所有 HR 主动联系过的对话历史（不论已读/未读） |
| **全部** | 所有对话（含我方发起的和系统通知） | 全量扫描，用于无未读角标时的后备方案 |

**2026-07-13 数据**：在"未读"标签页显示"30天内暂无联系人"时，"新招呼"标签页仍有 20+ 条对话，说明这些是历史 HR 招呼，已被阅读过。

### 2. Cron Job 消息判定流程（验证无误）

```
1. navigate → /web/geek/chat
2. 等待 3 秒（Vue SPA 渲染）
3. 点击"未读"标签 → 检查对话列表
   → 空（30天内暂无联系人）→ 当前无未读
4. 点击"新招呼"标签 → 扫描 HR 历史对话
   → 列表不为空，但均为已处理的旧消息
5. 点击"全部"标签 → body.innerText 扫描确认
   → 确认顶部最新对话为已处理的旧消息
6. 输出 [SILENT]
```

### 3. 对话预览文本判定

通过 `document.body.innerText` 扫描对话列表时，每个对话条目的文本格式为：

```
[时间]
[姓名][公司名][职位]
[消息预览]
```

**判定规则**：
- 预览含 `[送达]` / `[已读]` / `[图片]` → 我方最后发出，跳过
- 预览无标记 → 可能是 HR 消息，需检查内容
- 内容含"抖音短视频"/"经纪人"/"AI抽卡师"/"信息流" → 排除，跳过
- 内容含"后期制作"/"综艺后期包装"等匹配关键词 → 相关，需回复
- 内容为微信号/"复制微信号" → 微信交换已完成，跳过
- 内容为"您的附件简历 已发送"/"对方已同意" → 系统通知，跳过

### 4. 对话列表定位

对话列表中的 `<li>` 元素可用尺寸过滤：
- 宽度 ≈ 364px
- 高度 ≈ 78px
- 这是 Vue SPA 左侧对话列表的标准尺寸

```javascript
// 获取对话列表项
var items = Array.from(document.querySelectorAll('li'));
var conversations = items.filter(function(li) {
  var r = li.getBoundingClientRect();
  return Math.abs(r.width - 364) < 20 && Math.abs(r.height - 78) < 20;
});
```

### 5. safari_js() 优于 json_js()

当 `json_js()` 持续返回 `{"ok": true}` 无 `result` 字段时（即使 JS 代码有 return），改用手动 JSON 序列化：

```python
raw = safari_js("""
(function() {
  try {
    var result = ...;
    return JSON.stringify(result);
  } catch (err) {
    return JSON.stringify({error: String(err)});
  }
})()
""")
data = json.loads(raw)
```

### 6. [SILENT] 输出条件

输出 `[SILENT]` 的唯一条件：
- "未读"标签为空（"30天内暂无联系人"）
- "新招呼"标签中的对话均为已读旧消息
- "全部"标签扫描确认无 HR 发出的未回复消息
