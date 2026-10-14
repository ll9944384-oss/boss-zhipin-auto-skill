JSON.stringify((function() {
  var result = {};
  var wrap = document.querySelector('#wrap');
  if (!wrap || !wrap.__vue__) return {error: 'no_vue'};
  
  var vm = wrap.__vue__;
  
  // Access Vuex store
  if (vm.$store) {
    try {
      var state = vm.$store.state;
      var keys = Object.keys(state || {});
      result.storeKeys = keys;
      
      // Get each state value
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        var val = state[k];
        if (val && typeof val === 'object') {
          try {
            result[k] = JSON.parse(JSON.stringify(val));
          } catch(e) {
            result[k] = '[unserializable: ' + String(e).slice(0, 50) + ']';
          }
        } else {
          result[k] = val;
        }
      }
    } catch(e) {
      result.storeError = String(e).slice(0, 200);
    }
  }
  
  return result;
})())
