JSON.stringify((function() {
  var result = {};
  
  // Check for iframes
  var iframes = document.querySelectorAll('iframe');
  result.iframeCount = iframes.length;
  result.iframes = [];
  for (var i = 0; i < iframes.length; i++) {
    var f = iframes[i];
    result.iframes.push({
      id: f.id || '',
      className: (f.className || '').slice(0, 60),
      src: (f.src || '').slice(0, 100),
      width: f.clientWidth,
      height: f.clientHeight
    });
  }
  
  // Check the full HTML structure envelope
  var allDivsWithChat = document.querySelectorAll('div[class*="chat"], div[class*="dialog"], div[class*="conversation"], div[class*="message"]');
  result.chatDivs = [];
  for (var j = 0; j < allDivsWithChat.length && j < 15; j++) {
    var d = allDivsWithChat[j];
    var r = d.getBoundingClientRect();
    result.chatDivs.push({
      className: (d.className || '').slice(0, 80),
      rect: {l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)},
      visible: r.width > 10 && r.height > 10,
      hasContent: (d.innerHTML || '').length > 0
    });
  }
  
  // Check wrap id
  var wrap = document.getElementById('wrap');
  if (wrap) {
    result.wrapClass = (wrap.className || '');
    result.wrapChildren = wrap.children.length;
    result.wrapHTML = wrap.innerHTML.slice(0, 2000);
  }
  
  return result;
})())
