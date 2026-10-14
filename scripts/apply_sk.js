const path = require("path");
const SKILL_DIR = "/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto";
const nm = path.join(SKILL_DIR, "node_modules");
const { chromium } = require(path.join(nm, "playwright-core"));

const USER_DATA_DIR = path.join(require("os").homedir(), ".hermes", "boss-chrome-profile");
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

async function main() {
  const jobUrl = "https://www.zhipin.com/job_detail/af78a47c08948edf0nFz2t-7F1JU.html";
  const resumeImage = "/Users/YOUR_NAME/Desktop/YOUR_RESUME_IMAGE.jpg";
  
  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    viewport: null,
    args: ["--start-maximized"],
    executablePath: CHROME_PATH,
  });
  
  const page = context.pages()[0] || await context.newPage();
  
  // Navigate to job detail page
  await page.goto(jobUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  console.log("Navigated to:", page.url());
  
  // Find and click 立即沟通/继续沟通
  const chatBtn = page.locator("a.btn-startchat");
  if (await chatBtn.count() > 0) {
    await chatBtn.first().click();
    await page.waitForTimeout(2000);
    console.log("Clicked chat button");
  }
  
  // Check if we're in chat context
  const chatInput = page.locator("div.chat-input[contenteditable='true']").first();
  if (await chatInput.count() === 0) {
    console.log("No chat input found, checking page...");
    console.log("URL:", page.url());
  } else {
    console.log("In chat context");
    
    // Upload image via file input
    const fileInput = page.locator("input[type='file']").first();
    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(resumeImage);
      await page.waitForTimeout(2000);
      console.log("Image file set via input");
    }
    
    // Send greeting with portfolio
    await chatInput.click();
    const text = "您好，看到COMPANY_15在招聘视频剪辑岗位，TVC/品牌实拍/纪实方向正是我关注的方向。我熟悉PR、AE、达芬奇等后期软件，有宣传片、企业视频等项目的剪辑经验。这是我的作品集：百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>。希望能有机会进一步沟通！";
    await page.keyboard.type(text, { delay: 3 });
    await page.waitForTimeout(500);
    
    // Click send
    const sendBtn = page.locator("button.btn-send, div.btn-send, button:has-text('发送')").first();
    if (await sendBtn.count() > 0) {
      await sendBtn.click();
    } else {
      await page.keyboard.press("Enter");
    }
    console.log("Message sent");
  }
  
  console.log("Done! Check the Chrome window.");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
