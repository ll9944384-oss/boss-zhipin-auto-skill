---
name: boss-zhipin-auto
description: |
  多平台招聘投递助手。支持按用户指令在 BOSS直聘、猎聘、智联招聘中进行求职投递：
  自动识别平台、打开对应求职网站、搜索职位、分析JD、生成个性化招呼语、
  发送图片简历/作品集链接、记录投递状态并辅助回复HR消息。
  触发词：在BOSS直聘里面投递、在猎聘里面投递、在智联招聘里面投递、
  多平台投递、自动投简历、boss自动打招呼、招聘自动投递。
version: 1.0.0
metadata:
  hermes:
    tags: [job-search, recruitment, automation, boss-zhipin, browser]
    category: productivity
    related_skills: [macos-browser-automation, windows-browser-automation]
---

# 多平台招聘投递助手

这个 skill 是统一入口，不要为猎聘、智联招聘再新建独立 skill。BOSS直聘、猎聘、智联招聘共享候选人画像、JD 分析、岗位打分、招呼语生成和投递日志；差异只放在平台 runner 层。

## 统一入口与平台识别

用户可以这样下达指令：

```text
在BOSS直聘里面进行投递，岗位：留学顾问，城市：杭州
在猎聘里面投递，岗位：行政专员，城市：杭州
在智联招聘里面投递，岗位：内容运营，城市：杭州
同时在BOSS直聘、猎聘、智联招聘投递，岗位：留学顾问，城市：杭州
```

收到任何投递指令后，先调用统一 dispatcher 解析平台、关键词、城市和打开链接：

```bash
python3 <skill-dir>/scripts/job_apply_dispatcher.py plan '在猎聘里面投递，岗位：留学顾问，城市：杭州'
```

dispatcher 会返回：

- `tasks[].platform`：`boss` / `liepin` / `zhilian`
- `tasks[].open_url`：应该打开的搜索入口
- `tasks[].runner`：该平台已实现 runner 时给出脚本路径
- `mode`：单平台或多平台轮询

多平台时必须采用“轮询队列”，不要并发抢同一个前台窗口：

```text
打开全部平台 -> 用户完成登录 -> BOSS投3-5个 -> 猎聘投3-5个 -> 智联投3-5个 -> 循环
```

## 平台状态

| 平台 | 状态 | 执行方式 |
|------|------|----------|
| BOSS直聘 | 已实现 | macOS 使用 Safari runner；Windows 使用 Edge/Chrome runner |
| 猎聘 | 已实现 | macOS 使用 Safari runner；Windows 使用 Edge/Chrome runner |
| 智联招聘 | 规划中 | 先打开搜索页、读取JD、打分、生成招呼语；后续补详情页 runner |

智联在 runner 完成前，不要声称“全自动已投递成功”；只能输出 `planned`、`needs_manual_apply` 或 `needs_runner_implementation`。BOSS 和猎聘可以按各自已实现 runner 执行。

### 操作系统与 runner 选择

必须先运行 dispatcher，然后只调用 `tasks[].runner`。不得在 Windows 上调用 `.py` Safari runner，也不得在 macOS 上忽略用户已选的 Safari 流程。

| 系统 | BOSS runner | 猎聘 runner | 浏览器 |
|---|---|---|---|
| macOS | `scripts/safari_boss_runner.py` | `scripts/safari_liepin_runner.py` | Safari |
| Windows | `scripts/chrome_boss_runner.js` | `scripts/liepin_runner.js` | 优先 Microsoft Edge，其次 Google Chrome |

Windows 流程使用可见本地浏览器 + Playwright CDP。首次运行会创建独立登录资料目录，用户在打开的 Edge/Chrome 窗口中手动登录。不绕过验证码、登录限制或平台风控。

Windows PowerShell 首次安装依赖：

```powershell
Set-Location "$env:USERPROFILE\.hermes\skills\boss-zhipin-auto"
npm install playwright-core
```

Windows 调用示例：

```powershell
node "$env:USERPROFILE\.hermes\skills\boss-zhipin-auto\scripts\liepin_runner.js" open-search --keyword "留学顾问" --city "杭州" --city-code "070020"
node "$env:USERPROFILE\.hermes\skills\boss-zhipin-auto\scripts\liepin_runner.js" extract-cards
node "$env:USERPROFILE\.hermes\skills\boss-zhipin-auto\scripts\liepin_runner.js" open-detail --index 0
node "$env:USERPROFILE\.hermes\skills\boss-zhipin-auto\scripts\liepin_runner.js" extract-detail
node "$env:USERPROFILE\.hermes\skills\boss-zhipin-auto\scripts\liepin_runner.js" generate-greeting
node "$env:USERPROFILE\.hermes\skills\boss-zhipin-auto\scripts\liepin_runner.js" apply-current-job
```

