(function() {
  var result = {};
  
  // Find all chat list items in the sidebar (left panel)
  var allSelectors = [
    '.chat-list li, .friend-list li, .conversation-list li',
    '[class*="chat"] [class*="item"], [class*="conversation"] [class*="item"]',
    '.geek-chat-list li, .chat-list-wrap li',
    '.left-panel li, .chat-left li, .sidebar li',
    '.chat-content-left > div, .chat-list > div',
    'div[class*="chat-list"] > div, div[class*="conversation"] > div'
  ];
  
  var best = [];
  for (var s = 0; s < allSelectors.length; s++) {
    var found = document.querySelectorAll(allSelectors[s]);
    if (found.length > best.length) {
      best = [];
      for (var f = 0; f < found.length; f++) {
        best.push(found[f]);
      }
    }
  }
  
  // Filter to visible items with meaningful text
  var items = best.filter(function(n) {
    var r = n.getBoundingClientRect();
    var text = (n.innerText || '').trim();
    return r.width > 80 && r.height > 20 && text.length > 10;
  });
  
  result.count = items.length;
  result.items = [];
  
  for (var i = 0; i < items.length && i < 20; i++) {
    var item = items[i];
    var r = item.getBoundingClientRect();
    var text = (item.innerText || '').trim();
    // Check for unread indicators
    var badge = item.querySelector('.badge, [class*="badge"], [class*="unread"], [class*="red-dot"], [class*="msg-count"]');
    var hasUnread = badge ? true : (text.indexOf('新') >= 0);
    
    result.items.push({
      index: i,
      text: text.slice(0, 300),
      hasUnread: hasUnread,
      rect: {left: r.left, top: r.top, width: r.width, height: r.height}
    });
  }
  
  // Try to find which item has unread messages specifically
  result.unreadItems = result.items.filter(function(i) { return i.hasUnread; });
  
  return result;
})()
