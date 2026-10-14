#!/usr/bin/env python3
"""Click on each recent chat and check for HR messages."""
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safari_boss_runner import safari_js, json_js, chat_state_value, run_bridge, click_screen_point

def get_full_chat_content():
    """Get full chat content including message history."""
    js = r"""
    (function() {
      const result = {};
      
      // Get conversation info - who we're chatting with
      const headerEl = document.querySelector('.chat-header, [class*="chat-header"], [class*="chat-top"], ' +
        '[class*="dialog-header"], .dialog-title, header');
      if (headerEl) {
        result.header = (headerEl.innerText || '').trim().slice(0, 200);
      }
      
      // Get the full chat message area
      const chatBody = document.querySelector(
        '.chat-body, .chat-msg-list, [class*="chat-body"], [class*="msg-list"], ' +
        '[class*="message-list"], [class*="dialog-body"], .msg-scroll, ' +
        '.chat-content-right, [class*="chat-content-right"], ' +
        '.chat-right, .content-right'
      );
      
      if (chatBody) {
        result.chatBodyText = (chatBody.innerText || '').trim().slice(0, 5000);
        result.chatBodyHTML = chatBody.innerHTML.slice(0, 3000);
      }
      
      // Get page full text
      result.fullText = (document.body.innerText || '').trim().slice(0, 8000);
      
      // Check if there's a chat input (means we're in a conversation)
      const inputs = Array.from(document.querySelectorAll(
        'div[contenteditable="true"], textarea'
      )).filter(el => {
        const r = el.getBoundingClientRect();
        return r.width > 20 && r.height > 10;
      });
      result.hasInput = inputs.length > 0;
      result.inputInfo = inputs.map(i => ({
        tag: i.tagName,
        placeholder: i.getAttribute('placeholder') || '',
        text: (i.innerText || i.value || '').slice(0, 100)
      }));
      
      return result;
    })()
    """
    return json_js(js)

def click_chat_list_item(index):
    """Click on the nth chat list item in the sidebar."""
    js = f"""
    (function() {{
      // Try various selectors for chat list items in the sidebar
      const selectors = [
        '.chat-list li, .friend-list li, .conversation-list li, ' +
        '[class*="chat"] [class*="item"], [class*="conversation"] [class*="item"], ' +
        '.geek-chat-list li, .chat-list-wrap li, ' +
        'ul li[class*="chat"], div[class*="chat-item"], div[class*="session-item"], ' +
        '.left-panel li, .chat-left li, .sidebar li',
        '.chat-content-left > div, .chat-list > div',
        'div[class*="chat-list"] > div, div[class*="conversation"] > div'
      ];
      
      let items = [];
      for (const sel of selectors) {{
        const found = Array.from(document.querySelectorAll(sel));
        if (found.length > items.length) {{
          items = found.filter(n => {{
            const r = n.getBoundingClientRect();
            const text = (n.innerText || '').trim();
            return r.width > 100 && r.height > 20 && text.length > 5 && !/消息|客服/.test(text);
          }});
        }}
      }}
      
      if (items.length === 0) {{
        // Fallback: just find all clickable divs in the left area
        items = Array.from(document.querySelectorAll('div, li')).filter(n => {{
          const r = n.getBoundingClientRect();
          const text = (n.innerText || '').trim();
          return r.left < window.innerWidth * 0.4 && r.width > 100 && r.height > 20 && 
                 text.length > 10 && !/消息|客服|首页|职位/.test(text);
        }});
      }}
      
      const idx = {index};
      if (idx >= items.length) {{
        return {{clicked: false, reason: 'index_out_of_range', count: items.length}};
      }}
      
      const target = items[idx];
      const r = target.getBoundingClientRect();
      target.click();
      
      return {{
        clicked: true,
        index: idx,
        text: (target.innerText || '').trim().slice(0, 200),
        rect: {{left: r.left, top: r.top, width: r.width, height: r.height}},
        totalItems: items.length,
        selectors: selectors
      }};
    }})()
    """
    return json_js(js)

# Try clicking the first few chat items
for i in range(5):
    print(f"\n=== CLICKING CHAT ITEM {i} ===")
    result = click_chat_list_item(i)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("ok") and result.get("result", {}).get("clicked"):
        time.sleep(2)
        content = get_full_chat_content()
        print(f"\n=== CHAT CONTENT (item {i}) ===")
        print(json.dumps(content, ensure_ascii=False, indent=2))
        
        # If we found a conversation with input, check if there are HR messages we need to reply to
        result_data = content.get("result", {})
        if result_data.get("hasInput"):
            # We're in a conversation, look at the last messages from HR
            full_text = result_data.get("fullText", "")
            header = result_data.get("header", "")
            chat_body = result_data.get("chatBodyText", "")
            
            print(f"\n=== CONVERSATION: {header} ===")
            print(f"HAS INPUT: {result_data.get('hasInput')}")
            
            # Check if there's a new HR message (not our sent messages)
            lines = chat_body.split('\n')
            print(f"Chat body lines: {len(lines)}")
            for line in lines[-20:]:
                print(f"  {line}")
    
    time.sleep(1)

print("\n=== DONE ===")
