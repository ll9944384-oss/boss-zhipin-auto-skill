JSON.stringify((function() {
  var result = {};
  
  // Find all chat LI items in the sidebar
  var items = document.querySelectorAll('.chat-user li, .chat-content li, .friend-list li, ' +
    '.chat-container li, [class*="chat-user"] li');
  
  var chatItems = [];
  for (var i = 0; i < items.length; i++) {
    var el = items[i];
    var r = el.getBoundingClientRect();
    var text = (el.innerText || '').trim();
    if (r.width > 100 && r.height > 20 && text.length > 20) {
      chatItems.push({
        index: i,
        text: text.slice(0, 300),
        rect: {l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}
      });
    }
  }
  result.chatItems = chatItems.slice(0, 15);
  
  // Also specifically check: does any item have an unread badge or "新" character?
  var unreadItems = [];
  for (var j = 0; j < chatItems.length; j++) {
    var item = chatItems[j];
    if (item.text.indexOf('新') >= 0) {
      unreadItems.push(item);
    }
  }
  result.unreadItems = unreadItems;
  
  // Click on item at given index using the class name structure we found
  // The items are LI elements inside .chat-user
  function clickItem(idx) {
    var target = items[idx];
    if (!target) return {clicked: false, reason: 'index_out_of_range'};
    target.click();
    return {clicked: true, index: idx, text: (target.innerText || '').trim().slice(0, 100)};
  }
  
  // Try clicking item 0 (most recent - <HR>女士)
  result.click0 = clickItem(0);
  // Also get the text of item 0
  if (items[0]) result.item0Text = (items[0].innerText || '').trim().slice(0, 200);
  
  return result;
})())
