JSON.stringify((function() {
  var result = {};
  result.bodyHTML = document.body.innerHTML.slice(0, 5000);
  result.bodyText = document.body.innerText.slice(0, 2000);
  
  // Find ANY clickable elements in the left half of the page
  var allDivs = document.querySelectorAll('div, li, a, span');
  var leftItems = [];
  for (var i = 0; i < allDivs.length; i++) {
    var el = allDivs[i];
    var r = el.getBoundingClientRect();
    var text = (el.innerText || '').trim();
    if (r.left < window.innerWidth * 0.4 && r.width > 80 && r.height > 20 && 
        text.length > 10 && r.top > 50 && text.indexOf('首页') < 0 && 
        text.indexOf('职位') < 0 && text.indexOf('公司') < 0) {
      leftItems.push({
        tag: el.tagName,
        text: text.slice(0, 100),
        className: (el.className || '').slice(0, 80),
        rect: {l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}
      });
    }
  }
  result.leftItems = leftItems.slice(0, 30);
  
  // Also get all elements with "chat" related class names
  var allElements = document.querySelectorAll('[class*="chat"], [class*="msg"], [class*="dialog"], [class*="conversation"], [class*="session"]');
  var chatRelated = [];
  for (var j = 0; j < allElements.length && j < 20; j++) {
    var el2 = allElements[j];
    var r2 = el2.getBoundingClientRect();
    if (r2.width > 20 && r2.height > 20) {
      chatRelated.push({
        tag: el2.tagName,
        className: (el2.className || '').slice(0, 100),
        rect: {l: Math.round(r2.left), t: Math.round(r2.top), w: Math.round(r2.width), h: Math.round(r2.height)},
        text: (el2.innerText || '').trim().slice(0, 80)
      });
    }
  }
  result.chatRelated = chatRelated.slice(0, 20);
  
  return result;
})())