如同时安装 Edge 和 Chrome，runner 默认选 Edge。用户明确指定 Chrome 时，在启动 Hermes 前设置 `HERMES_BROWSER=chrome`。

### 猎聘 runner（macOS）

猎聘默认使用本地 Safari 和固定 Apple Events 桥接，不使用 Chrome/CDP，不绕过验证码或登录限制。用户必须先在 Safari 中手动登录猎聘，并在 Safari 开发菜单中允许来自 Apple Events 的 JavaScript。

固定 runner：

```bash
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_liepin_runner.py open-search --keyword '留学顾问'
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_liepin_runner.py set-city --city '杭州' --city-code '070020'
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_liepin_runner.py extract-cards
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_liepin_runner.py open-detail --index 0
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_liepin_runner.py extract-detail
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_liepin_runner.py generate-greeting
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_liepin_runner.py apply-current-job
```

猎聘投递顺序：

```text
打开 key-only 搜索页 -> `set-city` 选择并回读验证城市 -> 用户登录 -> `extract-cards` 筛列表
-> `open-detail --index N` 打开目标岗位 -> 读取JD -> 生成招呼语
-> 点「聊一聊/继续聊」-> 如弹出附件简历选择弹窗先点「立即投递」
-> 在 IM 输入框发送招呼语 -> 如仍未投递再点「投简历/立即投递」-> 回读页面状态
```

猎聘实战技术点：

- 不要让 Hermes 逐步猜测城市弹层的点击位置。必须调用固定 runner 的 `open-search` 或 `set-city`；runner 会先在页面内追加 `city/dq`，若参数被猎聘重定向清除，再回退到可见城市选择器。
- 城市动作只有在 runner 返回 `ok: true` 且 `status: city_verified` 时才算成功。如果返回 `city_selection_failed`，立即停止岗位提取和投递，把 `result.state.url`、`city/dq`和候选城市文本写入调试结果，不得默认当前城市正确。
- 用户当轮指定城市时，同时传 `--city '<城市名>' --city-code '<猎聘城市码>'`；不要把 BOSS 城市码传给猎聘。
- 即使 `city/dq` 验证成功，猎聘仍可能夹带异地推荐岗位。`extract-cards` 必须按岗位卡中的实际城市二次过滤；`cityMatched: false` 的岗位只记录在 `filteredOutOfCity`，不得进入打分或投递队列。
- 在 macOS 上，`scripts/liepin_runner.js` 只作为 Safari 不可用时的备用。在 Windows 上，它是猎聘默认 runner，Hermes 应直接调用。
- 杭州猎聘城市码当前使用 `070020`，保存在 `config.json.platforms.liepin.city_code`。
- 未投过岗位时，点「聊一聊」可能先弹出 `.select-resume-modal-container` 附件简历弹窗；必须先在弹窗里点「立即投递/投递」，再寻找聊天输入框。
- 已投过岗位时，按钮可能变成「继续聊」，直接打开聊天面板发招呼语。
- 猎聘聊天输入框是 `textarea.ant-im-input`；发送按钮优先找 `button.ant-im-btn-primary.im-ui-basic` 内的“发送”文本。
- 如果弹窗或验证码阻断，runner 必须返回结构化失败状态，不要声称投递成功。

状态规则：

- `sent_verified`：招呼语发送成功，并且页面出现“已投递/投递成功/申请成功/简历已投递”。
- `partial_needs_manual_check`：已经点过聊天或投递，但无法完整验证。
- `needs_manual_apply`：找不到聊天/投递按钮，需要用户检查页面。
- `login_or_verification_required`：猎聘要求登录、扫码或验证码，必须暂停让用户处理。

不要再输出“猎聘 runner 未实现”的手动投递指引；除非 runner 返回明确失败状态。

## 2026-07-11 效率修订

这项技能必须优先走“固定 Safari runner + 状态验证”模式，禁止每一步都临时写 AppleScript、再让用户点运行。上一轮会话 `20260711_161035_fa16e2` 暴露了两个严重问题：

- 低效：模型调用超过 110 次，反复执行“思考 -> 写脚本 -> 等待 -> 再分析”，最后触发 `max_iterations_reached(60/60)`。
- 误报：脚本输出 `sent` 不等于真的投递成功。必须回读聊天窗口，看到招呼语或作品集链接已出现在最近消息中，才能记录为“已发送”。
- 文案误导：BOSS 在 HR 未回复前可能不能发送在线简历，因此禁止写“在线简历已发送”。如果图片简历和作品集链接没有被验证发送成功，也禁止在消息里暗示已发送。

硬性规则：

