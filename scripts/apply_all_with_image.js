const path = require("path");
const nm = path.join("/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/node_modules");
const { chromium } = require(path.join(nm, "playwright-core"));
const UD = path.join(require("os").homedir(), ".hermes", "boss-chrome-profile");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const IMG = "/Users/YOUR_NAME/Desktop/YOUR_RESUME_IMAGE.jpg";
const PF = "百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>";

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function applyJob(page, url, company, title) {
  console.log("\n=== " + company + " - " + title + " ===");
  await page.goto(url, { waitUntil: "networkidle", timeout: 20000 }).catch(() => {});
  await sleep(3000);
  
  let u = page.url();
  console.log("URL:", u.slice(0, 80));
  if (u.includes("/web/user/")) {
    console.log("Need login - stopping");
    return false;
  }
  
  // Click chat
  const btn = page.locator("a.btn-startchat");
  if (await btn.count() === 0) {
    console.log("No chat button");
    return false;
  }
  await btn.click();
  await sleep(2500);
  
  // Upload image
  const fi = page.locator("input[type='file']").first();
  if (await fi.count() > 0) {
    try {
      await fi.setInputFiles(IMG);
      console.log("✅ Image set!");
    } catch(e) {
      console.log("Image fail:", e.message.slice(0, 50));
    }
    await sleep(1500);
  }
  
  // Send greeting
  const ci = page.locator("div.chat-input[contenteditable='true']").first();
  if (await ci.count() > 0) {
    await ci.click();
    await page.keyboard.type("您好，看到" + company + "在招聘" + title + "岗位，非常感兴趣。我熟悉PR、AE、达芬奇等后期软件，有宣传片、企业视频等项目的剪辑经验。这是我的作品集：" + PF + "。希望能有机会进一步沟通！", {delay: 3});
    await sleep(500);
    const sb = page.locator("button:has-text('发送')").first();
    if (await sb.count() > 0) { await sb.click(); console.log("✅ Sent!"); }
    else { await page.keyboard.press("Enter"); console.log("✅ Enter sent!"); }
  }
  return true;
}

async function main() {
  console.log("Launching Chrome...");
  const ctx = await chromium.launchPersistentContext(UD, {
    headless: false, viewport: null,
    args: ["--start-maximized"],
    executablePath: CHROME,
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  console.log("Chrome launched!");
  
  // First go to BOSS home 
  await page.goto("https://www.zhipin.com/web/geek/job", { waitUntil: "domcontentloaded", timeout: 15000 }).catch(() => {});
  await sleep(4000);
  console.log("After home nav:", page.url().slice(0, 80));
  
  if (page.url().includes("/web/user/")) {
    console.log("LOGIN REQUIRED - Please log in in the Chrome window!");
    for (let i = 0; i < 300; i++) {
      await sleep(2000);
      const u = page.url();
      if (!u.includes("/web/user/") && u.includes("zhipin.com")) {
        console.log("Login detected!");
        break;
      }
    }
  }
  
  const JOBS = [
    ["https://www.zhipin.com/job_detail/af78a47c08948edf0nFz2t-7F1JU.html", "COMPANY_15", "视频剪辑(TVC方向)"],
    ["https://www.zhipin.com/job_detail/97b7773b501a11f00nF73t61GVpT.html", "无印策动", "剪辑后期"],
    ["https://www.zhipin.com/job_detail/0ff95c16abe2f66903xy09y8EFdY.html", "COMPANY_12", "视频剪辑"],
    ["https://www.zhipin.com/job_detail/e1a2c195bdd4e7531HJz39-0E1RU.html", "观予文化", "宣传片编导"],
  ];
  
  for (const [u, c, t] of JOBS) {
    const ok = await applyJob(page, u, c, t);
    if (!ok) break;
    await sleep(2000);
  }
  
  console.log("\n✅ All done! Check Chrome window.");
}

main().catch(e => console.error("Error:", e.message));
