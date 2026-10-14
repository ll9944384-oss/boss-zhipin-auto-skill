#!/usr/bin/env node
/*
 * Chrome/Playwright runner for BOSS workflows.
 *
 * This runner uses a persistent local Chrome profile so the user can log in once
 * and reuse the session. It does not attempt to bypass CAPTCHA, rate limits, or
 * platform controls; if BOSS asks for manual verification, stop and let the user
 * handle it in Chrome.
 */

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

function loadPlaywright() {
  try {
    return require("playwright-core");
  } catch (error) {
    console.log(JSON.stringify({
      ok: false,
      status: "dependency_missing",
      reason: "playwright_core_not_installed",
      install: "Run npm install playwright-core inside the boss-zhipin-auto skill directory.",
    }, null, 2));
    process.exit(2);
  }
}

const { chromium } = loadPlaywright();
const { resolveBrowserExecutable, browserName } = require("./browser_runtime");

const SKILL_DIR = path.dirname(path.dirname(__filename));
const CONFIG_PATH = path.join(SKILL_DIR, "config.json");
const USER_DATA_DIR = path.join(os.homedir(), ".hermes", "boss-browser-profile");
const CDP_PORT = 9223;
const CDP_ENDPOINT = `http://127.0.0.1:${CDP_PORT}`;

function readConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
  } catch {
    return {};
  }
}

function absUserPath(filePath) {
  if (!filePath) return "";
  if (filePath.startsWith("~/")) return path.join(os.homedir(), filePath.slice(2));
  return path.resolve(filePath);
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      args._.push(token);
      continue;
    }
    const key = token.slice(2).replace(/-([a-z])/g, (_, ch) => ch.toUpperCase());
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

function waitForCdp(timeoutMs = 8000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(`${CDP_ENDPOINT}/json/version`, (res) => {
        let body = "";
        res.on("data", (chunk) => { body += chunk; });
        res.on("end", () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(body);
          } else if (Date.now() - started > timeoutMs) {
            reject(new Error(`CDP not ready: ${res.statusCode}`));
          } else {
            setTimeout(tick, 300);
          }
        });
      });
      req.on("error", () => {
        if (Date.now() - started > timeoutMs) reject(new Error("CDP not ready"));
        else setTimeout(tick, 300);
      });
      req.setTimeout(1000, () => req.destroy());
    };
    tick();
  });
}

async function ensureChromeRunning(startUrl = "https://www.zhipin.com/web/geek/job", preferredBrowser = "") {
  try {
    await waitForCdp(800);
    return { started: false, endpoint: CDP_ENDPOINT };
  } catch {
    // Start a normal, visible Chrome process that stays alive after this script exits.
  }

  const browserPath = resolveBrowserExecutable(preferredBrowser);
  fs.mkdirSync(USER_DATA_DIR, { recursive: true });
  const child = spawn(browserPath, [
    `--remote-debugging-port=${CDP_PORT}`,
    `--user-data-dir=${USER_DATA_DIR}`,
    "--no-first-run",
    "--no-default-browser-check",
    startUrl,
  ], {
    detached: true,
    stdio: "ignore",
  });
  child.unref();
  await waitForCdp(10000);
  return { started: true, endpoint: CDP_ENDPOINT, profile: USER_DATA_DIR, browser: browserName(browserPath), executable: browserPath };
}

async function openBrowser() {
  await ensureChromeRunning();
  const browser = await chromium.connectOverCDP(CDP_ENDPOINT);
  const context = browser.contexts()[0] || await browser.newContext();
  const page = context.pages()[0] || await context.newPage();
  return { browser, context, page };
}

async function disconnectBrowser(browser) {
  if (browser && typeof browser.disconnect === "function") {
    await browser.disconnect();
  }
}

async function findBossPage(context, page) {
  const pages = context.pages();
  return pages.find((p) => /zhipin\.com/.test(p.url())) || page;
}

async function visibleLocator(page, selector) {
  const loc = page.locator(selector);
  const count = await loc.count();
  for (let i = 0; i < count; i += 1) {
    const item = loc.nth(i);
    if (await item.isVisible().catch(() => false)) return item;
  }
  return null;
}

async function chatInput(page) {
  return visibleLocator(page, [
    'div.chat-input[contenteditable="true"]',
    "div.chat-input[contenteditable]",
    "textarea.input-area",
    '[contenteditable="true"]',
  ].join(", "));
}