1. 使用 `scripts/safari_boss_runner.py` 做 Safari 页面导航、JS 执行、职位提取、聊天回读验证。
2. 一轮最多只让 AI 做三次判断：解析用户目标、批量筛选职位、生成候选消息。低层点击、滚动、DOM 读取必须交给 runner。
3. 不再每一步创建 `/tmp/*.applescript`，也不要使用 `python3 -c`、`osascript -e`、heredoc 等临时脚本形式。
4. 任何“投递完成”必须满足验证条件：聊天窗口最近消息中包含本次招呼语关键片段或作品集链接。
5. 如果无法验证，状态只能写成 `needs_manual_check`，不得写 `sent`、`done`、`投递完成`。
6. 投递动作必须原子化：图片简历、作品链接、打招呼用语不能拆成多个模型回合。筛选出合适岗位后默认调用 `apply-current-job`，由 runner 负责点击沟通、进入聊天，并按“投递简历图片 -> 发作品集链接 -> 发打招呼用语”执行完整投递或只补发图片。
7. 图片简历上传优先使用 runner 内置的剪贴板粘贴方案：把图片写入系统剪贴板、聚焦 BOSS 聊天输入框、Cmd+V 粘贴、Enter/发送。失败后才允许尝试一次真实 UI 文件选择；仍失败则标记 `resume_image_manual_required`，不要反复尝试文件对话框。
8. 作品集链接必须以真实 URL 进入聊天文本；不得写“作品集可随时查看”但不附链接。
9. 在 HR 回复前，不要尝试或声称已发送 BOSS 在线简历。只按顺序发送：图片简历、作品集链接、自我介绍。
10. 严禁使用 `from hermes_tools import terminal`、`execute_code`、`Running code`、`import base64/json` 等代码执行方式来拼命令或转义文本；这会触发用户手动点“运行”。所有浏览器动作必须直接调用固定 runner 命令。
11. 必须先进入具体 HR 聊天上下文，页面出现 `chat-input` 或 `textarea.input-area` 后才能发送。停留在 `/web/geek/jobs` 搜索页时禁止发送文字或图片，避免把招呼语写进搜索框。
12. 如果已经和该 HR 聊过天，不要机械重复发送招呼语和作品集。默认使用 `apply-current-job`：它会先进入聊天并检查聊天记录，已发过介绍/作品集则只补发图片；未发过则完整投递。

推荐执行模型：

```
scan visible cards -> batch extract details -> filter
-> apply-current-job -> verify transcript -> log exact status
```

## 候选人画像

候选人画像统一从 `config.json` 的 `user_profile` 和 `search_params` 读取。不要把候选人固定理解为剪辑师，也不要把某一次投递的岗位、姓名、薪资、技能、作品集当成通用模板。

最低要求：

- 搜索关键词、城市、薪资、通勤范围优先读 `config.json`；用户当轮明确补充的信息优先级最高。
- 招呼语必须根据当前 JD 抽取岗位业务、能力要求和关键词，再和 `user_profile.skills / strengths / experience_highlights / transferable_skills` 做匹配。
- 如果候选人没有配置某行业经历，使用可迁移能力表达匹配，例如客户沟通、信息整理、需求理解、项目推进、学习能力；不要编造具体项目经历。
- 简历：优先发送图片简历；HR 未回复前不要声称已发送 BOSS 在线简历。
- 作品集或附件链接必须从 `config.json` 读取，只有真实链接存在时才发送。

---

## 总体流程

```
1. 识别平台 → 2. 打开网站并手动登录 → 3. 搜索筛选 → 4. 逐个投递 → 5. 监听HR回复 (循环)
                                   ↓
                              记录投递日志
```

**运行方式**：
1. 用户打开终端，启动 Hermes
2. 用户说 "在BOSS直聘里面投递"、"在猎聘里面投递" 或 "同时在BOSS直聘、猎聘、智联招聘投递"
3. 先调用 `job_apply_dispatcher.py plan` 解析平台和打开链接
4. 系统打开对应求职网站，等待用户手动登录
5. 登录确认后，按平台队列接管可自动化部分

**重要策略**：
BOSS 直聘是 SPA（单页应用），页面元素通过 JS 动态渲染。猎聘/智联偏传统详情页投递型，但也可能有验证码、扫码、登录态和投递频率限制。

### 打开网站规则

- BOSS直聘：打开 `https://www.zhipin.com/web/geek/job?query=<关键词>&city=<城市编码>`
- 猎聘：打开 `https://www.liepin.com/zhaopin/?key=<关键词>`
- 智联招聘：打开 `https://www.zhaopin.com` 或 dispatcher 返回的搜索入口
- 多平台：先逐个打开所有平台，让用户完成登录；不要在未登录状态下继续投递。
- 打开多个平台后，执行投递时一次只控制一个前台浏览器窗口；平台之间用队列轮询。

**⚠️ 浏览器选择**：Hermes 内置浏览器（Browserbase）会被 BOSS 直聘反爬系统拦截
（重定向到 `chrome://new-tab-page/`），`browser_navigate` / `browser_console` /
`browser_snapshot` 均不可用。**必须使用固定 Safari runner**。
详见关联技能 `macos-browser-automation` 和 `references/boss-zhipin-workflow.md`。

