JSON.stringify((function() {
  var result = {};
  var wrap = document.querySelector('#wrap');
  if (!wrap || !wrap.__vue__) return {error: 'no_vue'};
  
  var vm = wrap.__vue__;
  
  // Find Chat component
  function findChat(vm) {
    if (!vm) return null;
    var name = '';
    try { name = vm.$options.name || ''; } catch(e) {}
    if (name === 'Chat') return vm;
    if (vm.$children) {
      for (var i = 0; i < vm.$children.length; i++) {
        var found = findChat(vm.$children[i]);
        if (found) return found;
      }
    }
    return null;
  }
  
  var chatComp = findChat(vm);
  if (!chatComp) return {error: 'Chat component not found'};
  
  result.chatFound = true;
  
  // Get Chat component's methods
  try {
    var methods = Object.keys(chatComp.$options.methods || {});
    result.methods = methods;
  } catch(e) {
    result.methodsError = String(e).slice(0, 100);
  }
  
  // Get Chat component's data
  try {
    var data = {};
    var d = chatComp.$data;
    for (var k in d) {
      if (d.hasOwnProperty(k)) {
        var v = d[k];
        if (typeof v !== 'function') {
          try {
            data[k] = JSON.parse(JSON.stringify(v));
          } catch(e) {
            data[k] = '[complex]';
          }
        }
      }
    }
    result.data = data;
  } catch(e) {
    result.dataError = String(e).slice(0, 200);
  }
  
  // Get computed properties
  try {
    var computed = chatComp.$options.computed || {};
    result.computedKeys = Object.keys(computed);
  } catch(e) {}
  
  // Try to trigger the openChat or similar method with the first friend
  try {
    var friends = chatComp.friendList || chatComp.friends || chatComp.list || [];
    if (!friends.length && chatComp.$data) {
      var d2 = chatComp.$data;
      for (var k2 in d2) {
        if (Array.isArray(d2[k2]) && d2[k2].length > 0) {
          friends = d2[k2];
          result.foundListKey = k2;
          break;
        }
      }
    }
    result.friendsCount = friends.length;
    if (friends.length > 0) {
      result.firstFriend = JSON.parse(JSON.stringify(friends[0])).slice(0, 500);
    }
  } catch(e) {
    result.friendsError = String(e).slice(0, 200);
  }
  
  return result;
})())
