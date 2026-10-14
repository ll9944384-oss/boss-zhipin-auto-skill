const path = require("path");
const SKILL_DIR = "/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto";
const nm = path.join(SKILL_DIR, "node_modules");
const { chromium } = require(path.join(nm, "playwright-core"));
const USER_DATA_DIR = path.join(require("os").homedir(), ".hermes", "boss-chrome-profile");
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const RESUME = "/Users/YOUR_NAME/Desktop/YOUR_RESUME_IMAGE.jpg";
const PORTFOLIO = "百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>";

// Jobs to apply
const JOBS = [
  { url: "https://www.zhipin.com/job_detail/af78a47c08948edf0nFz2t-7F1JU.html", company: "COMPANY_15", title: "视频剪辑(TVC方向)" },
  { url: "https://www.zhipin.com/job_detail/97b7773b501a11f00nF73t61GVpT.html", company: "无印策动", title: "剪辑后期" },
  { url: "https://www.zhipin.com/job_detail/0ff95c16abe2f66903xy09y8EFdY.html", company: "COMPANY_12", title: "视频剪辑" },
  { url: "https://www.zhipin.com/job_detail/e1a2c195bdd4e7531HJz39-0E1RU.html", company: "观予文化", title: "宣传片编导" },
  { url: "https://www.zhipin.com/job_detail/260b9adb280979c30nF_0ty6GFVQ.html", company: "卓融文化", title: "视频拍摄剪辑" },
  { url: "https://www.zhipin.com/job_detail/4a492bba264837f80nFy3Nu4F1pX.html", company: "COMPANY_13", title: "AI创意导演助理" },
];

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function applyJob(page, job) {
  console.log("\n=== " + job.company + " - " + job.title + " ===");
  
  // Navigate to job detail
  await page.goto(job.url, { waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
  await sleep(2000);
  
  // Reload if redirected to login
  const url = page.url();
  if (url.includes("/web/user/")) {
    console.log("Login required, waiting...");
    // Wait for login by polling
    for (let i = 0; i < 180; i++) {
      await sleep(2000);
      const u = page.url();
      if (!u.includes("/web/user/")) {
        console.log("Login detected!");
        await page.goto(job.url, { waitUntil: "domcontentloaded" }).catch(() => {});
        await sleep(2000);
        break;
      }
    }
  }
  
  console.log("URL:", (page.url() || "").slice(0, 80));
  
  // Click chat button
  const btn = page.locator("a.btn-startchat").first();
  if (await btn.count() > 0) {
    await btn.first().click();
    await sleep(2000);
    console.log("Chat clicked");
  }
  
  // Upload resume image
  const fileInput = page.locator("input[type='file']").first();
  if (await fileInput.count() > 0) {
    try {
      await fileInput.setInputFiles(RESUME);
      console.log("Image uploaded!");
    } catch(e) {
      console.log("Image upload failed:", e.message.slice(0, 60));
    }
    await sleep(1500);
  }
  
  // Check chat context
  const chatInput = page.locator("div.chat-input[contenteditable='true']").first();
  if (await chatInput.count() === 0) {
    console.log("No chat input - skipped");
    return;
  }
  
  // Send greeting with portfolio
  await chatInput.click();
  const greeting = "您好，看到" + job.company + "在招聘" + job.title + "岗位，非常感兴趣。我熟悉PR、AE、达芬奇等后期软件，有宣传片、企业视频等项目的剪辑经验。这是我的作品集：" + PORTFOLIO + "。希望能有机会进一步沟通！";
  await page.keyboard.type(greeting, { delay: 3 });
  await sleep(800);
  
  const sendBtn = page.locator("button:has-text('发送'), div:has-text('发送')").first();
  if (await sendBtn.count() > 0) {
    await sendBtn.first().click();
    console.log("Sent!");
  } else {
    await page.keyboard.press("Enter");
    console.log("Enter sent");
  }
  await sleep(1000);
}

async function main() {
  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false, viewport: null,
    args: ["--start-maximized"],
    executablePath: CHROME_PATH,
  });
  const page = context.pages()[0] || await context.newPage();
  
  // Start at jobs page
  await page.goto("https://www.zhipin.com/web/geek/job", { waitUntil: "domcontentloaded" });
  console.log("Opened BOSS. Please log in if needed.");
  
  // Check if already logged in
  await sleep(2000);
  const firstUrl = page.url();
  if (firstUrl.includes("/web/user/")) {
    console.log("Waiting for login in Chrome window...");
  } else {
    console.log("Already logged in!");
  }
  
  // Apply to first job only for now
  await applyJob(page, JOBS[0]);
  
  console.log("\nDone! Check the Chrome window.");
}

main().catch(e => console.error("Error:", e.message));
