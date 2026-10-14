const path = require("path");
const SKILL_DIR = "/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto";
const nm = path.join(SKILL_DIR, "node_modules");
const { chromium } = require(path.join(nm, "playwright-core"));

const USER_DATA_DIR = path.join(require("os").homedir(), ".hermes", "boss-chrome-profile");
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const RESUME_IMAGE = "/Users/YOUR_NAME/Desktop/YOUR_RESUME_IMAGE.jpg";

const JOBS = [
  { url: "https://www.zhipin.com/job_detail/af78a47c08948edf0nFz2t-7F1JU.html", title: "COMPANY_15-视频剪辑(TVC方向)", company: "COMPANY_15" },
  // Add more jobs as needed
];

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function applyJob(page, job) {
  console.log(`\n=== Applying: ${job.title} ===`);
  
  // Navigate to job detail
  await page.goto(job.url, { waitUntil: "domcontentloaded", timeout: 15000 }).catch(() => {});
  await sleep(2000);
  console.log("URL:", page.url().slice(0, 80));
  
  // Click 立即沟通/继续沟通
  const btn = page.locator("a.btn-startchat").first();
  if (await btn.count() > 0) {
    await btn.click();
    await sleep(2000);
    console.log("Chat button clicked");
  }
  
  // Check for chat input
  const chatInput = page.locator("div.chat-input[contenteditable='true']").first();
  if (await chatInput.count() === 0) {
    console.log("No chat input - may need login. Check browser.");
    return false;
  }
  
  console.log("Chat input found!");
  
  // Upload image via file input
  const fileInputs = page.locator("input[type='file']");
  const fc = await fileInputs.count();
  for (let i = 0; i < fc; i++) {
    try {
      await fileInputs.nth(i).setInputFiles(RESUME_IMAGE);
      console.log("Image uploaded via file input #" + i);
      break;
    } catch(e) {
      console.log("File input #" + i + " failed: " + e.message.slice(0, 60));
    }
  }
  await sleep(1500);
  
  // Send greeting + portfolio
  await chatInput.click();
  const greeting = "您好，看到" + job.company + "在招聘" + (job.title.includes("-") ? job.title.split("-")[1] : "视频剪辑") + "岗位，非常感兴趣。我熟悉PR、AE、达芬奇等后期软件，有宣传片、企业视频等项目的剪辑经验。这是我的作品集：百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>。希望能有机会进一步沟通！";
  await page.keyboard.type(greeting, { delay: 3 });
  await sleep(500);
  
  // Try send
  const sendBtn = page.locator("button:has-text('发送'), div.edit-area").first();
  if (await sendBtn.count() > 0) {
    await sendBtn.click();
    console.log("Send clicked");
  } else {
    await page.keyboard.press("Enter");
    console.log("Enter pressed");
  }
  await sleep(1000);
  
  console.log("Done: " + job.title);
  return true;
}

async function main() {
  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    viewport: null,
    args: ["--start-maximized"],
    executablePath: CHROME_PATH,
  });
  
  const page = context.pages()[0] || await context.newPage();
  
  // Apply to each job
  for (const job of JOBS) {
    await applyJob(page, job);
  }
  
  console.log("\n=== All jobs processed ===");
  console.log("Check Chrome window for results.");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
