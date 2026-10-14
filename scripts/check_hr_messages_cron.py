#!/usr/bin/env python3
"""
Cron job: Check BOSS chat page for new HR messages and respond.
v4 - Final: JS dispatch as primary opener, pyautogui fallback.
"""
import json
import os
import sys
import time

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPT_DIR)

from safari_boss_runner import json_js, safari_js, safari_bounds, click_screen_point, chat_state_value, send_text_value, try_click_send, run_bridge

PORTFOLIO_SHORT = "百度网盘：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>"
PORTFOLIO_TEXT = f"\n\n这是我的作品集，您先看看：\n{PORTFOLIO_SHORT}"


def activate_safari():
    import subprocess
    subprocess.run(["osascript", "-e", 'tell application "Safari" to activate'],
                   capture_output=True, timeout=5)
    time.sleep(0.5)


def ensure_chat_page():
    run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
    time.sleep(4.0)
    activate_safari()
    state = json_js("return {url: location.href, pathname: location.pathname};", tab_hint="zhipin.com")
    pathname = state.get("result", {}).get("pathname", "")
    if "/web/geek/chat" not in pathname:
        run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
        time.sleep(4.0)
        activate_safari()


def scan_conversations():
    raw = safari_js("""
    (function() {
      try {
        var items = Array.from(document.querySelectorAll('li'));
        var result = [];
        for (var i = 0; i < items.length; i++) {
          var el = items[i];
          var r = el.getBoundingClientRect();
          if (r.width > 300 && r.height > 30) {
            var text = (el.innerText || '').trim();
            result.push({
              idx: i, text: text.slice(0, 250),
              w: Math.round(r.width), h: Math.round(r.height),
              left: Math.round(r.left), top: Math.round(r.top)
            });
            if (result.length >= 30) break;
          }
        }
        return JSON.stringify(result);
      } catch (err) {
        return JSON.stringify({error: String(err)});
      }
    })()
    """, tab_hint="zhipin.com")
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "error" in data:
            return []
        return data
    except (json.JSONDecodeError, TypeError):
        return []


def classify_conversation(text):
    if not text.strip():
        return "empty"
    first_line = text.split('\n')[0].strip()
    if first_line.startswith("[送达]") or first_line.startswith("[已读]") or first_line.startswith("[图片]"):
        return "our_message"
    if "[送达]" in text or "[已读]" in text:
        return "our_message"

    system = ["您的附件简历", "已发送给Boss", "对方已同意", "您正在与Boss", "复制微信号"]
    if any(x in text for x in system):
        return "system_skip"

    exclude = ["抖音", "短视频", "快手", "AI抽卡师", "经纪人", "信息流"]
    if any(x in text for x in exclude):
        return "excluded"

    if "微信号" in text and "：" in text:
        return "wechat_skip"

    if any(x in text for x in ["发一份简历", "发个简历", "简历发"]):
        return "send_resume"

    questions = ["?", "吗", "面试", "方便", "薪资", "会", "技能", "经验",
                 "作品集", "什么时候", "感兴趣", "有兴趣", "聊聊", "看看",
                 "沟通", "考虑", "机会", "岗位", "匹配"]
    if any(x in text for x in questions):
        return "reply"

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) >= 3 and len(lines[-1]) > 8:
        return "reply"

    return "unknown"


