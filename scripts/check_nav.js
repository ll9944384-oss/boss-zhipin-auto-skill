JSON.stringify((function() {
  var result = {};
  
  // Try to check login state from the nav bar
  var userNav = document.querySelector('.user-nav, [class*="user-nav"]');
  if (userNav) {
    result.userNav = (userNav.innerText || '').trim().slice(0, 200);
  }
  
  // Check if the page shows "YOUR_NAME" anywhere in the header
  var header = document.getElementById('header');
  if (header) {
    result.headerText = (header.innerText || '').trim().slice(0, 500);
  }
  
  // Check the chat user panel for the logged-in user's info
  var chatUserItems = document.querySelectorAll('.chat-user li');
  var firstConv = chatUserItems.length > 0 ? (chatUserItems[0].innerText || '').trim().slice(0, 100) : 'none';
  result.firstConversation = firstConv;
  
  // Check if there's a class indicating login state on body or html
  result.bodyClass = document.body.className;
  result.htmlClass = document.documentElement.className;
  
  return result;
})())
