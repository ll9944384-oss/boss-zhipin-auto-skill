#!/usr/bin/env node
/*
 * Liepin runner for the unified job application skill.
 *
 * It uses a visible local Edge/Chrome session through Playwright CDP. It does not
 * bypass CAPTCHA, login checks, rate limits, or platform controls. If Liepin
 * asks for manual verification, stop and let the user handle it in the browser.
 */

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

function loadPlaywright() {
  try {
    return require("playwright-core");
  } catch {
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
const USER_DATA_DIR = path.join(os.homedir(), ".hermes", "job-apply-browser-profile");
const CDP_PORT = 9224;
const CDP_ENDPOINT = `http://127.0.0.1:${CDP_PORT}`;

function readConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
  } catch {
    return {};
  }
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
    if (!next || next.startsWith("--")) args[key] = true;
    else {
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
          if (res.statusCode >= 200 && res.statusCode < 300) resolve(body);
          else if (Date.now() - started > timeoutMs) reject(new Error(`CDP not ready: ${res.statusCode}`));
          else setTimeout(tick, 300);
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

async function ensureChromeRunning(startUrl = "https://www.liepin.com", preferredBrowser = "") {
  try {
    await waitForCdp(800);
    return { started: false, endpoint: CDP_ENDPOINT };
  } catch {
    // Start a normal, visible Chrome process that the user can inspect.
  }

  const browserPath = resolveBrowserExecutable(preferredBrowser);
  fs.mkdirSync(USER_DATA_DIR, { recursive: true });
  const child = spawn(browserPath, [
    `--remote-debugging-port=${CDP_PORT}`,
    `--user-data-dir=${USER_DATA_DIR}`,
    "--no-first-run",
    "--no-default-browser-check",
    startUrl,
  ], { detached: true, stdio: "ignore" });
  child.unref();
  await waitForCdp(10000);
  return { started: true, endpoint: CDP_ENDPOINT, profile: USER_DATA_DIR, browser: browserName(browserPath), executable: browserPath };
}

async function openBrowser(startUrl, preferredBrowser = "") {
  await ensureChromeRunning(startUrl, preferredBrowser);
  const browser = await chromium.connectOverCDP(CDP_ENDPOINT);
  const context = browser.contexts()[0] || await browser.newContext();
  const pages = context.pages();
  const page = pages.find((p) => /liepin\.com/.test(p.url())) || pages[0] || await context.newPage();
  return { browser, context, page };
}

async function disconnect(browser) {
  if (browser && typeof browser.disconnect === "function") await browser.disconnect();
}

function searchUrl(keyword) {
  const encoded = encodeURIComponent(keyword || "");
  return encoded ? `https://www.liepin.com/zhaopin/?key=${encoded}` : "https://www.liepin.com";
}

function liepinCityCode(config, args) {
  return args.cityCode || config.platforms?.liepin?.city_code || "";
}

function liepinCityName(config, args) {
  return args.city || args.cityName || config.search_params?.city_name || config.user_profile?.location || "";
}

async function readCityState(page, cityCode, cityName) {
  return page.evaluate(({ code, name }) => {
    const url = new URL(location.href);
    const city = url.searchParams.get("city") || "";
    const dq = url.searchParams.get("dq") || "";
    const normalize = (text) => String(text || "").replace(/\s+/g, " ").trim();
    const candidates = Array.from(document.querySelectorAll(
      "[class*='city'], [class*='location'], [class*='area'], [data-selector*='city'], [aria-label*='城市']"
    )).filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    }).map((node) => normalize(node.innerText || node.textContent || "")).filter(Boolean).slice(0, 30);
    const urlMatched = Boolean(code) && (city === code || dq === code);
    const labelMatched = Boolean(name) && candidates.some((text) => text === name || text.startsWith(`${name} `));
    return { url: location.href, city, dq, cityCode: code, cityName: name, urlMatched, labelMatched, candidates };
  }, { code: cityCode, name: cityName });
}

