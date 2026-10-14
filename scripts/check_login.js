JSON.stringify((function() {
  var result = {};
  
  // Check page data
  if (typeof _PAGE !== 'undefined') {
    result.isLogin = _PAGE.isLogin;
    result.uid = _PAGE.uid;
    result.name = _PAGE.name;
    result.hasToken = !!_PAGE.token;
  } else {
    result.pageData = 'not_found';
  }
  
  // Check if there's a "登录/注册" button visible
  var loginBtns = document.querySelectorAll('a[href*="login"], a[href*="passport"], ' +
    '[class*="login"], button:contains("登录"), span:contains("登录")');
  result.loginBtnCheck = Array.from(loginBtns).slice(0, 3).map(function(b) {
    return {text: (b.innerText || '').trim().slice(0, 20), href: b.href || ''};
  });
  
  // Check the header for login state
  var headerUserNav = document.querySelector('.user-nav, .header-user, ' +
    '[class*="user-nav"], [class*="header-user"]');
  if (headerUserNav) {
    result.headerNavText = (headerUserNav.innerText || '').trim().slice(0, 200);
  }
  
  return result;
})())