操作模式（Safari 方案）：
0. **默认只使用 Safari 固定 runner**：`/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py`。用户明确要求“换回 Safari”后，Chrome/Playwright runner 只作为实验备用，不再作为默认投递路线。
1. **优先使用固定 runner**：`/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py`
2. 禁止反复生成临时 AppleScript 文件作为主流程
3. 每次页面操作后等待 SPA 渲染，但等待由 runner 或单个批处理脚本承担
4. 每次发送后必须调用 `verify-message` 回读验证
5. runner 已经是可执行文件，直接调用脚本路径；不要再写成 `python3 ~/.hermes/.../safari_boss_runner.py`，这样会增加 Hermes 审批/运行拦截概率。
6. 投递岗位时用 `apply-current-job`，不要为了长招呼语生成 base64，不要写 Python/JS 辅助脚本；招呼语由 runner 先读取当前详情页 JD 后生成，作品集从 `config.json` 读取。

固定 runner 调用示例：

```bash
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py tabs
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py navigate 'https://www.zhipin.com/web/geek/job?query=用户目标关键词&city=101210100'
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py extract-cards
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py extract-detail
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py open-current-detail
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py click-chat
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py send-text '您好...'
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py click-send
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py verify-message '作品集：https://pan.baidu.com'
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py apply-current-job \
  --job-title '岗位名' \
  --company '<HR_NAME>' \
  --resume-image '/Users/YOUR_NAME/Desktop/resume.jpg'
```

Chrome/Playwright runner 只在 Safari 登录或页面结构完全失效时作为实验备用；默认不要调用：

```bash
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/chrome_boss_runner.js open-login
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/chrome_boss_runner.js apply-current-job --resume-image '/Users/YOUR_NAME/Desktop/resume.jpg'
```

首选且默认使用 `apply-current-job`。不要单独运行代码生成 payload；如果文本转义变复杂，也不要处理转义，直接使用 runner 内部模板。

投递时必须使用 `apply-current-job`，不要分别调用 `send-text`、图片上传、`send-text` 三个模型回合。除非 runner 返回明确的局部失败，再只处理失败的局部动作。

`apply-current-job` 的投递顺序：

- 如果当前停在搜索结果页，runner 必须先进入当前/第一个职位卡片的详情页，再点击详情页里的「立即沟通/继续沟通」；不要直接在搜索列表页点击沟通按钮。
- 第一步：上传图片简历。
- 第二步：单独发送真实作品集链接。
- 第三步：基于当前岗位 JD 生成并发送个性化打招呼用语，不在这条消息里附作品集。
- 进入聊天前必须先从当前岗位详情页提取 JD，按 JD 中的业务场景、岗位职责、技能要求、性格/协作要求生成个性化招呼语；如果提取失败，才退回 `config.json` 中的通用候选人画像。
- 禁止出现“在线简历已发送”“简历已发送”“作品集可查看但无链接”。
- 如果 `resume_image` 上传失败，最终状态应为 `resume_image_manual_required`，并提醒用户手动拖入图片；因为当前流程要求图片第一步完成，所以不要继续发送作品集和招呼语。
- 上传图片简历时不要临时写剪贴板、pyautogui 或 AppleScript 方案；这些逻辑已内置在 runner 的 `upload-image` / `apply-current-job` 中。
- 验证作品集时必须检查 `pan.baidu.com` 或用户提供的真实域名是否出现在最近聊天文本中。

状态记录要求：

| 状态 | 含义 |
|------|------|
| `candidate` | 只在列表页看到，还没检查 JD |
| `filtered_out` | 地点/薪资/用户排除项不匹配 |
| `prepared` | 已生成招呼语和作品集消息 |
| `sent_verified` | 已回读聊天窗口并确认消息存在 |
| `needs_manual_check` | 脚本可能发送了，但无法回读确认 |
| `resume_image_manual_required` | 图片简历需要用户手动拖入 |
| `partial_sent_verified` | 招呼语/作品集已验证，但图片上传失败 |

---

## 阶段一：等待手动登录

### 目标
打开BOSS直聘网页版，等待用户完成扫码或验证码登录。

### 操作步骤

1. 导航到Boss直聘首页：
   ```
   browser_navigate("https://www.zhipin.com/web/geek/job")
   ```

2. 获取页面快照，判断是否已登录：
   ```
   browser_snapshot()
   ```

3. **登录状态判断**：
   - 如果页面显示登录界面（有"登录"按钮或扫码提示）→ 提示用户手动登录
   - 如果页面显示职位列表 → 说明已登录，跳到阶段二

4. **提示用户**：
   说："请在浏览器中完成登录（扫码或验证码），登录成功后回复'好了'或'继续'。"

