var buttonEnabled = true;
var globalTimeout = 0;

$("#select_engine").steps({
  headerTag: "h4",
  bodyTag: "div",
  transitionEffect: "slide",
  cssClass: "pill wizard",
  enableKeyNavigation: false,
  onStepChanging: updateButton,
  labels: { finish: "Start Scan" },
  onInit: function (event, current) {
    $(".actions ul li:nth-child(3) a").attr(
      "onclick",
      `$(this).closest('form').submit()`
    );
  },
});
$("input[type=radio][name=scan_mode]").change(initTimer).keyup(initTimer);
disableNext();
$('a[role="menuitem"]').addClass("text-white");

function initTimer() {
  if (globalTimeout) clearTimeout(globalTimeout);
  globalTimeout = setTimeout(updateButton, 400);
}
function disableNext() {
  var nextButton = $(".actions ul li:nth-child(2) a");
  nextButton.attr("href", "#");
  buttonEnabled = $(".actions ul li:nth-child(2)")
    .addClass("disabled")
    .attr("aria-disabled", "true");
}

function enableNext() {
  var nextButton = $(".actions ul li:nth-child(2) a");
  nextButton.attr("href", "#next");
  buttonEnabled = $(".actions ul li:nth-child(2)")
    .removeClass("disabled")
    .attr("aria-disabled", "false");
}

function updateButton() {
  $('a[role="menuitem"]').addClass("btn btn-primary waves-effect waves-light");
  var text = $("input[type=radio][name=scan_mode]").val();
  if (text === "") {
    disableNext();
    return false;
  } else {
    enableNext();
    return true;
  }
}

$("#excludedPaths").selectize({
  persist: false,
  createOnBlur: true,
  create: true,
});
