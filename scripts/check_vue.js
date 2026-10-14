JSON.stringify((function() {
  var result = {};
  
  // Check console errors by looking at the page's onerror
  result.url = location.href;
  
  // Check the right panel after the click
  var conv = document.querySelector('.chat-conversation');
  var noData = document.querySelector('.chat-no-data');
  
  result.convHTML = conv ? conv.innerHTML.slice(0, 1000) : 'no_conv';
  
  if (noData) {
    result.noDataStyle = noData.getAttribute('style') || '';
    result.noDataComputedDisplay = getComputedStyle(noData).display;
    result.noDataVisible = noData.offsetParent !== null;
  }
  
  // Try to check Vue component state
  var vueApp = document.querySelector('#app, #wrap');
  if (vueApp && vueApp.__vue__) {
    result.hasVue = true;
    // Check if the chat component has loaded conversations
    try {
      var vm = vueApp.__vue__;
      // Common Vuex store patterns
      if (vm.$store) {
        result.hasStore = true;
        var state = vm.$store.state;
        var keys = Object.keys(state || {}).slice(0, 10);
        result.storeKeys = keys;
        if (state.chat) {
          result.chatState = JSON.parse(JSON.stringify(state.chat)).slice(0, 200);
        }
      }
    } catch(e) {
      result.vueError = String(e).slice(0, 200);
    }
  } else {
    result.hasVue = false;
    // Try to find Vue on the page
    result.vueDetected = typeof Vue !== 'undefined';
  }
  
  return result;
})())
