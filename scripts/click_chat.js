JSON.stringify((function() {
  var result = {};
  
  // Find ALL LI elements inside the chat user area
  var allLis = document.querySelectorAll('.chat-user li');
  result.totalLis = allLis.length;
  
  var lis = [];
  for (var i = 0; i < allLis.length; i++) {
    var el = allLis[i];
    var r = el.getBoundingClientRect();
    var text = (el.innerText || '').trim();
    lis.push({
      index: i,
      text: text.slice(0, 100),
      rect: {l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)},
      visible: r.width > 10 && r.height > 10
    });
  }
  result.lis = lis;
  
  // For the 4th LI (index 3), click it - this should be <HR>先生 or <HR_NAME>based on position
  // Let's click each one starting from the top visible ones
  // Actually, let's find which items have "对话" context - we want the ones showing HR names
  
  // The first visible LI after the filter bar would be a chat conversation
  var visibleItems = lis.filter(function(item) { 
    return item.rect.l < 200 && item.rect.t > 100 && item.visible; 
  });
  result.visibleItems = visibleItems;
  
  // Click item at index 3 (the 4th LI, which should be <HR>女士)
  if (allLis.length > 3) {
    allLis[3].click();
    result.clicked = {index: 3, text: (allLis[3].innerText || '').trim().slice(0, 100)};
  }
  
  return result;
})())