async function tryCityPicker(page, cityName) {
  if (!cityName) return { ok: false, status: "city_picker_skipped", reason: "missing_city_name" };
  const triggerSelectors = [
    "[class*='city'] [role='button']",
    "[class*='city'] button",
    "[class*='city']",
    "[class*='location']",
    "[data-selector*='city']",
  ];
  let trigger = null;
  for (const selector of triggerSelectors) {
    const items = page.locator(selector);
    for (let i = 0; i < Math.min(await items.count(), 30); i += 1) {
      const item = items.nth(i);
      if (!(await item.isVisible().catch(() => false))) continue;
      const text = (await item.innerText().catch(() => "")).replace(/\s+/g, " ").trim();
      if (text.length <= 40 && /\u5168\u56fd|\u57ce\u5e02|\u5730\u70b9|\u5730\u533a/.test(text)) { trigger = item; break; }
    }
    if (trigger) break;
  }
  if (!trigger) return { ok: false, status: "city_picker_trigger_not_found" };
  await trigger.click().catch(() => {});
  await page.waitForTimeout(500);

  const overlay = page.locator("[role='dialog']:visible, .ant-modal:visible, .ant-popover:visible, [class*='city']:visible").last();
  const scope = await overlay.isVisible().catch(() => false) ? overlay : page;
  const search = scope.locator("input[placeholder*='\u57ce\u5e02'], input[placeholder*='\u641c\u7d22'], input[type='search']").first();
  if (await search.isVisible({ timeout: 800 }).catch(() => false)) {
    await search.fill(cityName);
    await page.waitForTimeout(500);
  }
  const option = scope.getByText(cityName, { exact: true }).last();
  if (!(await option.isVisible({ timeout: 1200 }).catch(() => false))) {
    return { ok: false, status: "city_picker_option_not_found", cityName };
  }
  await option.click();
  await page.waitForTimeout(500);
  const confirm = scope.getByText(/\u786e\u5b9a|\u5b8c\u6210/, { exact: true }).last();
  if (await confirm.isVisible({ timeout: 500 }).catch(() => false)) await confirm.click();
  await page.waitForTimeout(1200);
  return { ok: true, status: "city_picker_clicked", cityName };
}

async function applyCityInsideSearchPage(page, cityCode, cityName) {
  if ((!cityCode && !cityName) || !/\/zhaopin\//.test(page.url())) {
    return { ok: false, status: "city_not_applied", reason: "missing_city_or_not_search_page" };
  }
  const before = page.url();
  let target = before;
  if (cityCode) {
    target = await page.evaluate((code) => {
      const url = new URL(location.href);
      url.searchParams.set("city", code);
      url.searchParams.set("dq", code);
      location.assign(url.toString());
      return url.toString();
    }, cityCode);
    await page.waitForLoadState("domcontentloaded").catch(() => {});
    await page.waitForTimeout(1800);
    const state = await readCityState(page, cityCode, cityName);
    if (state.urlMatched || state.labelMatched) {
      return { ok: true, status: "city_verified", method: "url_params", cityCode, cityName, before, target, state };
    }
  }

  const picker = await tryCityPicker(page, cityName);
  const state = await readCityState(page, cityCode, cityName);
  const ok = state.urlMatched || state.labelMatched;
  return {
    ok,
    status: ok ? "city_verified" : "city_selection_failed",
    method: "ui_picker",
    cityCode,
    cityName,
    before,
    target,
    picker,
    state,
    reason: ok ? undefined : "city_not_confirmed_after_url_and_picker_attempts",
  };
}

async function cmdOpenSearch(args) {
  const config = readConfig();
  const keyword = args.keyword || config.search_params?.keyword || args._[1] || "";
  const cityCode = liepinCityCode(config, args);
  const cityName = liepinCityName(config, args);
  const url = searchUrl(keyword);
  const { browser, page } = await openBrowser(url);
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1800);
  const city = await applyCityInsideSearchPage(page, cityCode, cityName);
  console.log(JSON.stringify({ ok: city.ok, status: city.ok ? "opened" : "city_selection_failed", platform: "liepin", keyword, city, url: page.url() }, null, 2));
  await disconnect(browser);
}

