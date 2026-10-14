# 2026-07-23 Cron 结构化对话提取案例

## 场景
Cron 定时检查 BOSS直聘聊天页面，提取所有对话并分类 HR 消息 vs 自动发送的消息。

## 提取方法

使用 `safari_js()` + 手动 `JSON.stringify` 替代 `json_js()`（因后者会在复杂返回值时丢失 `result` 字段）。

### 可靠的 CSS 选择器

```python
from safari_boss_runner import safari_js
import json

raw = safari_js("""
(function() {
  var items = document.querySelectorAll('.friend-content-warp');
  var convos = Array.from(items).slice(0, 30).map(function(el, idx) {
    var time = (el.querySelector('.time') || {}).innerText || '';
    var nameBox = (el.querySelector('.name-box') || {}).innerText || '';
    var nameText = (el.querySelector('.name-text') || {}).innerText || '';
    var lastMsg = (el.querySelector('.last-msg-text') || {}).innerText || '';
    return {
      idx: idx,
      time: time.trim(),
      nameBox: nameBox.trim(),
      nameText: nameText.trim(),
      lastMsg: lastMsg.trim()
    };
  });
  return JSON.stringify({convos: convos, count: convos.length});
})();
""")
result = json.loads(raw)
```

成功提取 40 条对话（2026-07-23 现场验证）。

### 消息分类规则（文本启发式）

| 类型 | 特征 | 示例 |
|------|------|------|
| **我方已发送** | 含 `[已读]` 或 `[送达]` 前缀 | `[送达]\n这是我的作品集...` |
| **HR主动发来** | 无前缀，直接显示时间+姓名+消息 | `昨天\n<HR>女士COMPANY_2招聘者\n你好...` |
| **系统拒绝** | 无前缀但含"不够匹配""不符合" | `感谢您的关注，感觉您的个人经验与我们招聘要求不太符合` |
| **图片消息** | lastMsg 仅为 `[图片]` | — |

### 按排除规则分类示例

2026-07-23 检查中共发现 40 条对话，其中 HR 主动发来的新消息（按页面排序从最新到最旧）：

| 时间 | 招聘方 | 消息摘要 | 分类 | 处理 |
|------|--------|----------|------|------|
| 昨天 | <HR>女士 COMPANY_2 招聘者 | 找短视频拍摄剪辑 | **排除**（纯短视频） | 跳过 |
| 昨天 | <HR>女士 COMPANY_1 招聘者 | MCN达人孵化 | **排除**（无关岗位） | 跳过 |
| 昨天 | <HR>女士 COMPANY_20 招聘专员 | 不匹配拒绝 | 系统拒绝 | 无需处理 |
| 昨天 | <HR_NAME> COMPANY_17 总监 | 对后期制作感兴趣 | **待回复** | 排队 |
| 07/21 | <HR>女士 COMPANY_7 HRBP | 要简历 | **需发附件简历** | 排队 |
| 07/21 | <HR>女士 快鸟先飞 人事 | 问剪映/PS技能 | **待回复** | 排队 |

### 每次只处理最上面1条

规则：`每次只处理最上面最新的1条未读消息，处理完就停止，等下次触发`

当前最上面的是被排除的，则跳过并报告，下次 cron 触发再处理下一条。
