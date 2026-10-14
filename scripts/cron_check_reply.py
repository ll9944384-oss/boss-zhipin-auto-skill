#!/usr/bin/env python3
"""
Cron job: Check for new HR messages on BOSS直聘 chat page and reply.
Only processes the single latest unread HR-initiated message.

IMPORTANT: Due to Vue SPA trusted event barrier, conversations cannot be
opened programmatically. We can ONLY reply if a conversation is already open
(hasChatInput=true) from a previous session.
"""
import json
import sys
import time

sys.path.insert(0, "/Users/YOUR_NAME/.hermes/skills/boss-zhipin-auto/scripts")
from safari_boss_runner import safari_js, json_js, send_text_value, click_send_value, run_bridge, chat_state_value


def get_page_text():
    """Get full page text content."""
    js = """
    var text = document.body.innerText || '';
    return text.slice(0, 10000);
    """
    return json_js(js)


def main():
    print("=== BOSS直聘 HR Message Check ===")
    print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Navigate to chat page
    run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
    time.sleep(4.0)
    
    # Check if a conversation is already open (has chat input)
    state = chat_state_value()
    print(f"\n=== CHAT STATE ===")
    print(json.dumps(state, ensure_ascii=False))
    
    has_open_conv = state.get("ok") and state.get("result", {}).get("hasChatInput", False)
    
    if not has_open_conv:
        print("\n[INFO] No conversation currently open on the chat page.")
        print("[INFO] Cannot reply programmatically due to Vue SPA trusted event barrier.")
        print("[INFO] Processing will report findings only.")
    
    # Get full page text to identify HR messages
    text_data = get_page_text()
    if not text_data.get("ok") or not text_data.get("result"):
        print(json.dumps({"error": "Failed to get page text", "detail": text_data}))
        return
    
    full_text = text_data["result"]
    
    # Parse conversations from text
    lines = full_text.split("\n")
    convos = []
    for i, line in enumerate(lines):
        line = line.strip()
        if ("女士" in line or "先生" in line) and len(line) < 50 and len(line) > 5:
            time_str = ""
            if i > 0:
                prev = lines[i-1].strip()
                if ":" in prev and len(prev) < 10:
                    time_str = prev
            msg = lines[i+1] if i+1 < len(lines) else ""
            convos.append({
                "name_line": line,
                "time": time_str,
                "first_msg": msg.strip()[:200]
            })
    
    print(f"\n=== ALL CONVERSATIONS ({len(convos)}) ===")
    
    # Find HR messages that are questions/initiations (not our sent messages)
    skip_phrases = ["已读", "送达", "这是我的作品集", "百度网盘", "感谢您的关注",
                     "感谢你的关注", "暂时与该职位不够匹配"]
    
    hr_messages = []
    for c in convos:
        msg = c["first_msg"]
        is_our_send = any(p in msg for p in skip_phrases)
        if not is_our_send:
            hr_messages.append(c)
            print(f"  [{c['time']}] {c['name_line']}")
            print(f"    {c['first_msg'][:100]}")
    
    if not hr_messages:
        print("\n✅ No new HR messages to respond to.")
        print("[SILENT]")
        return
    
    # Try to find a non-excluded HR message to respond to
    excluded_keywords = ["短视频", "抖音", "快手", "AI抽卡", "经纪人", "信息流剪辑师"]
    
    # Separate actionable messages from excluded ones
    excluded_msgs = []
    actionable_msgs = []
    
    for c in hr_messages:
        name_and_msg = c["name_line"] + c["first_msg"]
        if any(kw in name_and_msg for kw in excluded_keywords):
            excluded_msgs.append(c)
        else:
            # Skip rejections
            if "匹配" in c["first_msg"] and ("不" in c["first_msg"] or "不符" in c["first_msg"]):
                continue
            # Skip "面试时间已过" type messages
            if "面试时间已过" in c["first_msg"]:
                continue
            actionable_msgs.append(c)
    
    print(f"\n=== ACTIONABLE HR MESSAGES ({len(actionable_msgs)}) ===")
    if not actionable_msgs:
        print("  (none - all are excluded/rejected)")
        print("[SILENT]")
        return
    
    for c in actionable_msgs:
        print(f"  [{c['time']}] {c['name_line']}")
        print(f"    {c['first_msg'][:120]}")
    
    # Process the most recent actionable message
    target_hr = actionable_msgs[0]
    
    # Check if the open conversation matches this HR
    conv_text_matches_target = False
    if has_open_conv:
        # Check the conversation pane to see if it matches our target HR
        check = json_js("""
        var convPane = document.querySelector('.chat-conversation');
        if (!convPane) return {openConv: false, reason: 'no_conv_pane'};
        var text = (convPane.innerText || '').trim().slice(0, 500);
        var headerEl = convPane.querySelector('.top-info-content, .chat-header, [class*=\"header\"]');
        var headerText = headerEl ? (headerEl.innerText || '').trim() : '';
        return {openConv: true, text: text, headerText: headerText};
        """)
        if check.get("ok") and check.get("result", {}).get("openConv"):
            conv_text = check["result"].get("text", "")
            conv_header = check["result"].get("headerText", "")
            # Check if the name in target_hr appears in the conversation text
            name_parts = target_hr["name_line"][:15]
            conv_text_matches_target = name_parts in conv_text or name_parts in conv_header
            print(f"\n=== OPEN CONVERSATION ===")
            print(f"  Header: {conv_header[:100]}")
            print(f"  Text preview: {conv_text[:200]}")
            print(f"  Matches target HR '{name_parts}': {conv_text_matches_target}")
    
    if not has_open_conv or not conv_text_matches_target:
        name_line = target_hr["name_line"]
        msg = target_hr["first_msg"]
        
        print(f"\n[INFO] Cannot reply to '{name_line}' right now — no open conversation or wrong conversation open.")
        print(f"[INFO] HR message: {msg[:120]}")
        print(f"\n📋 Unresponded HR messages requiring manual attention:")
        for c in actionable_msgs:
            print(f"  🔴 [{c['time']}] {c['name_line']}")
            print(f"     {c['first_msg'][:150]}")
        print("\n   (Left sidebar: click conversation to open, then cron can auto-reply next time)")
        return
    
    # We have an open conversation matching the target HR - send reply!
    print(f"\n=== REPLYING TO: {target_hr['name_line']} ===")
    
    name_line = target_hr["name_line"]
    msg = target_hr["first_msg"]
    portfolio_msg = "这是我的作品集，百度网盘链接：https://pan.baidu.com/s/<YOUR_SHARE_ID> 提取码：<CODE>，请查收~"
    
    if "离职" in msg or "离职状态" in msg:
        reply = f"你好，目前是离职状态，随时可以到岗。熟练使用PR、AE、达芬奇等后期工具，这是我的作品集：\n\n{portfolio_msg}"
    elif "面试" in msg:
        reply = f"好的，谢谢邀请！请问什么时间方便面试？这是我的作品集，您可以先看看：\n\n{portfolio_msg}"
    elif "薪资" in msg or "期望" in msg or "薪" in msg:
        reply = f"期望薪资7000元/月。这是我的作品集，您可以先看看：\n\n{portfolio_msg}"
    elif "工作机会" in msg or "看机会" in msg or "新机会" in msg or "新工作" in msg or "考虑" in msg and "机会" in msg:
        reply = f"你好，正在看新的工作机会！我主要做视频剪辑和后期制作，熟练使用PR、AE、达芬奇。这是我的作品集：\n\n{portfolio_msg}"
    elif "hello" in msg.lower() or "hi" in msg.lower() or "在吗" in msg:
        reply = f"你好！目前在找视频剪辑/后期相关的工作，熟练使用PR、AE、达芬奇。这是我的作品集：\n\n{portfolio_msg}"
    elif "能力" in msg or "会" in msg or "软件" in msg or "技能" in msg or "剪映" in msg:
        reply = f"我熟练使用PR、AE、达芬奇等剪辑和后期工具，有丰富的视频剪辑经验。这是我的作品集：\n\n{portfolio_msg}"
    elif "附件简历" in msg or ("简历" in msg and ("发" in msg or "发" in name_line)):
        reply = f"好的，这是我的简历。\n\n{portfolio_msg}"
    else:
        reply = f"你好，感谢联系！我目前在看视频剪辑/后期制作相关的工作机会，熟练使用PR、AE、达芬奇等工具。这是我的作品集：\n\n{portfolio_msg}"
    
    print(f"\n=== REPLY TEXT ===")
    print(reply)
    print("==================")
    
    # Send reply
    print(f"\n=== SENDING REPLY ===")
    send_result = send_text_value(reply)
    time.sleep(1.0)
    click_result = click_send_value()
    result = {"send_text": send_result, "click_send": click_result}
    print(json.dumps(result, ensure_ascii=False))
    
    # Verify
    time.sleep(1.5)
    verify = json_js("""
    var text = document.body.innerText || '';
    return {hasPortfolio: text.indexOf('pan.baidu.com') > 0, tail: text.slice(-500)};
    """)
    print(f"\n=== VERIFICATION ===")
    print(json.dumps(verify, ensure_ascii=False))
    
    sent_ok = (
        (result.get("send_text", {}).get("result", {}).get("sent", False) or
         result.get("click_send", {}).get("ok", False))
    )
    
    if sent_ok:
        print(f"\n✅ Reply sent to {target_hr['name_line']}!")
    else:
        print(f"\n⚠️ Send attempt complete - check manually if needed.")


if __name__ == "__main__":
    main()