async function extractDetail(page) {
  const data = await page.evaluate(() => {
    const body = document.body.innerText || "";
    const title = (document.querySelector(".job-name, h1, .name") || {}).textContent || "";
    const company = (
      document.querySelector(".company-name, .sider-company .name, .job-detail-company .name, a[href*='/gongsi/']")
      || {}
    ).textContent || "";
    const jdNode = document.querySelector(".job-sec-text, .detail-text, .job-detail, [class*='job-sec']");
    const salary = (body.match(/\d+\s*-\s*\d+\s*K(?:·\d+薪)?|\d+\s*K(?:·\d+薪)?/i) || [""])[0];
    return {
      url: location.href,
      title: title.trim(),
      company: company.trim(),
      salary,
      jdText: ((jdNode ? jdNode.innerText : body) || "").replace(/\s+/g, " ").trim().slice(0, 4000),
      text: body.slice(0, 5000),
    };
  });
  return data;
}

function includesAny(text, words) {
  const lower = String(text || "").toLowerCase();
  return words.some((word) => lower.includes(String(word).toLowerCase()));
}

function greetingFor(detail, profile) {
  const jd = detail.jdText || detail.text || "";
  const title = detail.title || profile.job_title || "剪辑师";
  const skills = ["PR", "AE", "达芬奇", "PS"];
  const configured = (profile.skills || []).map((skill) => {
    const lower = String(skill).toLowerCase();
    if (lower.includes("premiere")) return "PR";
    if (lower.includes("after effects")) return "AE";
    if (lower.includes("davinci") || lower.includes("resolve")) return "达芬奇";
    if (lower.includes("photoshop")) return "PS";
    if (lower.includes("final cut")) return "Final Cut Pro";
    return String(skill);
  });
  const skillText = [...new Set([...skills, ...configured])].slice(0, 4).join("、");

  let project = "后期制作项目";
  let need = "重点不只是剪接，还要兼顾素材逻辑、节奏、包装、调色和成片质感";
  let response = "我能把剪辑、基础调色、包装、声音处理和多版本输出串起来推进";

  if (includesAny(jd, ["tvc", "广告片", "品牌片", "品牌宣传"])) {
    project = "广告TVC、品牌片";
    need = "更看重信息表达、画面质感和品牌调性";
    response = "我会先理清传播目标和素材逻辑，再把剪辑节奏、画面风格、包装和声音统一起来推进";
  } else if (includesAny(jd, ["宣传片", "形象片", "企业宣传", "企业视频"])) {
    project = "企业宣传片、形象片";
    need = "既要讲清楚企业信息，也要保证画面稳、节奏顺、整体气质统一";
    response = "我能从素材梳理、结构节奏、基础调色到字幕包装一起处理，让成片完整、干净、有说服力";
  } else if (includesAny(jd, ["纪录片", "纪实", "采访", "访谈"])) {
    project = "纪录片、纪实类内容";
    need = "更看重素材取舍、叙事逻辑和情绪节奏";
    response = "我会先抓人物和事件线索，再通过剪辑节奏、音乐音效和画面衔接把内容关系讲清楚";
  } else if (includesAny(jd, ["mg动画", "二维动画", "三维动画", "展厅", "多媒体", "数字视觉"])) {
    project = "MG动画、展厅多媒体和数字视觉内容";
    need = "更看重信息层级、视觉包装和落地交付的稳定性";
    response = "我能配合把脚本信息、画面节奏、AE包装和输出规格串起来，保证不同展示场景下的完成度";
  }

  return `您好，看到贵公司在招聘${title}，这个方向和我比较匹配。${project}不是单纯把素材剪顺，${need}。${response}。我熟悉${skillText}等后期工具，希望有机会进一步沟通。`;
}

async function ensureDetailPage(page) {
  if (/\/job_detail\//.test(page.url())) return { ok: true, status: "already_detail_page", url: page.url() };
  const target = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll(".job-card-wrap, .job-card-box"));
    const card = cards.find((node) => {
      const r = node.getBoundingClientRect();
      return r.width > 80 && r.height > 40;
    }) || cards[0];
    if (!card) return null;
    const titleEl = card.querySelector(".job-name, a[href*='/job_detail/']");
    const hrefEl = card.querySelector("a[href*='/job_detail/']") || titleEl;
    let href = hrefEl ? hrefEl.getAttribute("href") || "" : "";
    if (!href) return null;
    if (href.startsWith("/")) href = location.origin + href;
    if (/\/job_detail\//.test(href) && !/\.html(?:$|\?)/.test(href)) href = href.replace(/(?:\?.*)?$/, ".html");
    return { url: href, title: titleEl ? titleEl.textContent.trim() : "" };
  });
  if (!target) return { ok: false, status: "job_detail_link_not_found", url: page.url() };
  await page.goto(target.url, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1800);
  return { ok: true, status: "navigated_to_detail", target };
}

