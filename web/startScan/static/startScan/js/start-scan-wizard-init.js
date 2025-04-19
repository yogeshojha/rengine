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
    $(".actions ul li:nth-child(3) a")
      .attr("onclick", `$(this).closest('form').submit()`)
      .addClass("text-white");
    $(".actions ul li:nth-child(1) a[href='#previous']").removeClass(
      "btn btn-primary waves-effect waves-light"
    );
    disableNext();
    updateButton();
    updatePreviousButton();
  },
});

$("input[type=radio][name=scan_mode]").change(initTimer).keyup(initTimer);
// $('a[role="menuitem"]').addClass("text-white");

function initTimer() {
  if (globalTimeout) clearTimeout(globalTimeout);
  globalTimeout = setTimeout(updateButton, 400);
}

function disableNext() {
  var nextButton = $(".actions ul li:nth-child(2) a");
  nextButton.attr("href", "#");
  nextButton.removeClass("btn btn-primary waves-effect waves-light text-white");
  buttonEnabled = false;
  $(".actions ul li:nth-child(2)")
    .addClass("disabled")
    .attr("aria-disabled", "true");
}

function enableNext() {
  var nextButton = $(".actions ul li:nth-child(2) a");
  nextButton.attr("href", "#next");
  buttonEnabled = true;
  nextButton.addClass("btn btn-primary waves-effect waves-light text-white");
  $(".actions ul li:nth-child(2)")
    .removeClass("disabled")
    .attr("aria-disabled", "false");
}

function updateButton() {
  var selectedEngine = $("input[type=radio][name=scan_mode]:checked").val();
  if (selectedEngine) {
    enableNext();
  } else {
    disableNext();
  }
  updatePreviousButton();
  return buttonEnabled;
}

function updatePreviousButton() {
  var previousButton = $("a[href='#previous']");
  if (previousButton.parent().hasClass("disabled")) {
    previousButton.removeClass("text-white");
  } else {
    previousButton.addClass("text-white");
  }
}

$("#select_engine").on("steps.change", function (e, currentIndex, newIndex) {
  setTimeout(updatePreviousButton, 0);
});

$("#excludedPaths").selectize({
  persist: false,
  createOnBlur: true,
  create: true,
});