5. 用户确认后，刷新页面快照确认登录成功：
   ```
   browser_snapshot()
   ```

6. 确认看到职位列表或首页内容后，进入阶段二。

---

## 阶段二：搜索与筛选职位

### 搜索参数

从 `config.json.search_params` 读取搜索条件。`keyword` 为空时，先让用户给出目标岗位关键词；不要自行使用“剪辑”作为默认关键词。

- 搜索关键词：`search_params.keyword` 或用户当轮指定的岗位
- 城市：`search_params.city_name / city_code`
- 薪资下限：`search_params.salary_min`，为空则不做薪资硬筛

### 操作步骤

1. 导航到搜索页面（带城市和关键词参数）：
   ```
   browser_navigate("https://www.zhipin.com/web/geek/job?query=<岗位关键词>&city=<城市编码>")
   ```

2. 等待页面加载完成后获取快照：
   ```
   browser_snapshot(full=false)
   ```

3. **设置薪资筛选**：
   - 在页面快照中找到薪资筛选区域的元素
   - 寻找"薪资不限"或薪资下拉选项
   - 如果配置了薪资下限，点击薪资筛选，选择最接近目标薪资的区间
   - 不要选择明显高于用户目标的薪资段，避免筛掉实际匹配岗位

4. **重新获取快照**，确认筛选已生效：
   ```
   browser_snapshot()
   ```

5. **提取职位列表**：
   - **用 JS 提取 `.job-card-wrap` 元素**：获取职位名、公司、地点、经验/学历标签
   - **⚠️ 薪资字段在列表页为空**：`<span class="job-salary">` 标签存在但内容为空，
     BOSS 直聘不在此页面展示薪资。必须进入详情页才能看到薪资
   - 提取职位链接：`card.querySelector('.job-name').getAttribute('href')`
     格式如 `/job_detail/xxx.html`
   - 职位结构示例：`.job-name`(标题), `.boss-name`(公司), `.company-location`(地点),
     `.tag-list li`(经验/学历标签)

6. **对每个职位执行以下判断**：
   - 是否符合用户当轮目标岗位和 `config.json` 的职业方向？
   - 公司地点是否在可接受通勤范围内？
     - BOSS会显示大致区域，优先匹配 `accepted_districts`
     - 排除明显超出通勤范围或命中 `excluded_districts` 的区域
   - 如果配置了薪资下限，薪资是否达到目标？
   - JD 是否出现用户明确排除的行业、岗位类型或工作内容？
   - 如果是→ 进入阶段三
   - 如果否→ 跳过，继续下一个

---

## 阶段三：打招呼 & 发送简历

对每个符合条件的职位，执行以下操作：

### 3.1 打开职位详情

1. **从列表页提取到的链接拼接完整 URL 并导航**：
   ```
   window.location.href = 'https://www.zhipin.com' + jobHref
   ```
   - 链接格式如 `/job_detail/xxx.html`，**必须加 `.html` 后缀**否则空白页
   - **⚠️ 登录丢失风险**：通过 `window.location.href` 导航到详情页可能丢失登录状态
     （导航栏显示「登录/注册」而非用户名）。如发生此情况，让用户先在 Safari 中
     手动重新登录，再继续自动化

2. 等待 3-4 秒让 SPA 渲染详情页。

3. **用 JS 提取详情页内容** (`document.body.innerText`)：
   - 薪资：虽然列表页不展示，详情页文本中通常包含薪资信息
   - JD：`.job-sec-text, .detail-text, .job-detail` 等选择器
   - 公司信息：`.company-name, .sider-company` 等

### 3.2 分析JD内容

从详情页文本中提取以下信息，判断是否匹配：
- 公司名称、薪资范围、公司规模/行业
- 岗位业务：岗位服务什么客户、项目或场景
- 技能要求：软件、工具、证书、经验、销售/服务/内容/运营/交付能力等
- 加分项：JD 中明确提到但不是硬性门槛的能力
- 排除项：只按用户明确说过的排除条件或 `config.json` 中的规则排除，不要把某个职业的排除项套到其他岗位

### 3.3 AI生成个性化招呼语

`apply-current-job` 会自动基于当前详情页 JD 内容生成一段约80-150字的中文招呼语，Hermes 不需要另行手写消息。要求：

**核心原则**：
- 先判断 JD 的业务场景：这个岗位到底要解决什么问题，而不是只复述岗位名。
- 再从候选人的技能、经历亮点、通用能力里挑 2-4 个真实匹配点。
- 没有直接行业经验时，强调可迁移能力，例如需求理解、客户沟通、信息整理、执行推进、学习速度；不要硬编行业案例。
- 语气要像熟悉业务的人：自然、专业、直接、有分寸，不要像新手自我介绍，也不要像分析报告。

