# Cron Job: 聊天消息检查参考

## 页面结构实测数据（2026-07-12）

BOSS直聘聊天页（`/web/geek/chat`）是 Vue SPA，实测 DOM 结构如下：

### 对话列表项定位

使用 `document.querySelectorAll("li")` + 尺寸过滤即可可靠找到对话项：

| 属性 | 数值 |
|------|------|
| 对话列表项宽度 | ~364px |
| 对话列表项高度 | ~78px |
| left 偏移 | ~123px |
| top 从 ~167px 开始，每项间隔 ~78px |

注意区分「用户头像/导航栏 `<li>`」（宽高约 49-57px）和「对话列表 `<li>`」（宽 364px）。

### 消息文本格式

每条对话 `<li>` 的 `innerText` 格式：

```
[未读数]
[时间]
[姓名][公司名][职位]
[最后消息预览]
```

示例：
```
1
20:10
<HR_NAME>COMPANY_5经理
你好，我们急招抖音短视频拍剪，如有兴趣希望可以深聊
```

- 未读消息左侧会有一个 "1" 作为数字角标（在 text 的最开头）
- 筛选控件有"未读(2)"、"全部"等 tab 按钮，也是 `<li>` 或文本元素

### 消息标记解读

| 文本前缀 | 含义 |
|----------|------|
| `[送达]` | 我方消息已送达，非 HR 消息 |
| `[已读]` | 我方消息已被 HR 阅读，非 HR 消息 |
| `[图片]` | 我方发送的图片 |
| 无标记 + 姓名+公司 | 可能是 HR 发来的新消息 |

### 系统通知识别

格式如「您的附件简历 YOUR_NAME_20... 已发送给Boss点击查看附件」或「对方已同意，您的附件简历已发送给对方」→ 跳过，非 HR 提问。

### JS 提取代码（已测试可用）

```javascript
// 简单可靠：获取所有可见 li 项
var items = document.querySelectorAll("li");
var list = [];
for (var i = 0; i < items.length; i++) {
  var el = items[i];
  var r = el.getBoundingClientRect();
  if (r.width > 50 && r.height > 20) {
    var text = (el.innerText || "").trim().slice(0, 100);
    if (text) {
      list.push({idx: i, text: text, w: Math.round(r.width), h: Math.round(r.height), left: Math.round(r.left), top: Math.round(r.top)});
      if (list.length >= 15) break;
    }
  }
}
return list;
```

## 场景判定速查

| 消息预览文本特征 | 判定 | 操作 |
|---|---|---|
| 含「抖音」「短视频」「快手」 | 排除方向 | 跳过 |
| 含「附件简历已发送」「已发送给Boss」 | 系统通知 | 跳过 |
| 含「AI抽卡师」「经纪人」「COMPANY_14」+无关岗位 | 无关岗位 | 跳过 |
| HR 主动提问（含「?」「吗」「方便」「会」「薪资」） | 需要回复 | 按规则回复 |
| HR 说「发一份简历」 | 要求简历 | 发送附件简历 |