async function enterChat(page) {
  const existing = await chatInput(page);
  if (existing) return { ok: true, status: "already_in_chat" };

  const candidates = page.locator("button, a, [role='button'], .btn, [class*='btn'], span, div");
  const count = await candidates.count();
  for (let i = 0; i < count; i += 1) {
    const item = candidates.nth(i);
    const text = ((await item.innerText().catch(() => "")) || "").trim();
    if (!/^(立即沟通|继续沟通|感兴趣)$/.test(text)) continue;
    if (!(await item.isVisible().catch(() => false))) continue;
    await item.click({ timeout: 3000 }).catch(() => null);
    await page.waitForTimeout(2000);
    if (await chatInput(page)) return { ok: true, status: "entered_chat", buttonText: text };
  }
  return { ok: false, status: "chat_button_not_opened", url: page.url() };
}

async function sendText(page, text) {
  const input = await chatInput(page);
  if (!input) return { ok: false, reason: "chat_input_not_found" };
  await input.click();
  await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
  await page.keyboard.type(text, { delay: 5 });
  const send = await visibleLocator(page, "button:has-text('发送'), [role='button']:has-text('发送'), div:has-text('发送'), span:has-text('发送')");
  if (send) {
    await send.click().catch(() => null);
  } else {
    await page.keyboard.press("Enter");
  }
  await page.waitForTimeout(1200);
  return { ok: true, clickedSend: Boolean(send), text };
}

async function uploadResumeImage(page, imagePath) {
  const absolute = absUserPath(imagePath);
  if (!absolute) return { ok: false, status: "resume_image_skipped", reason: "empty_path" };
  if (!fs.existsSync(absolute)) return { ok: false, status: "resume_image_manual_required", reason: "file_not_found", path: absolute };
  const input = await chatInput(page);
  if (!input) return { ok: false, status: "resume_image_manual_required", reason: "chat_input_not_found", path: absolute };

  const beforeImages = await page.locator("img").count().catch(() => 0);

  const fileInputs = page.locator("input[type='file']");
  const inputCount = await fileInputs.count();
  for (let i = 0; i < inputCount; i += 1) {
    const fileInput = fileInputs.nth(i);
    const accept = await fileInput.getAttribute("accept").catch(() => "");
    if (accept && !/image|jpg|jpeg|png|gif/i.test(accept)) continue;
    await fileInput.setInputFiles(absolute).catch(() => null);
    await page.waitForTimeout(1800);
    const afterImages = await page.locator("img").count().catch(() => 0);
    if (afterImages > beforeImages) {
      return { ok: true, status: "resume_image_sent_verified", method: "set_input_files", path: absolute };
    }
  }

  const imageButton = await visibleLocator(page, [
    ".chat-controls .btn-sendimg",
    "[class*='chat-controls'] [class*='sendimg']",
    "[class*='toolbar'] [class*='sendimg']",
    "[class*='toolbar'] [class*='image']",
    "button:has-text('图片')",
    "[role='button']:has-text('图片')",
  ].join(", "));
  if (imageButton) {
    const chooserPromise = page.waitForEvent("filechooser", { timeout: 4000 }).catch(() => null);
    await imageButton.click().catch(() => null);
    const chooser = await chooserPromise;
    if (chooser) {
      await chooser.setFiles(absolute);
      await page.waitForTimeout(1800);
      const afterImages = await page.locator("img").count().catch(() => 0);
      if (afterImages > beforeImages) {
        return { ok: true, status: "resume_image_sent_verified", method: "filechooser", path: absolute };
      }
    }
  }

  return { ok: false, status: "resume_image_manual_required", reason: "image_upload_not_verified", path: absolute };
}

async function verifyText(page, needle) {
  if (!needle) return false;
  const body = await page.locator("body").innerText().catch(() => "");
  return body.slice(-6000).includes(needle);
}

async function cmdOpenLogin() {
  const { browser, page } = await openBrowser();
  await page.goto("https://www.zhipin.com/web/geek/job", { waitUntil: "domcontentloaded" });
  console.log(JSON.stringify({ ok: true, status: "opened_login", url: page.url(), profile: USER_DATA_DIR }, null, 2));
  await disconnectBrowser(browser);
}