**招呼语模板框架**：
> 您好，看到贵公司在招聘 [职位名]，我认真看了 JD，岗位重点应该在 [业务场景/核心目标]。
> 我这边能匹配的是 [真实技能/经历/可迁移能力]，
> 对 [JD 里的关键要求] 会重点兼顾。
> 如果需要一个能快速理解业务、把事情推进到结果的人，希望有机会进一步沟通。

**约束**：
- 如果 JD 要求某项工具/证书/经验，只有候选人画像里有对应内容时才写“熟悉/做过”；否则写“能快速学习/有相关底层能力”，不要编造。
- 如果 JD 提到明确业务场景，例如留学咨询、销售转化、课程顾问、视频后期、行政协调、内容运营等，招呼语要围绕该场景说匹配点。
- 不要编造没有的经历；候选人画像为空时，只能使用通用可迁移能力。
- 不要承诺具体的掌握程度数字，保持真实
- **不要说在线简历已发送** — BOSS 在 HR 未回复前可能限制在线简历发送
- 招呼语本身不要包含作品集 URL；作品集由 runner 在简历图片后、招呼语前单独发送

### 3.4 发送招呼语

只允许调用固定 runner 的 `apply-current-job`，不要手写 JS，不要用 `browser_console`，不要生成 base64，不要用代码工具拼接文本。

```bash
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py apply-current-job --job-title '岗位名' --company '公司名' --resume-image '/Users/YOUR_NAME/Desktop/resume.jpg'
```

`apply-current-job` 会先从当前岗位页点击「立即沟通/继续沟通」，如果没有直接出现聊天输入框，会自动进入顶部消息页并尝试打开最近聊天；进入聊天后再检查聊天记录：如果已经发过招呼语或作品集，只补发图片；如果没有发过，才按“图片简历、作品集、招呼语”完整发送。登录丢失或无法进入聊天时 runner 会返回失败状态，不能继续声称已投递。
发送前 runner 会记录 `extract_job_detail_for_greeting` 步骤，并把最终招呼语写入 `send_greeting.text`，方便复核招呼语是否确实来自 JD。
如果 runner 返回 `could_not_enter_chat_context`，说明无法自动进入具体聊天框；此时再让用户介入，不要继续发送。
如果文字已经进入输入框但未发出，只允许调用固定 runner 的 `click-send` 补点发送按钮，不要写临时 pyautogui、System Events 或 AppleScript。

### 3.5 图片简历，不发送在线简历

BOSS 直聘在 HR 未回复前可能限制发送在线简历，因此：

- 不要点击或声称点击了“发简历”。
- 不要在招呼语里写“在线简历已发送”。
- 只尝试发送用户提供的图片简历。
- 如果图片上传失败，返回 `resume_image_manual_required`，让用户手动拖入图片。
- 等 HR 回复后，用户可以再手动或半自动点击“发简历”。

如果当前 HR 对话已经发过招呼语或作品集，只补发图片简历，可以使用：

```bash
/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts/safari_boss_runner.py resume-image-only '/Users/YOUR_NAME/Desktop/resume.jpg'
```

这种模式不会发送招呼语，也不会发送作品集，只尝试把图片发到当前打开的聊天对话。一般情况下优先用 `apply-current-job` 自动判断，只有你明确要求“只补图”时才用它。

### 3.6 发送作品集链接

作品集链接由 `apply-current-job` 在需要完整投递时自动作为第二步单独发送。不要单独再跑 `send-text` 或 `browser_console` 发送作品集，除非 runner 明确返回作品集未验证成功。

必须验证发送结果：

- `apply-current-job` 返回 `verified.portfolio: true`，才能认为作品集链接已发送。
- 如果返回 `verified.portfolio: false`，状态只能写 `needs_manual_check`，不能说“投递完成”。

### 3.7 记录投递日志

每次操作后，在控制台输出以下信息。注意：`状态` 必须来自回读验证，不得只根据点击脚本返回值填写：

```
[投递记录]
时间：[当前时间]
公司：[公司名称]
职位：[岗位名]
薪资：[薪资范围]
地点：[公司地点]
招呼语：[招呼语内容]
状态：sent_verified / needs_manual_check / resume_image_manual_required
验证证据：[最近聊天内容中匹配到的关键短句，或说明未验证]
---
```

### 3.8 返回职位列表

1. 返回职位列表页：
   ```
   browser_back()
   ```

2. 获取快照，继续下一个职位：
   ```
   browser_snapshot()
   ```

3. **滚动加载更多职位**（如果需要）：
   ```
   browser_scroll(direction="down")
   ```

---

## 阶段四：监听并回复HR消息

这个阶段是一个**独立循环**，可以在打招呼的同时运行，也可以单独运行。

### 核心原则

BOSS 直聘的聊天列表是 SPA 动态渲染页面，无障碍树可能找不到可点击元素。
不要使用 `browser_console` 或代码工具临时注入 JS。阶段四默认只做消息读取、分类和回复草稿；涉及真实发送时必须使用固定 runner 能力，不能临时写脚本。

