const path = require("path");
const nm = path.join("/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/node_modules");
const { chromium } = require(path.join(nm, "playwright-core"));
const UD = path.join(require("os").homedir(), ".hermes", "boss-chrome-profile");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const IMG = "/Users/YOUR_NAME/Desktop/YOUR_RESUME_IMAGE.jpg";
const PF = "百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>";

const JOBS = [
  ["https://www.zhipin.com/job_detail/af78a47c08948edf0nFz2t-7F1JU.html", "COMPANY_15", "视频剪辑(TVC方向)"],
  ["https://www.zhipin.com/job_detail/97b7773b501a11f00nF73t61GVpT.html", "无印策动", "剪辑后期"],
  ["https://www.zhipin.com/job_detail/0ff95c16abe2f66903xy09y8EFdY.html", "COMPANY_12", "视频剪辑"],
  ["https://www.zhipin.com/job_detail/e1a2c195bdd4e7531HJz39-0E1RU.html", "观予文化", "宣传片编导"],
  ["https://www.zhipin.com/job_detail/260b9adb280979c30nF_0ty6GFVQ.html", "卓融文化", "视频拍摄剪辑"],
  ["https://www.zhipin.com/job_detail/4a492bba264837f80nFy3Nu4F1pX.html", "COMPANY_13", "AI创意导演助理"],
];

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitForLogin(page) {
  console.log("Waiting for login...");
  for (let i = 0; i < 300; i++) {
    await sleep(2000);
    const url = page.url();
    if (!url.includes("/web/user/") && url.includes("zhipin.com")) {
      console.log("Login detected!");
      await sleep(1500);
      return true;
    }
  }
  return false;
}

async function applyOne(page, url, company, title) {
  console.log("\n=== " + company + " - " + title + " ===");
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
  await sleep(2500);
  
  let u = page.url();
  if (u.includes("/web/user/")) {
    console.log("Redirected to login. Need to log in again.");
    return false;
  }
  
  // Click chat
  const btn = page.locator("a.btn-startchat").first();
  if (await btn.count() === 0) {
    console.log("No chat button at:", u.slice(0, 60));
    return false;
  }
  await btn.click();
  await sleep(2500);
  
  // Upload image
  const fi = page.locator("input[type='file']").first();
  if (await fi.count() > 0) {
    try {
      await fi.setInputFiles(IMG);
      console.log("✅ Image uploaded!");
    } catch(e) {
      console.log("Image fail:", e.message.slice(0, 50));
    }
    await sleep(1500);
  }
  
  // Send greeting
  const ci = page.locator("div.chat-input[contenteditable='true']").first();
  if (await ci.count() > 0) {
    await ci.click();
    await page.keyboard.type("您好，看到" + company + "在招聘" + title + "岗位，非常感兴趣。我熟悉PR、AE、达芬奇等后期软件，有宣传片、企业视频等项目的剪辑经验。这是我的作品集：" + PF + "。希望能有机会进一步沟通！", {delay: 2});
    await sleep(500);
    const sb = page.locator("button:has-text('发送')").first();
    if (await sb.count() > 0) await sb.click();
    else await page.keyboard.press("Enter");
    console.log("✅ Greeting sent!");
  }
  await sleep(1500);
  return true;
}

async function main() {
  const ctx = await chromium.launchPersistentContext(UD, {
    headless: false, viewport: null,
    args: ["--start-maximized"],
    executablePath: CHROME,
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  
  // Go to BOSS first
  await page.goto("https://www.zhipin.com/", { waitUntil: "domcontentloaded" });
  await sleep(2000);
  
  if (page.url().includes("/web/user/")) {
    console.log("Please log in to BOSS直聘 in the Chrome window that just opened.");
    const loggedIn = await waitForLogin(page);
    if (!loggedIn) {
      console.log("Login timeout. Please restart.");
      return;
    }
  } else {
    console.log("Already logged in!");
  }
  
  // Apply to all jobs
  for (const [url, company, title] of JOBS) {
    await applyOne(page, url, company, title);
  }
  
  console.log("\n✅ All jobs processed! Check Chrome window.");
}

main().catch(e => console.error("Error:", e.message));
