JSON.stringify((function() {
  var result = {};
  
  // Check current URL
  result.url = location.href;
  
  // Check if any URL params changed after clicking
  result.search = location.search;
  result.hash = location.hash;
  
  // Look at the chat-conversation div specifically
  var conv = document.querySelector('.chat-conversation');
  if (conv) {
    result.conversationExists = true;
    result.conversationClass = conv.className;
    result.conversationStyle = conv.getAttribute('style') || 'no style attr';
    result.conversationChildCount = conv.children.length;
    result.conversationHTML = conv.innerHTML.slice(0, 2000);
    result.conversationText = (conv.innerText || '').trim().slice(0, 2000);
    var disp = getComputedStyle(conv).display;
    result.conversationDisplay = disp;
  } else {
    result.conversationExists = false;
  }
  
  // Check chat-no-data
  var noData = document.querySelector('.chat-no-data');
  if (noData) {
    result.noDataExists = true;
    result.noDataDisplay = noData.style.display;
    result.noDataText = (noData.innerText || '').trim().slice(0, 200);
  }
  
  // Check for any visible loading states
  var loading = document.querySelector('.loading, [class*="loading"], .spinner');
  if (loading) {
    result.loadingExists = true;
    result.loadingText = (loading.innerText || '').trim().slice(0, 100);
  }
  
  return result;
})())
