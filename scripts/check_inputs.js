JSON.stringify((function() {
  var result = {};
  
  // Check ALL possible chat input formats
  var allSelectors = [
    'div.chat-input[contenteditable="true"]',
    'div.chat-input[contenteditable]',
    'textarea.input-area',
    'div[contenteditable="true"]',
    'div[contenteditable]',
    'textarea',
    'input[type="text"]',
    '[class*="chat-input"]',
    '[class*="input-area"]',
    '[class*="editor"]',
    '[contenteditable]'
  ];
  
  for (var s = 0; s < allSelectors.length; s++) {
    var sel = allSelectors[s];
    var els = document.querySelectorAll(sel);
    var vis = [];
    for (var i = 0; i < els.length; i++) {
      var r = els[i].getBoundingClientRect();
      if (r.width > 10 && r.height > 10) {
        vis.push({
          tag: els[i].tagName,
          className: (els[i].className || '').slice(0, 60),
          rect: {l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)},
          placeholder: els[i].getAttribute('placeholder') || '',
          contenteditable: els[i].getAttribute('contenteditable') || '',
          text: (els[i].innerText || els[i].value || '').trim().slice(0, 50)
        });
      }
    }
    if (vis.length > 0) {
      result[sel] = vis;
    }
  }
  
  // Check total visible input-like elements
  var allEditable = document.querySelectorAll('[contenteditable="true"], textarea, [contenteditable]');
  var totalVis = 0;
  allEditable.forEach(function(el) {
    var r = el.getBoundingClientRect();
    if (r.width > 10 && r.height > 10) totalVis++;
  });
  result.totalVisibleInputs = totalVis;
  
  // Also get the full HTML of the right panel area
  var rightArea = document.querySelector('.chat-content-right, .chat-right, ' +
    '[class*="chat-content-right"], .content-right, ' +
    '.chat-conversation');
  if (rightArea) {
    result.rightPanelHTML = rightArea.innerHTML.slice(0, 3000);
    result.rightPanelText = (rightArea.innerText || '').trim().slice(0, 2000);
  }
  
  return result;
})())