async function cmdSetCity(args) {
  const config = readConfig();
  const cityCode = liepinCityCode(config, args);
  const cityName = liepinCityName(config, args);
  const { browser, page } = await openBrowser(searchUrl(args.keyword || config.search_params?.keyword || ""));
  if (!/\/zhaopin\//.test(page.url())) {
    await page.goto(searchUrl(args.keyword || config.search_params?.keyword || ""), { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
  }
  const result = await applyCityInsideSearchPage(page, cityCode, cityName);
  console.log(JSON.stringify({ ok: result.ok, status: result.status, platform: "liepin", result }, null, 2));
  await disconnect(browser);
}

async function cmdNavigate(args) {
  const url = args.url || args._[1] || "https://www.liepin.com";
  const { browser, page } = await openBrowser(url);
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1600);
  console.log(JSON.stringify({ ok: true, status: "navigated", platform: "liepin", url: page.url() }, null, 2));
  await disconnect(browser);
}

async function extractCardsValue(page) {
  return page.evaluate(() => {
    const normalize = (text) => String(text || "").replace(/\s+/g, " ").trim();
    const anchors = Array.from(document.querySelectorAll("a[href]"));
    const seen = new Set();
    const cards = [];
    for (const a of anchors) {
      const href = a.href || "";
      const text = normalize(a.innerText || a.textContent || "");
      if (!/liepin\.com\/(?:a\/)?job\//.test(href) && !/\/job\/\d+/.test(href)) continue;
      if (!text || text.length < 2 || text.length > 80) continue;
      const container = a.closest("[class*='job'], [class*='card'], li, article, section, div") || a.parentElement;
      const allText = normalize(container ? container.innerText : text);
      const key = `${href}|${text}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const salary = (allText.match(/\d+\s*-\s*\d+\s*k|\d+\s*-\s*\d+\s*K|\d+\s*k|\d+\s*K|面议/i) || [""])[0];
      cards.push({
        idx: cards.length,
        title: text,
        url: href,
        salary,
        text: allText.slice(0, 500),
      });
      if (cards.length >= 30) break;
    }
    return { url: location.href, count: cards.length, cards };
  });
}

async function cmdExtractCards() {
  const { browser, page } = await openBrowser("https://www.liepin.com");
  const result = await extractCardsValue(page);
  console.log(JSON.stringify({ ok: true, result }, null, 2));
  await disconnect(browser);
}

async function cmdOpenDetail(args) {
  const index = Number(args.index ?? args._[1] ?? 0);
  const { browser, page } = await openBrowser("https://www.liepin.com");
  const cards = await extractCardsValue(page);
  const target = cards.cards?.[index];
  if (!target) {
    console.log(JSON.stringify({ ok: false, status: "card_index_not_found", index, cards }, null, 2));
    await disconnect(browser);
    return;
  }
  await page.goto(target.url, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1800);
  const detail = await extractDetailValue(page);
  console.log(JSON.stringify({ ok: true, status: "detail_opened", index, target, detail }, null, 2));
  await disconnect(browser);
}

async function extractDetailValue(page) {
  return page.evaluate(() => {
    const normalize = (text) => String(text || "").replace(/\s+/g, " ").trim();
    const body = document.body.innerText || "";
    const pageText = normalize(body);
    const titleFromText = (pageText.match(/(?:^|\s)([\u4e00-\u9fa5A-Za-z0-9+（）()\/-]{2,40})\s+\d+\s*-\s*\d+\s*k/i) || [])[1] || "";
    const rawTitle = normalize(
      (document.querySelector("h1, [class*='job-title'], [class*='title']") || {}).textContent || ""
    );
    const title = /邀请|应聘|登录|投递|收藏/.test(rawTitle) ? titleFromText : (rawTitle || titleFromText);
    const company = normalize(
      (document.querySelector("[class*='company'] a, [class*='company'], a[href*='/company/']") || {}).textContent || ""
    );
    const salary = (body.match(/\d+\s*-\s*\d+\s*k|\d+\s*-\s*\d+\s*K|\d+\s*k|\d+\s*K|面议/i) || [""])[0];
    const jdNode = document.querySelector(
      "[class*='job-intro'], [class*='job-desc'], [class*='description'], [class*='require'], [class*='content']"
    );
    const nodeText = normalize((jdNode ? jdNode.innerText : "") || "");
    const jdFromBody = (
      pageText.match(/(岗位职责[:：][\s\S]{80,}?)(?:公司简介|猎聘温馨提示|猜你喜欢|职位地址|数据来源)/)
      || pageText.match(/(职位介绍[\s\S]{80,}?)(?:公司简介|猎聘温馨提示|猜你喜欢|职位地址|数据来源)/)
      || []
    )[1] || "";
    const jdText = (jdFromBody || (nodeText.length > 80 ? nodeText : pageText)).slice(0, 5000);
    const loginNeeded = /登录|验证码|扫码/.test(body) && !/职位描述|岗位职责|任职要求/.test(body);
    return {
      url: location.href,
      title,
      company: company.replace(/^·\s*/, ""),
      salary,
      jdText,
      text: pageText.slice(0, 6000),
      loginNeeded,
    };
  });
}

async function cmdExtractDetail() {
  const { browser, page } = await openBrowser("https://www.liepin.com");
  const result = await extractDetailValue(page);
  console.log(JSON.stringify({ ok: true, result }, null, 2));
  await disconnect(browser);
}

function normalizeTerms(items) {
  if (!items) return [];
  if (typeof items === "string") return items.split(/[、,，/|\n]+/).map((s) => s.trim()).filter(Boolean);
  return items.map((s) => String(s).trim()).filter(Boolean);
}

function configuredAliases(config, key) {
  return (config.greeting_rules?.[key] || []).map((item) => {
    const label = String(item.label || "").trim();
    const aliases = normalizeTerms(item.aliases);
    return { label, aliases: [...aliases, label].filter(Boolean) };
  }).filter((item) => item.label);
}

function includesTerm(text, term) {
  return term && String(text || "").toLowerCase().includes(String(term).toLowerCase());
}

function pickMatches(jdText, profile, config) {
  const jd = jdText || "";
  const skills = [];
  const needs = [];
  const profileHits = [];
  const skillAliases = [
    ...configuredAliases(config, "universal_skill_aliases"),
    ...normalizeTerms(profile.skills).map((skill) => ({ label: skill, aliases: [skill] })),
    ...normalizeTerms(profile.industry_keywords).map((kw) => ({ label: kw, aliases: [kw] })),
  ];
  for (const item of skillAliases) {
    if (item.aliases.some((alias) => includesTerm(jd, alias)) && !skills.includes(item.label)) skills.push(item.label);
  }
  for (const item of configuredAliases(config, "universal_need_aliases")) {
    if (item.aliases.some((alias) => includesTerm(jd, alias)) && !needs.includes(item.label)) needs.push(item.label);
  }
  for (const item of [...normalizeTerms(profile.experience_highlights), ...normalizeTerms(profile.transferable_skills)]) {
    if (includesTerm(jd, item) && !profileHits.includes(item)) profileHits.push(item);
  }
  return {
    skills: (skills.length ? skills : normalizeTerms(profile.skills)).slice(0, 4),
    needs: needs.slice(0, 4),
    profileHits: (profileHits.length ? profileHits : normalizeTerms(profile.strengths)).slice(0, 4),
  };
}

function compactText(text, maxLen) {
  const value = String(text || "").replace(/\s+/g, " ").trim();
  if (value.length <= maxLen) return value;
  const cut = value.slice(0, maxLen).trim();
  const sentenceEnd = Math.max(cut.lastIndexOf("。"), cut.lastIndexOf("！"), cut.lastIndexOf("？"));
  if (sentenceEnd >= maxLen * 0.65) return cut.slice(0, sentenceEnd + 1);
  const commaEnd = Math.max(cut.lastIndexOf("，"), cut.lastIndexOf("；"));
  if (commaEnd >= maxLen * 0.65) return `${cut.slice(0, commaEnd).replace(/[，；、\s]+$/, "")}。`;
  return `${cut.replace(/[，；、\s]+$/, "")}。`;
}

function buildGreeting(detail, config) {
  const profile = config.user_profile || {};
  const maxChars = Number(config.greeting_rules?.max_chars || 220);
  const title = detail.title || profile.job_title || profile.target_role || "这个岗位";
  const company = detail.company || "贵公司";
  const matches = pickMatches(detail.jdText || detail.text || "", profile, config);
  const skillText = [...new Set([...matches.skills, ...normalizeTerms(profile.transferable_skills)])].slice(0, 4).join("、")
    || "沟通理解、信息整理、执行推进、复盘优化";
  const needText = matches.needs.length ? matches.needs.slice(0, 3).join("、") : "执行质量、沟通配合和结果落地";
  const profileText = matches.profileHits.length ? `，优势在${matches.profileHits.slice(0, 3).join("、")}` : "";
  const business = matches.skills.length ? matches.skills.slice(0, 3).join("、") : "岗位要求";
  return compactText(
    `您好，看到${company}在招聘${title}，我认真看了JD，重点应该在${business}。` +
    `我理解这个岗位核心不是简单完成动作，而是把${needText}真正做好。` +
    `我这边能匹配的是${skillText}${profileText}。` +
    `我做事会先对齐目标和交付标准，再按优先级推进，过程中及时反馈关键进展。希望有机会进一步沟通。`,
    maxChars
  );
}

async function cmdGenerateGreeting() {
  const config = readConfig();
  const { browser, page } = await openBrowser("https://www.liepin.com");
  const detail = await extractDetailValue(page);
  console.log(JSON.stringify({ ok: true, greeting: buildGreeting(detail, config), detail }, null, 2));
  await disconnect(browser);
}

async function visibleButtonByText(page, texts) {
  const selectors = "button, a, [role='button'], .btn, [class*='btn'], span, div";
  const loc = page.locator(selectors);
  const count = await loc.count();
  for (let i = 0; i < Math.min(count, 500); i += 1) {
    const item = loc.nth(i);
    const visible = await item.isVisible().catch(() => false);
    if (!visible) continue;
    const text = (await item.innerText().catch(() => "")).replace(/\s+/g, " ").trim();
    if (!text || text.length > 30) continue;
    if (texts.some((target) => text === target || text.includes(target))) return { item, text };
  }
  return null;
}

async function findChatInput(page) {
  const selectors = [
    "textarea.ant-im-input",
    "textarea",
    "input[type='text']",
    "[contenteditable='true']",
    "[class*='textarea']",
    "[class*='input']",
  ].join(", ");
  const loc = page.locator(selectors);
  const count = await loc.count();
  for (let i = 0; i < Math.min(count, 80); i += 1) {
    const item = loc.nth(i);
    if (await item.isVisible().catch(() => false)) return item;
  }
  return null;
}

async function handleResumeModal(page) {
  const modal = page.locator(".select-resume-modal-container").first();
  if (!(await modal.isVisible({ timeout: 1200 }).catch(() => false))) {
    return { ok: false, status: "resume_modal_not_present" };
  }
  const button = modal.locator("button, .ant-btn, [role='button']").filter({ hasText: /立即投递|确认投递|投递|确定/ }).first();
  if (!(await button.isVisible({ timeout: 1500 }).catch(() => false))) {
    return { ok: false, status: "resume_modal_button_not_found" };
  }
  const text = (await button.innerText().catch(() => "")).replace(/\s+/g, " ").trim();
  await button.click();
  await page.waitForTimeout(1800);
  return { ok: true, status: "resume_modal_submitted", buttonText: text };
}

async function findSendButton(page) {
  const primary = page.locator("button.ant-im-btn-primary.im-ui-basic").filter({ hasText: /发送/ }).first();
  if (await primary.isVisible({ timeout: 1200 }).catch(() => false)) return { item: primary, text: "发送" };
  const textNode = page.locator("text=发送").first();
  if (await textNode.isVisible({ timeout: 1200 }).catch(() => false)) {
    const button = textNode.locator("xpath=ancestor::button[contains(@class,'ant-im-btn-primary') or contains(@class,'im-ui-basic')][1]");
    if (await button.isVisible({ timeout: 1200 }).catch(() => false)) return { item: button, text: "发送" };
  }
  return visibleButtonByText(page, ["发送", "发 送"]);
}

async function sendGreetingInChat(page, greeting) {
  const modalResult = await handleResumeModal(page);
  const input = await findChatInput(page);
  if (!input) return { ok: false, status: "chat_input_not_found", resumeModal: modalResult };
  await input.click();
  await page.keyboard.insertText(greeting);
  await page.waitForTimeout(300);
  const send = await findSendButton(page);
  if (send) {
    await send.item.click();
    await page.waitForTimeout(1000);
    return { ok: true, status: "sent_by_button", buttonText: send.text, resumeModal: modalResult };
  }
  await page.keyboard.press("Enter");
  await page.waitForTimeout(1000);
  return { ok: true, status: "sent_by_enter", resumeModal: modalResult };
}

async function maybeOpenFirstDetail(page) {
  if (/liepin\.com\/(?:a\/)?job\//.test(page.url())) return { ok: true, status: "already_detail", url: page.url() };
  const cards = await extractCardsValue(page);
  const first = cards.cards?.[0];
  if (!first) return { ok: false, status: "job_card_not_found", cards };
  await page.goto(first.url, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1800);
  return { ok: true, status: "opened_first_detail", target: first, url: page.url() };
}

async function cmdApplyCurrentJob(args) {
  const config = readConfig();
  const { browser, page } = await openBrowser("https://www.liepin.com");
  const steps = [];
  const detailState = await maybeOpenFirstDetail(page);
  steps.push({ step: "ensure_detail", result: detailState });
  if (!detailState.ok) {
    console.log(JSON.stringify({ ok: false, status: "detail_required", steps }, null, 2));
    await disconnect(browser);
    return;
  }

  const detail = await extractDetailValue(page);
  steps.push({ step: "extract_detail", result: detail });
  if (detail.loginNeeded) {
    console.log(JSON.stringify({ ok: false, status: "login_or_verification_required", detail, steps }, null, 2));
    await disconnect(browser);
    return;
  }

  const greeting = args.greeting || buildGreeting(detail, config);
  const chat = await visibleButtonByText(page, ["继续聊", "聊一聊", "沟通", "联系TA", "立即沟通"]);
  let greetingStatus = { ok: false, status: "chat_button_not_found" };
  let modalApplyStatus = { ok: false, status: "resume_modal_not_attempted" };
  if (chat) {
    await chat.item.click();
    await page.waitForTimeout(1800);
    modalApplyStatus = await handleResumeModal(page);
    if (modalApplyStatus.ok) await page.waitForTimeout(1600);
    greetingStatus = await sendGreetingInChat(page, greeting);
  }
  steps.push({ step: "send_greeting", result: greetingStatus, modalApplyStatus, text: greeting });

  await page.bringToFront();
  const apply = await visibleButtonByText(page, ["投简历", "立即投递", "申请职位", "投递简历"]);
  let applyStatus = modalApplyStatus.ok
    ? { ok: true, status: "apply_submitted_from_resume_modal", verified: false }
    : { ok: false, status: "apply_button_not_found" };
  if (apply) {
    await apply.item.click();
    await page.waitForTimeout(1800);
    const confirm = await visibleButtonByText(page, ["确认投递", "确定", "继续投递", "投递"]);
    if (confirm) {
      await confirm.item.click();
      await page.waitForTimeout(1800);
    }
    const body = await page.locator("body").innerText().catch(() => "");
    const verified = /已投递|投递成功|申请成功|简历已投递/.test(body);
    applyStatus = { ok: true, status: verified ? "apply_verified" : "apply_clicked_needs_check", buttonText: apply.text, verified };
  }
  steps.push({ step: "apply_resume", result: applyStatus });

  const finalStatus = greetingStatus.ok && applyStatus.verified
    ? "sent_verified"
    : greetingStatus.ok || applyStatus.ok
      ? "partial_needs_manual_check"
      : "needs_manual_apply";
  console.log(JSON.stringify({
    ok: finalStatus === "sent_verified",
    status: finalStatus,
    platform: "liepin",
    detail,
    greeting,
    verified: { greeting: Boolean(greetingStatus.ok), resume: Boolean(applyStatus.verified) },
    steps,
  }, null, 2));
  await disconnect(browser);
}

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const args = parseArgs(rest);
  try {
    if (cmd === "open-search") await cmdOpenSearch(args);
    else if (cmd === "set-city") await cmdSetCity(args);
    else if (cmd === "navigate") await cmdNavigate(args);
    else if (cmd === "extract-cards") await cmdExtractCards(args);
    else if (cmd === "open-detail") await cmdOpenDetail(args);
    else if (cmd === "extract-detail") await cmdExtractDetail(args);
    else if (cmd === "generate-greeting") await cmdGenerateGreeting(args);
    else if (cmd === "apply-current-job") await cmdApplyCurrentJob(args);
    else {
      console.log(JSON.stringify({
        ok: false,
        status: "unknown_command",
        commands: ["open-search", "set-city", "navigate", "extract-cards", "open-detail", "extract-detail", "generate-greeting", "apply-current-job"],
      }, null, 2));
      process.exitCode = 2;
    }
  } catch (error) {
    console.log(JSON.stringify({ ok: false, status: "runner_error", error: String(error && error.stack || error) }, null, 2));
    process.exitCode = 1;
  }
}

main().then(() => {
  process.exit(process.exitCode || 0);
});
