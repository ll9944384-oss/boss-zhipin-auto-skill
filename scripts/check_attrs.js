JSON.stringify((function() {
  var result = {};
  
  // Get data attributes from friend content items
  var items = document.querySelectorAll('.friend-content-warp');
  result.itemCount = items.length;
  result.items = [];
  for (var i = 0; i < items.length && i < 5; i++) {
    var el = items[i];
    var attrs = {};
    for (var j = 0; j < el.attributes.length; j++) {
      var attr = el.attributes[j];
      attrs[attr.name] = attr.value;
    }
    result.items.push({
      tag: el.tagName,
      className: el.className,
      id: el.id,
      attrs: attrs,
      dataSet: JSON.parse(JSON.stringify(el.dataset || {})),
      text: (el.innerText || '').trim().slice(0, 100)
    });
    
    // Also check parent LI
    var li = el.closest('li');
    if (li) {
      var liAttrs = {};
      for (var k = 0; k < li.attributes.length; k++) {
        var attr2 = li.attributes[k];
        liAttrs[attr2.name] = attr2.value;
      }
      result.items[i].liAttrs = liAttrs;
      result.items[i].liClass = li.className;
      result.items[i].liDataset = JSON.parse(JSON.stringify(li.dataset || {}));
    }
  }
  
  // Also look for any Vue-specific data attributes
  var allFriendElements = document.querySelectorAll('[data-geek-id], [data-geekid], [data-sessionid], [data-session-id], [data-friendid]');
  result.friendIds = [];
  allFriendElements.forEach(function(el) {
    result.friendIds.push({
      tag: el.tagName,
      geekId: el.getAttribute('data-geek-id') || el.getAttribute('data-geekid') || '',
      sessionId: el.getAttribute('data-sessionid') || el.getAttribute('data-session-id') || '',
      friendId: el.getAttribute('data-friendid') || ''
    });
  });
  
  return result;
})())
