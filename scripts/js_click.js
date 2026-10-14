JSON.stringify((function() {
  var result = {};
  
  // Directly click the first visible chat LI item using JavaScript
  var allLis = Array.from(document.querySelectorAll('.chat-user li'));
  var visible = allLis.filter(function(li) {
    var r = li.getBoundingClientRect();
    return r.width > 50 && r.height > 20;
  });
  
  result.totalVisible = visible.length;
  
  if (visible.length > 0) {
    // Click on visible[0] (should be <HR>先生)
    var target = visible[0];
    var text = (target.innerText || '').trim();
    result.clickedText = text.slice(0, 150);
    
    // Use click() method
    target.click();
    result.clickMethod = 'js_click';
    
    // Also try dispatchEvent
    var evt = new MouseEvent('click', {bubbles: true, cancelable: true});
    target.dispatchEvent(evt);
    result.dispatchMethod = true;
  }
  
  return result;
})())