async function cmdExtractDetail() {
  const { browser, context, page } = await openBrowser();
  const bossPage = await findBossPage(context, page);
  console.log(JSON.stringify({ ok: true, result: await extractDetail(bossPage) }, null, 2));
  await disconnectBrowser(browser);
}

async function cmdUploadImage(args) {
  const { browser, context, page } = await openBrowser();
  const bossPage = await findBossPage(context, page);
  console.log(JSON.stringify(await uploadResumeImage(bossPage, args.resumeImage || args.path || ""), null, 2));
  await disconnectBrowser(browser);
}

async function cmdApplyCurrentJob(args) {
  const config = readConfig();
  const profile = config.user_profile || {};
  const portfolio = args.portfolio || profile.portfolio_link || "";
  const resumeImage = args.resumeImage || profile.resume_image || "";
  const { browser, context, page } = await openBrowser();
  let bossPage = await findBossPage(context, page);
  const steps = [];

  // Navigate to BOSS first to ensure login context
  await bossPage.goto("https://www.zhipin.com/web/geek/job", { waitUntil: "domcontentloaded", timeout: 15000 }).catch(() => {});
  await bossPage.waitForTimeout(3000);
  steps.push({ step: "navigate_home", result: { url: bossPage.url() } });
  
  // Then navigate to target job URL if given
  if (args.url) {
    await bossPage.goto(args.url, { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
    await bossPage.waitForTimeout(3000);
    steps.push({ step: "navigate_to_url", url: args.url, result: { url: bossPage.url() } });
  }

  // Wait for page to stabilize before evaluating
  await bossPage.waitForTimeout(1000);
  steps.push({ step: "ensure_detail_page", result: await ensureDetailPage(bossPage) });
  const detail = await extractDetail(bossPage);
  steps.push({ step: "extract_detail", result: detail });
  const chat = await enterChat(bossPage);
  steps.push({ step: "enter_chat", result: chat });
  if (!chat.ok) {
    console.log(JSON.stringify({ ok: false, status: "needs_manual_check", reason: "could_not_enter_chat_context", steps }, null, 2));
    await disconnectBrowser(browser);
    return;
  }

  const image = await uploadResumeImage(bossPage, resumeImage);
  steps.push({ step: "upload_resume_image", result: image });
  if (!image.ok) {
    console.log(JSON.stringify({ ok: false, status: image.status, reason: image.reason, steps }, null, 2));
    await disconnectBrowser(browser);
    return;
  }

  let portfolioOk = false;
  if (portfolio) {
    const sentPortfolio = await sendText(bossPage, portfolio);
    steps.push({ step: "send_portfolio", result: sentPortfolio });
    portfolioOk = await verifyText(bossPage, portfolio.includes("pan.baidu.com") ? "pan.baidu.com" : portfolio.slice(0, 18));
    steps.push({ step: "verify_portfolio", result: { verified: portfolioOk } });
  }

  const greeting = greetingFor(detail, profile);
  const sentGreeting = await sendText(bossPage, greeting);
  steps.push({ step: "send_greeting", result: sentGreeting });
  const greetingOk = await verifyText(bossPage, greeting.slice(0, 18));
  steps.push({ step: "verify_greeting", result: { verified: greetingOk } });

  console.log(JSON.stringify({
    ok: image.ok && portfolioOk && greetingOk,
    status: image.ok && portfolioOk && greetingOk ? "sent_verified" : "needs_manual_check",
    verified: { resume_image: image.ok, portfolio: portfolioOk, greeting: greetingOk },
    greeting,
    steps,
  }, null, 2));
  await disconnectBrowser(browser);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0];
  if (cmd === "open-login") return cmdOpenLogin();
  if (cmd === "extract-detail") return cmdExtractDetail();
  if (cmd === "upload-image") return cmdUploadImage(args);
  if (cmd === "apply-current-job") return cmdApplyCurrentJob(args);
  console.log(JSON.stringify({
    ok: false,
    status: "unknown_command",
    commands: ["open-login", "extract-detail", "upload-image --resume-image PATH", "apply-current-job --resume-image PATH"],
  }, null, 2));
  process.exit(1);
}

main().then(() => {
  process.exit(0);
}).catch((error) => {
  console.log(JSON.stringify({ ok: false, status: "runner_error", reason: String(error && error.stack || error) }, null, 2));
  process.exit(1);
});
