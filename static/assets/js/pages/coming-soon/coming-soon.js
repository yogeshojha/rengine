// Set the date we're counting down to
var getYear = new Date().getFullYear()+1;
var countDownDate = new Date("Dec 5, "+ getYear +" 15:37:25").getTime();

// Update the count down every 1 second
var countdownfunction = setInterval(function() {

  // Get todays date and time
  var now = new Date().getTime();
  
  // Find the distance between now an the count down date
  var distance = countDownDate - now;
  
  // Time calculations for days, hours, minutes and seconds
  var days = Math.floor(distance / (1000 * 60 * 60 * 24));
  var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
  var seconds = Math.floor((distance % (1000 * 60)) / 1000);
  
  // Output the result in an element with id="demo"
  document.getElementById("timer").innerHTML = '<div class="days"><span class="count">' + days + '</span> <span class="text">Days</span></div>' +
 '<div class="hours"><span class="count">'+ hours +'</span> <span class="text">Hours</span></div>' +
 '<div class="min"><span class="count">'+ minutes +'</span> <span class="text">Mins</span></div>' +
 '<div class="sec"><span class="count">'+ seconds +'</span> <span class="text">Secs</span></div>';
  
  // If the count down is over, write some text 
  if (distance < 0) {
    clearInterval(countdownfunction);
    document.getElementById("timer").innerHTML = "EXPIRED";
  }
}, 1000);