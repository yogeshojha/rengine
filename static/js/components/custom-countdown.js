$('#cd-simple').countdown('2020/10/10', function(event) {
  var $this = $(this).html(event.strftime(''
    +'<div class="countdown">'+
        '<div class="clock-count-container">'+
            '<h1 class="clock-val">%d</h1>'+
        '</div>'+
        '<h4 class="clock-text"> Days </h4>'+
    '</div>'+
    '<div class="countdown">'+
        '<div class="clock-count-container">'+
            '<h1 class="clock-val">%H</h1>'+
        '</div>'+
        '<h4 class="clock-text"> Hours </h4>'+
    '</div>'+
    '<div class="countdown">'+
        '<div class="clock-count-container">'+
            '<h1 class="clock-val">%M</h1>'+
        '</div>'+
        '<h4 class="clock-text"> Mins </h4>'+
    '</div>'+
    '<div class="countdown">'+
        '<div class="clock-count-container">'+
            '<h1 class="clock-val">%S</h1>'+
        '</div>'+
        '<h4 class="clock-text"> Sec </h4>'+
    '</div>'));
});

$('#cd-circle').countdown('2020/10/10', function(event) {
  var $this = $(this).html(event.strftime(''
    +'<div class="countdown">'+
        '<div class="clock-count-container">'+
            '<h1 class="clock-val">365</h1>'+
        '</div>'+
        '<h4 class="clock-text"> Days </h4>'+
    '</div>'+
    '<div class="countdown">'+
        '<div class="clock-count-container">'+
            '<h1 class="clock-val">%H</h1>'+
        '</div>'+
        '<h4 class="clock-text"> Hours </h4>'+
    '</div>'+
    '<div class="countdown">'+
        '<div class="clock-count-container">'+
            '<h1 class="clock-val">%M</h1>'+
        '</div>'+
        '<h4 class="clock-text"> Mins </h4>'+
    '</div>'+
    '<div class="countdown">'+
        '<div class="clock-count-container">'+
            '<h1 class="clock-val">%S</h1>'+
        '</div>'+
        '<h4 class="clock-text"> Sec </h4>'+
    '</div>'));
});