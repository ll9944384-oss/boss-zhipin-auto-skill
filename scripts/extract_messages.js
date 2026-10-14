(function() {
  try {
    // Extract all chat messages
    const messages = [];
    
    // Try to find the chat message area
    const msgElements = document.querySelectorAll(
      '.chat-msg, .msg-item, .chat-message-item, [class*="msg-item"], [class*="message-item"], ' +
      '.msg-content, [class*="message-content"], .chat-content-item, [class*="chat-content"] li, ' +
      '.im-message, .chat-message, .chat_record, .record-item'
    );
    
    if (msgElements.length > 0) {
      msgElements.forEach((el, idx) => {
        const text = (el.innerText || el.textContent || '').trim();
        if (text) {
          // Determine if it's from me or HR
          const classes = String(el.className || '');
          const isRight = classes.includes('right') || classes.includes('self') || classes.includes('send');
          const isLeft = classes.includes('left') || classes.includes('other') || classes.includes('receive');
          messages.push({
            idx,
            text: text.slice(0, 500),
            direction: isRight ? 'sent' : (isLeft ? 'received' : 'unknown'),
            classes: classes.slice(0, 100)
          });
        }
      });
    }
    
    // Fallback: just get all text from the chat area
    if (messages.length === 0) {
      // Try finding conversation area
      const chatArea = document.querySelector(
        '.chat-area, .im-chat, .chat-container, [class*="chat-area"], [class*="im-chat"], ' +
        '.chat-content, .conversation-body, .msg-board, .message-box'
      );
      
      if (chatArea) {
        const allMsgNodes = chatArea.querySelectorAll('p, div, span, li');
        const seen = new Set();
        allMsgNodes.forEach((node) => {
          const text = (node.innerText || node.textContent || '').trim();
          if (text && text.length > 5 && !seen.has(text)) {
            seen.add(text);
            messages.push({ idx: messages.length, text: text.slice(0, 500), direction: 'unknown' });
          }
        });
      }
    }
    
    // Also get the chat list on the left sidebar
    const chatList = [];
    const listItems = document.querySelectorAll(
      '.chat-list-item, .friend-item, .conversation-item, ' +
      '[class*="chat-list"] [class*="item"], [class*="conversation"] [class*="item"], ' +
      '.im-list-item, .geek-list-item'
    );
    
    listItems.forEach((el, idx) => {
      const text = (el.innerText || el.textContent || '').trim();
      if (text) {
        const hasUnread = el.querySelector('.unread, .badge, [class*="unread"], [class*="badge"]') !== null;
        chatList.push({ idx, text: text.slice(0, 300), hasUnread });
      }
    });
    
    // Get page title and current URL
    return {
      url: location.href,
      title: document.title,
      pathname: location.pathname,
      messages,
      chatList,
      htmlSnippet: document.body.innerText.slice(0, 3000)
    };
  } catch (err) {
    return { error: String(err && err.stack || err) };
  }
})();
