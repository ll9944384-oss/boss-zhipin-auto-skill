JSON.stringify((function() {
  var result = {};
  
  // Find all LI elements that represent actual conversations (not filter tabs)
  var allLis = Array.from(document.querySelectorAll('.chat-user li'));
  
  // Filter tabs are at the top with small text - skip them
  var conversations = allLis.filter(function(li) {
    var r = li.getBoundingClientRect();
    var text = (li.innerText || '').trim();
    // A conversation item has: a name (Chinese), a message, time
    // Filter tabs have short text like "全部", "未读", etc.
    return r.width > 50 && r.height > 20 && 
           r.top > 100 && // Skip top filter tabs
           (text.indexOf('招聘') >= 0 || text.indexOf('HR') >= 0 || 
            text.indexOf('经理') >= 0 || text.indexOf('总监') >= 0 ||
            text.indexOf('主管') >= 0 || text.indexOf('顾问') >= 0 ||
            text.indexOf('招聘者') >= 0 || text.indexOf('人事') >= 0 ||
            text.indexOf('创始人') >= 0 || text.indexOf('董事长') >= 0);
  });
  
  result.totalConversations = conversations.length;
  
  // Show what we have
  var convInfo = [];
  for (var i = 0; i < conversations.length && i < 5; i++) {
    var c = conversations[i];
    convInfo.push({
      index: i,
      text: (c.innerText || '').trim().slice(0, 150),
      rect: (function() { var r = c.getBoundingClientRect(); return {l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}; })()
    });
  }
  result.conversations = convInfo;
  
  // Click the first conversation (should be <HR>先生 or whoever is most recent)
  if (conversations.length > 0) {
    var target = conversations[0];
    var rectBefore = (function() { var r = target.getBoundingClientRect(); return {l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}; })();
    
    // Use dispatchEvent
    target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
    target.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
    target.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
    
    result.clicked = {
      text: (target.innerText || '').trim().slice(0, 100),
      rect: rectBefore
    };
  }
  
  return result;
})())
