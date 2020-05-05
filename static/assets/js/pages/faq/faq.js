// Scroll To Top

$(document).on('click', '.arrow', function(event) {
  event.preventDefault();
  var body = $("html, body");
  body.stop().animate({scrollTop:0}, 500, 'swing');
});