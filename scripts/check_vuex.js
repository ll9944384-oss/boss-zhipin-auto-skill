JSON.stringify((function() {
  var result = {};
  
  var wrap = document.querySelector('#wrap');
  if (!wrap || !wrap.__vue__) return {error: 'no_vue_instance'};
  
  var vm = wrap.__vue__;
  
  // Try to find the actual Vue component that has the chat list
  // The component might be nested, so let's walk the component tree
  function findComponent(vm, name) {
    if (!vm) return null;
    var n = vm.$options ? vm.$options.name || '' : '';
    if (n && n.toLowerCase().indexOf(name.toLowerCase()) >= 0) return vm;
    if (vm.$children) {
      for (var i = 0; i < vm.$children.length; i++) {
        var found = findComponent(vm.$children[i], name);
        if (found) return found;
      }
    }
    return null;
  }
  
  result.rootName = vm.$options ? vm.$options.name || 'unnamed' : 'no_options';
  result.rootChildCount = vm.$children ? vm.$children.length : 0;
  
  // Try to find chat-related component
  var chatComp = findComponent(vm, 'chat');
  if (chatComp) {
    result.foundChatComp = true;
    var compName = chatComp.$options ? chatComp.$options.name || '' : '';
    result.chatCompName = compName;
    
    // Get the chat data from the component
    try {
      var data = chatComp.$data || {};
      var dataStr = JSON.stringify(data).slice(0, 2000);
      result.chatCompData = dataStr;
    } catch(e) {
      result.chatCompDataError = String(e).slice(0, 200);
    }
  } else {
    result.foundChatComp = false;
    
    // Try to get from Vuex store
    if (vm.$store) {
      var store = vm.$store;
      result.hasStore = true;
      
      // Get state keys
      var stateKeys = Object.keys(store.state || {});
      result.stateKeys = stateKeys;
      
      // Try to get chat state
      try {
        result.chatState = JSON.stringify(store.state.chat).slice(0, 2000);
      } catch(e) {
        result.chatStateError = String(e).slice(0, 200);
      }
      
      // Try to get session/conversation state
      var sessionKeys = ['session', 'conversation', 'geek', 'friend', 'im'];
      for (var s = 0; s < sessionKeys.length; s++) {
        var k = sessionKeys[s];
        if (store.state[k]) {
          try {
            result[k + 'State'] = JSON.stringify(store.state[k]).slice(0, 2000);
          } catch(e) {
            result[k + 'Error'] = String(e).slice(0, 200);
          }
        }
      }
    }
  }
  
  return result;
})())
