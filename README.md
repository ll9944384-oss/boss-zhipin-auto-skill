# boss-zhipin-auto

一个给 AI Agent（Hermes / Codex 等）用的 **BOSS 直聘自动投递技能包**：自动搜索职位 → 分析 JD 生成个性化招呼语 → 按「图片简历 → 作品集链接 → 招呼语」的顺序投递 → 监听并智能回复 HR 消息。

> ⚠️ **这是脱敏后的模板版本。** 原作者的个人信息（姓名、简历路径、网盘分享链接、HR 与公司名、BOSS 页面 token）已全部替换成占位符，**脚本直接跑会失败**，必须先把下面的占位符换成你自己的值。

---

## 目录结构

```
SKILL.md            # 技能主文件：完整工作流、话术规则、坑位清单
config.json         # 求职者画像 / 搜索参数 / 平台配置 / 招呼语规则
scripts/            # runner 脚本：Safari、Chrome/Edge、cron 巡检、投递调度
references/         # 实战沉淀：DOM 结构、事件链、cron 坑位、会话复盘
```

## 首次使用：替换占位符

全仓库 `grep -rn "<YOUR"` 或按下表全局替换：

| 占位符 | 含义 | 出现位置 |
|---|---|---|
| `YOUR_NAME` | 你的系统用户名 / 昵称 / 简历文件名 | 路径、简历 PDF 名、页面登录判定 |
| `/Users/YOUR_NAME/Desktop/YOUR_RESUME_IMAGE.jpg` | 图片简历路径 | `config.json`、`scripts/*` |
| `pan.baidu.com/s/<YOUR_SHARE_ID>` + `提取码：<CODE>` | 作品集网盘分享 | `config.json`、`scripts/*` |
| `<YOUR_UID>` / `<YOUR_ENCRYPT_USER_ID>` / `<YOUR_TOKEN>` | BOSS 页面 `_PAGE` 身份数据（本地调试用） | `references/` |
| `<WECHAT_ID>` | 微信号 | `references/` |
| `<HR>` / `<HR_NAME>` | HR 称谓 / 姓名 | `references/` |
| `COMPANY_1` … `COMPANY_20` | 出现过的公司名（同一家编号一致） | `references/` |

占位符在参考文档里只是叙述用例，**只有 `config.json` 和 `scripts/` 里的必须改** 才能跑起来。

## 运行前提

- macOS：Safari（runner 走 AppleScript 桥，见 `scripts/safari_boss_bridge.applescript`）
- Windows：Edge / Chrome（`scripts/chrome_boss_runner.js`）
- Node + `playwright-core`（`npm install`）
- 首次运行需手动登录 BOSS 直聘，脚本复用已登录的浏览器会话

## 已内置的关键经验（references/）

- **macOS Safari 点击屏障**：Safari 不接收 `isTrusted === false` 的合成事件，pyautogui / `element.click()` / AppleScript 全部被拦；必须走 AppleScript 桥或真实光标。
- **cron 巡检**：只读扫描会话列表 → 按 `[已读]/[送达]` 标签区分「HR 发来的」和「我方发出的」消息（无标签的是 HR 的最后一条）→ 分类回复。
- **列表虚拟滚动**：会话列表会随 Vue 懒加载增删，每次都要重新扫描，不能缓存索引。
- **回复分类**：要附件简历 / 要作品集 / 问地点薪资 / 群发广告 / 无关广告 各有对应话术与跳过规则。

## 免责声明

自动化操作第三方招聘平台可能违反其用户协议，账号风险自负。请控制频率（`config.json` 里的 `automation` 段落）、只投真实感兴趣的岗位，不要用于群发骚扰。本仓库仅供技术学习参考。
