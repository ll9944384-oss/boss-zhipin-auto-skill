JSON.stringify((function() {
  var result = {};
  
  // Try to find the conversation items and click with comprehensive events
  var items = document.querySelectorAll('.friend-content-warp');
  result.totalItems = items.length;
  
  if (items.length > 0) {
    var target = items[0];
    var r = target.getBoundingClientRect();
    result.target = {
      text: (target.innerText || '').trim().slice(0, 100),
      rect: {l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}
    };
    
    // Fire multiple event types at the center of the element
    var centerX = r.left + r.width / 2;
    var centerY = r.top + r.height / 2;
    
    var events = [
      'pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'
    ];
    
    var fired = [];
    for (var i = 0; i < events.length; i++) {
      var evt = new MouseEvent(events[i], {
        bubbles: true,
        cancelable: true,
        view: window,
        detail: 1,
        screenX: centerX,
        screenY: centerY,
        clientX: centerX,
        clientY: centerY,
        button: 0,
        buttons: 1,
        composed: true
      });
      fired.push(target.dispatchEvent(evt));
    }
    result.eventsFired = fired;
    
    // Also try the LI element
    var li = target.closest('li');
    if (li) {
      for (var j = 0; j < events.length; j++) {
        var evt2 = new MouseEvent(events[j], {
          bubbles: true, cancelable: true, view: window,
          detail: 1, clientX: centerX, clientY: centerY,
          button: 0, buttons: 1
        });
        li.dispatchEvent(evt2);
      }
      result.liFired = true;
    }
  }
  
  // Check the result URL
  result.url = location.href;
  
  return result;
})())
