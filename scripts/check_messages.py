#!/usr/bin/env python3
"""Check BOSS直聘 chat page for new HR messages via Safari bridge."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from safari_boss_runner import safari_js, json_js, chat_state_value, run_bridge

def main():
    # First check chat state
    state = chat_state_value()
    print("=== CHAT STATE ===")
    print(json.dumps(state, ensure_ascii=False, indent=2))
    
    if not state.get("ok") or not state.get("result", {}).get("hasChatInput"):
        # Try to navigate and re-check
        run_bridge("navigate", "https://www.zhipin.com/web/geek/chat")
        import time
        time.sleep(3)
        state = chat_state_value()
        print("=== CHAT STATE (after nav) ===")
        print(json.dumps(state, ensure_ascii=False, indent=2))
    
    # Get all messages visible on the page - focus on messages from HR (not us)
    # We need to look for chat messages. The typical structure is:
    # Messages from HR are on the left, our messages are on the right
    js = r"""
    (function() {
      const result = {};
      
      // Get full page text
      result.fullText = (document.body.innerText || '').slice(-10000);
      
      // Try to extract chat messages specifically
      // BOSS chat messages are usually in .msg-item, .chat-msg, or similar containers
      const msgContainers = document.querySelectorAll(
        '.msg-item, .chat-msg, [class*="message"], .msg-content, .chat-content, ' +
        '[class*="chat"] [class*="item"], [class*="msg-list"] > div, ' +
        '.chat-message-item, .msg-bubble'
      );
      
      const messages = [];
      msgContainers.forEach(container => {
        const text = (container.innerText || '').trim();
        if (text) {
          const r = container.getBoundingClientRect();
          const isMine = r.left > window.innerWidth / 2;
          messages.push({
            text: text.slice(0, 500),
            isMine: isMine,
            rect: {left: r.left, top: r.top, width: r.width, height: r.height}
          });
        }
      });
      
      result.messages = messages;
      
      // Also look for the chat list items (sidebar) that show unread counts
      const chatListItems = document.querySelectorAll(
        '.chat-list li, [class*="chat"] [class*="list"] [class*="item"], ' +
        '[class*="conversation"] [class*="item"], li[class*="chat"], ' +
        'div[class*="chat-item"], div[class*="session-item"]'
      );
      
      const chatList = [];
      chatListItems.forEach(item => {
        const text = (item.innerText || '').trim();
        const r = item.getBoundingClientRect();
        if (text && r.width > 50) {
          // Check for unread indicators
          const badge = item.querySelector('.badge, [class*="badge"], [class*="unread"], [class*="red-dot"], [class*="msg-count"]');
          const unreadCount = badge ? (parseInt(badge.textContent) || 1) : 0;
          chatList.push({
            text: text.slice(0, 300),
            hasUnread: unreadCount > 0 || /新/.test(text),
            unreadCount: unreadCount,
            rect: {left: r.left, top: r.top, width: r.width, height: r.height}
          });
        }
      });
      
      result.chatList = chatList;
      
      // Get chat list items from the sidebar to see which conversations have new messages
      // Try different selectors for the conversation list
      const sidebarItems = document.querySelectorAll(
        '.conversation-list > div, [class*="conversation-item"], ' +
        '.friend-list li, .chat-content-left li, ' +
        '.geek-chat-list li, .chat-list-wrap li'
      );
      
      const sidebar = [];
      sidebarItems.forEach(item => {
        const text = (item.innerText || '').trim();
        const r = item.getBoundingClientRect();
        if (text && r.width > 50) {
          sidebar.push({
            text: text.slice(0, 200),
            rect: {left: r.left, top: r.top, width: r.width, height: r.height}
          });
        }
      });
      
      result.sidebar = sidebar;
      
      return result;
    })()
    """
    
    page_data = json_js(js)
    print("\n=== PAGE DATA ===")
    print(json.dumps(page_data, ensure_ascii=False, indent=2))
    
    # Also check specific text for login state
    verify = json_js(r"""
    const text = document.body.innerText || '';
    return {
      hasLoginForm: /验证码登录/.test(text),
      isLoggedIn: /搜索30天内的联系人/.test(text) || /沟通记录/.test(text) || /消息/.test(text),
      hasMessages: /你好|您好|在吗|面试|招聘|简历|薪资/.test(text),
      pageUrl: location.href,
      pageTitle: document.title,
      textSample: text.slice(0, 2000)
    };
    """)
    print("\n=== AUTH CHECK ===")
    print(json.dumps(verify, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
