

var switchFunctionality = {

    onChange: function () {

        var linkElement = document.querySelectorAll('link');
        var scriptElement = document.querySelectorAll('script');
        var switchElement = document.querySelector('.theme-shifter');
        var loaderElement = document.querySelector('#load_screen');

        switchElement.addEventListener('change', function() {

            if(this.checked) {

                Cookies.deleteCookie('dark_mode');

                location.reload();

            } else {

                this.checked = false;
                Cookies.setCookie('dark_mode', 1, 1);

                location.reload();
                
            }

        })

    },
    setMode: function() {
        
        var loaderElement = document.querySelector('#load_screen');
        var lightStyleEl = document.querySelectorAll('.light-theme');
        var darkStyleEl = document.querySelectorAll('.dark-theme');        

        if (Cookies.getCookie('dark_mode') != "") {

            var linkElement = document.querySelectorAll('link');
            var scriptElement = document.querySelectorAll('script');
            var imgLogo = document.querySelector('img[alt="logo"]');

            if(imgLogo) {
                imgLogo.setAttribute('src', 'dark/assets/img/90x90.jpg');
            }

            for (var i = 0; i < lightStyleEl.length; i++) {
                if(lightStyleEl[i]) {
                    lightStyleEl[i].setAttribute('media', "max-width: 1px");
                }
            }

            for (var i = 0; i < linkElement.length; i++) {
                getHref = linkElement[i].getAttribute('href');

                n = getHref.startsWith("https");

                if( getHref == "assets/css/loader.css" ) {
                } else {

                    if(n) {
                        linkElement[i].setAttribute('href', getHref);
                    } else {
                        linkElement[i].setAttribute('href', 'dark/' + getHref);
                    }
                }
            }

            for (var i = 0; i < scriptElement.length; i++) {
                getSrc = scriptElement[i].getAttribute('src');

                if( getSrc == "dark/assets/js/loader.js" ) {
                } else {
                    scriptElement[i].setAttribute('src', 'dark/' + getSrc);
                }
            }
            
        } else {

            for (var i = 0; i < darkStyleEl.length; i++) {
                if(darkStyleEl[i]) {
                    darkStyleEl[i].setAttribute('media', "max-width: 1px");
                    darkStyleEl[i].remove()
                }
            }
            load_screen.style.display = 'none';
        }
    }

}

var Cookies = {
    setCookie: function (cname, cvalue, exdays) {
      var d = new Date();
      d.setTime(d.getTime() + (exdays*24*60*60*1000));
      var expires = "expires="+ d.toUTCString();
      document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    },
    getCookie: function(cname) {
      var name = cname + "=";
      var decodedCookie = decodeURIComponent(document.cookie);
      var ca = decodedCookie.split(';');
      for(var i = 0; i <ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
          c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
          return c.substring(name.length, c.length);
        }
      }
      return "";
    },
    deleteCookie: function (name) {
      document.cookie = name +'=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    }
}


window.addEventListener("load", function(){
    switchFunctionality.setMode();
});
            