### 触发方式

- 用户说"检查HR消息"或"开始监听HR回复"
- 或者在打招呼每投递5个职位后，自动检查一次消息

### 操作步骤

1. 使用 Safari 打开 `https://www.zhipin.com/web/geek/chat`。
2. 如果需要自动读取，必须通过固定 runner 新增/已有命令完成；不要现场生成 `browser_console`、Python、AppleScript 片段。
3. 没有固定 runner 命令时，只输出建议回复草稿，不要声称已经回复。
4. **读取HR最新消息**：只基于实际可见文本分析，不能猜测。

### AI分析HR消息并生成回复

根据HR的消息内容，判断意图并生成回复：

#### 情况A：HR发来面试邀请

HR消息示例：
- "方便来面试吗？"
- "我们想约你面试"
- "明天下午有时间吗？"

**回复策略**：
- 表达感谢和积极态度
- **不要直接承诺具体时间** — 需要用户自己确认
- 回复模板：
  > 您好！感谢邀请~ 我对这个岗位很感兴趣。
  > 请问方便告知一下面试的形式（线上/线下）和大概的流程吗？
  > 我确认一下时间安排后第一时间回复您。

#### 情况B：HR询问具体问题

HR消息示例：
- "你会用达芬奇吗？"
- "之前主要做什么类型的视频？"
- "期望薪资多少？"
- "什么时候能到岗？"

**回复策略**：
- 根据 `config.json.user_profile` 的真实能力诚实回答
- **期望薪资**：优先读 `expected_salary`；为空时请用户确认，不要自行报价
- **到岗时间**：优先读 `available_date`
- **技能问题**：基于候选人真实技能、经历亮点和可迁移能力回答

#### 情况C：HR要求发作品集

HR消息示例：
- "有作品集吗？"
- "发几个作品看看"
- "有没有链接？"

**回复策略**：
- 用户作品集链接：从 `config.json.user_profile.portfolio_link` 读取；为空时先询问用户
- 直接将链接和提取码发给HR，附简短说明：
  > 您好，这是我的作品集/资料链接：[从 config.json 读取的真实链接]
  > 请查收~

#### 情况D：HR发了公司介绍/岗位详情

HR消息示例：长篇公司介绍、岗位详细要求

**回复策略**：
- 阅读并理解内容
- 表达对公司/岗位的兴趣
- 如有匹配点，简单提及
- 主动推进下一步：
  > 感谢您的详细介绍！我之前也有过类似的经验，
  > 很期待有机会加入贵公司。方便进一步聊聊吗？

#### 情况E：其他/寒暄

HR消息示例：表情包、"好的"、"收到"、系统消息

**回复策略**：
- 简单友好的回应
- 不要过度回复
- 示例："好的，期待您的回复~" 或 "感谢~"

### 发送回复

没有固定 runner 命令时，不自动发送 HR 回复，只输出回复草稿。不要为了回复消息临时调用 `browser_console`、`execute_code` 或 `hermes_tools`。

### 标记已处理

回复完所有HR消息后：
1. 返回消息列表
2. 确认是否还有未处理消息
3. 输出处理摘要：
   ```
   [HR消息处理摘要]
   共处理 X 条HR消息
   - 面试邀请：Y 条 (已表达意向)
   - 问题回复：Z 条
   - 其他：W 条
   ```

---

## 阶段五：持续循环模式

启动完整的无人值守模式：

```
循环执行：
  1. 检查HR消息并回复（阶段四）
  2. 搜索新职位（阶段二）
  3. 如果没有新职位 → 等待5分钟后重新开始
  4. 对每个新职位 → 打招呼 + 发简历（阶段三）
  5. 每投递5个职位 → 检查一次HR消息
  6. 每30分钟 → 输出一次进度报告
```

### 防重复投递机制

- 维护一个「已投递公司列表」
- 每次在投递前，检查该公司是否已被投递过
- 如果已投递 → 跳过
- 每天最多投递50个职位（BOSS平台限制）

### 进度报告格式

每30分钟输出：

```
═══════════════════════════════════════
        BOSS直聘自动投递 - 进度报告
═══════════════════════════════════════
运行时间：X小时X分钟
已搜索职位：X 个
已投递职位：X 个
已回复HR：X 条消息
当前队列剩余：X 个职位
═══════════════════════════════════════
```

---

## 注意事项

### BOSS平台反爬策略

1. **操作间隔**：每次点击之间等待1-3秒，模拟人类操作节奏
2. **不要批量快速操作**：每投递1个职位后，等待3-5秒再进行下一个
3. **滚动页面时**：每次滚动后等待1-2秒再读取快照
4. **如果遇到验证码**：
   - 使用 browser_vision 截图分析
   - 提示用户需要手动处理验证码
   - 暂停自动化，等待用户处理完毕

