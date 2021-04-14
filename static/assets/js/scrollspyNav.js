// Cache selectors
var lastId,
    sidenav = $(".sidenav"),
    // All list items
    menuItems = sidenav.find("a");

menuItems.on('click', function(event) {
  // Make sure this.hash has a value before overriding default behavior
  if (this.hash !== "") {
    // Prevent default anchor click behavior
    event.preventDefault();

    // Store hash
    var hash = this.hash;

    // Using jQuery's animate() method to add smooth page scroll
    // The optional number (800) specifies the number of milliseconds it takes to scroll to the specified area
    $('html, body').animate({
      scrollTop: $(hash).offset().top + -82
    }, 800);
  }  // End if
});