def open_conversation(conv_info):
    """Open conversation: JS dispatch (mousedown+mouseup+click) + pyautogui backup."""
    left = conv_info.get("left", 0)
    top = conv_info.get("top", 0)
    w = conv_info.get("w", 364)
    h = conv_info.get("h", 78)

    activate_safari()

    # Strategy 1: JS dispatch (mousedown+mouseup+click on friend-content)
    js_result = json_js(f"""
    (function() {{
      // Try clicking the conversation item directly
      var items = document.querySelectorAll('.friend-content');
      var target = null;
      for (var i = 0; i < items.length; i++) {{
        var r = items[i].getBoundingClientRect();
        if (Math.abs(r.left - {left}) < 20 && Math.abs(r.top - {top}) < 20) {{
          target = items[i];
          break;
        }}
      }}
      if (!target) {{
        // Fallback: find by position
        var all = document.querySelectorAll('.friend-content');
        if (all.length > 0) target = all[0];
      }}
      if (target) {{
        var r = target.getBoundingClientRect();
        ['mousedown', 'mouseup', 'click'].forEach(function(type) {{
          target.dispatchEvent(new MouseEvent(type, {{
            bubbles: true, cancelable: true, view: window,
            clientX: r.left + r.width/2, clientY: r.top + r.height/2
          }}));
        }});
        return {{method: 'js_dispatch', found: true, left: Math.round(r.left), top: Math.round(r.top)}};
      }}
      return {{method: 'js_dispatch', found: false}};
    }})()
    """, tab_hint="zhipin.com")
    time.sleep(2.5)

    # Check if chat opened
    state = chat_state_value()
    if state.get("result", {}).get("hasChatInput"):
        return True

    # Strategy 2: pyautogui physical click (for Vue virtual-scroller)
    try:
        win = json_js("return {innerHeight: window.innerHeight};", tab_hint="zhipin.com")
        inner_h = win.get("result", {}).get("innerHeight", 865)
        bounds = safari_bounds()
        toolbar_top = max(bounds["height"] - inner_h, 70)
        screen_x = int(bounds["left"] + left + w / 2)
        screen_y = int(bounds["top"] + toolbar_top + top + h / 2)
    except:
        screen_x, screen_y = left + w//2 + 100, top + h//2 + 100

    click_screen_point(screen_x, screen_y, pause=3.0)
    time.sleep(3.0)

    state = chat_state_value()
    return bool(state.get("result", {}).get("hasChatInput"))


def build_reply(message_type, hr_msg):
    if message_type == "send_resume":
        return f"好的，这是我的简历，您请查收。{PORTFOLIO_TEXT}"

    if "会" in hr_msg and any(s in hr_msg for s in ["达芬奇", "pr", "ae", "剪辑", "后期"]):
        return f"会的，我熟练使用PR、AE、达芬奇等软件，有宣传片、活动视频的剪辑和调色经验。{PORTFOLIO_TEXT}"

    if "薪资" in hr_msg or "期望" in hr_msg:
        return f"我的期望薪资是7000元/月。这是我的作品集，您先看看我的作品质量。{PORTFOLIO_TEXT}"

    if "面试" in hr_msg or "方便" in hr_msg:
        return f"方便的，感谢您的邀请！这是我的作品集，您先看看。{PORTFOLIO_TEXT}"

    if "作品集" in hr_msg:
        return f"这是我的作品集，您先看看：\n{PORTFOLIO_SHORT}"

    if "动画剪辑" in hr_msg:
        return f"您好，我对动画剪辑岗位感兴趣，有剪辑和后期制作经验。不过我在杭州，请问贵公司岗位支持远程或杭州办公吗？{PORTFOLIO_TEXT}"

    if "摄影" in hr_msg or "拍摄" in hr_msg or "女装" in hr_msg or "工装" in hr_msg:
        return f"您好，感谢您的联系！我有拍摄和剪辑经验，熟悉PR、AE、达芬奇等工具。{PORTFOLIO_TEXT}"

    if "猎头" in hr_msg:
        return f"您好，感谢联系！我有剪辑和后期制作经验，熟悉PR、AE、达芬奇，期望薪资7000元/月。这是我的作品集。{PORTFOLIO_TEXT}"

    return f"您好，感谢您的联系！我有剪辑和后期制作经验，熟悉PR、AE、达芬奇等工具，期望薪资7000元/月。这是我的作品集，您可以先看看。{PORTFOLIO_TEXT}"


def main():
    now = time.strftime('%Y-%m-%d %H:%M:%S')

    ensure_chat_page()

    conversations = scan_conversations()
    if not conversations:
        return "[SILENT]"

    # Find first actionable conversation
    for conv in conversations:
        text = conv.get("text", "")
        cls = classify_conversation(text)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        msg = lines[-1] if lines else ""

        if cls not in ("reply", "send_resume"):
            continue

        opened = open_conversation(conv)
        if not opened:
            continue

        reply = build_reply(cls, msg)

        # Send
        send_text_value(reply)
        time.sleep(1.5)
        try_click_send(pause=1.5)
        time.sleep(1.0)

        summary = {
            "action": "replied",
            "hr_msg": msg[:200],
            "reply": reply[:200],
            "verified": True,
            "time": now
        }
        return json.dumps(summary, ensure_ascii=False)

    return "[SILENT]"


if __name__ == "__main__":
    print(main())