### 异常处理

- **页面加载缓慢**：最多等待10秒，超时后刷新页面重试
- **元素未找到**：获取全量快照(full=true)重新分析页面结构
- **发送失败**：检查是否被限制（如当日打招呼次数已用完），如是则输出提示
- **对话窗口未出现**：尝试再次点击"立即沟通"按钮

### 安全边界

- 本工具仅供个人求职使用
- 不修改或伪造用户简历信息
- 不主动发起加微信等越界操作（除非HR先提）
- 不发送未授权附件；只发送用户明确指定的图片简历和作品集链接
- 所有操作在浏览器可视范围内进行，用户可随时干预

### 图片简历上传限制

- BOSS 直聘网页端聊天**支持发送图片**（聊天列表中出现 `[图片]` 标记）
- 聊天页图片上传入口是 **第 0 个 `<input type="file">`**（可见，accept=image/gif,jpeg,jpg,png）
- 父元素链：`DIV.btn-sendimg > DIV.toolbar-btn-content > DIV.chat-controls`
- ⚠️ **浏览器安全限制**：JS `document.querySelectorAll("input[type=file]")[0].click()` **无法触发原生文件对话框**
  （非用户手势触发的事件被浏览器拦截）。解决方案：
  1. 用户手动拖拽图片到聊天窗口（推荐）
  2. 使用 `pyautogui` 模拟键盘操作（Cmd+Shift+G → 输入路径 → Enter），需先 `pyautogui.FAILSAFE = False`
  3. 将图片简历上传到百度网盘作品集文件夹，HR 可从作品集链接查看
- **结论**：自动化投递流程必须先用 `apply-current-job` 进入聊天、判断当前聊天状态并尝试发送图片简历；只有 runner 返回 `resume_image_manual_required` 时，才让用户手动拖入图片

### 职业专项筛选规则

- 只有当 `search_params.keyword` 或用户目标明确是视频剪辑/影视后期时，才启用短视频排除规则。
- 对其他岗位，例如留学顾问、行政、销售、运营，不要套用视频剪辑的排除项。
- 视频剪辑专项：仅检查标题不够，大量岗位标题是「剪辑」「视频剪辑」等泛词，但 JD 中揭示是短视频/短剧/AI短剧。进入详情页后必须检查 JD 全文：
  - 「短剧」「AI短剧」「AI漫剧」「网大网剧」「直播切片」「切片剪辑」「带货视频」
  - 「达人IP」「达人矩阵」「信息流素材」「种草」「抖音综艺」「直播连麦」
  - 尤其警惕「AIGC内容剪辑师」「AI情感短视频」「短剧后期」等伪装岗位

### 替代搜索关键词

替代搜索关键词必须按用户目标岗位生成。下面只是“视频剪辑/影视后期”目标下的示例，不得用于其他职业：

| 关键词 | URL 编码 | 适用场景 |
|--------|----------|----------|
| 影视后期 | %E5%BD%B1%E8%A7%86%E5%90%8E%E6%9C%9F | 传统影视后期、包装 |
| 宣传片 剪辑 | %E5%AE%A3%E4%BC%A0%E7%89%87+%E5%89%AA%E8%BE%91 | 企业宣传片方向 |
| 后期制作 | %E5%90%8E%E6%9C%9F%E5%88%B6%E4%BD%9C | 泛后期岗位 |
| PR 剪辑 | PR+%E5%89%AA%E8%BE%91 | PR 软件相关岗位 |

每次切换关键词后，都需要滚动加载更多结果（`window.scrollBy(0, 2000)` × 多次）。

---

## 配置参考

### 职位搜索URL参数

| 参数 | 值 | 说明 |
|------|-----|------|
| query | 用户目标岗位关键词 | 搜索关键词 |
| city | 101210100 | 杭州城市编码 |
| experience | (可选) | 经验要求 |
| degree | (可选) | 学历要求 |

### BOSS直聘城市编码参考（杭州各区）

| 区域 | 编码 |
|------|------|
| 拱墅区 | 101210100,101210100_101210109 |
| 西湖区 | 101210100,101210100_101210106 |
| 上城区 | 101210100,101210100_101210102 |
| 余杭区 | 101210100,101210100_101210110 |
| 滨江区 | 101210100,101210100_101210108 |
| 萧山区 | 101210100,101210100_101210109_? |

说明：BOSS直聘的区域筛选编码可能因版本更新而变化，实际使用时应以页面动态获取的为准。

---

## 启动命令

用户在 Hermes 中启动：

```
开始BOSS直聘自动投递
```

或者分阶段启动：

```
在BOSS上搜索[目标岗位]       → 只执行阶段二
检查BOSS上的HR消息         → 只执行阶段四
停止BOSS自动投递           → 停止循环模式
```
