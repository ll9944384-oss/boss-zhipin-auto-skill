# 2026-07-22 Cron Job: 群发广告跳过 + AppleScript Bridge 稳定性

## 会话概述

Cron job 定时检查 BOSS直聘聊天页面。发现2条未读消息，顶部未读为<HR_NAME>（COMPANY_8）的群发广告。按规则跳过，未回复。

## 群发广告识别模式

**来源**：<HR_NAME> - COMPANY_8招聘者（15:36）
**消息原文**：
> 无责保底 6-10k！ 提供酒店式住宿+保姆级陪跑！宝子不来看看吗？

**判定依据**：
- 无具体职位名称（没说招剪辑/后期/编导等）
- 无技能要求（没说会PR/AE/达芬奇等）
- 话术极度泛化：「无责保底」「酒店式住宿」「保姆级陪跑」「宝子」
- 典型的直播主播/带货/达人孵化类招募话术
- 完全群发广播风格，非定向招聘

**结论**：属于「群发广告/无关岗位」，按规则跳过不回复。

## AppleScript Bridge 稳定性问题

### 现象
点击对话（JS dispatch click on `.friend-content`）后，下次调用 `json_js()` 或 `safari_js()` 报错：
```
RuntimeError: safari_boss_bridge.applescript: execution error: 变量"jsResult"没有定义。 (-2753)
```

### 原因
Vue SPA 切换对话时会卸载/重装 DOM。AppleScript bridge 的 JS 执行上下文依赖于 DOM 中的特定元素——DOM 重建后，bridge 注入的全局变量 `jsResult` 丢失。

### 恢复方法
重新 `navigate` 到聊天页即可恢复 bridge：
```python
from safari_boss_runner import json_js
# 或者直接调用 runner 命令
# `runner navigate "https://www.zhipin.com/web/geek/chat" --wait 3.0`
```

### 减轻策略
在 cron job 流程中，所有对话操作（点击、读取）之间不要依赖 bridge 的持续稳定性。每次需要执行 JS 前，如果前一步做了 DOM 修改操作（点击对话、点击按钮、提交表单），先重新 navigate 再执行 JS。
