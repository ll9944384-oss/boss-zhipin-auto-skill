(function() {
  var result = {};

  // Check if we're in a chat conversation (has input field)
  var inputs = Array.from(document.querySelectorAll('div[contenteditable="true"], textarea'));
  var visibleInputs = inputs.filter(function(el) {
    var r = el.getBoundingClientRect();
    return r.width > 20 && r.height > 10;
  });
  result.hasInput = visibleInputs.length > 0;
  
  // Get the chat header/recipient name
  var headerEl = document.querySelector(
    '.chat-header, [class*="chat-header"], [class*="chat-top"], ' +
    '[class*="dialog-header"], .dialog-title, header'
  );
  result.header = headerEl ? (headerEl.innerText || '').trim().slice(0, 200) : '';
  
  // Get chat message area text
  var chatBody = document.querySelector(
    '.chat-body, .chat-msg-list, [class*="chat-body"], [class*="msg-list"], ' +
    '[class*="message-list"], .msg-scroll, ' +
    '.chat-content-right, [class*="chat-content-right"]'
  );
  result.chatText = chatBody ? (chatBody.innerText || '').trim().slice(0, 5000) : '';
  
  // Full page text
  result.fullText = (document.body.innerText || '').trim().slice(0, 8000);
  
  // Title
  result.title = document.title;
  result.url = location.href;
  
  return result;
})()
