function schedulerChanged(selectObject) {
  selectedValue = selectObject.value;
  if (selectedValue == "periodic") {
    var clockedDiv = document.getElementById("clocked-div");
    clockedDiv.classList.remove("show");
    clockedDiv.classList.remove("active");
    var periodicDiv = document.getElementById("periodic-div");
    periodicDiv.classList.add("show");
    periodicDiv.classList.add("active");
  } else if (selectedValue == "clocked") {
    var periodicDiv = document.getElementById("periodic-div");
    periodicDiv.classList.remove("show");
    periodicDiv.classList.remove("active");
    var clockedDiv = document.getElementById("clocked-div");
    clockedDiv.classList.add("show");
    clockedDiv.classList.add("active");
  }
}

var buttonEnabled = true;
var globalTimeout = 0;

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
  var text = $("input[type=radio][name=scan_mode]").val();
  if (text === "") {
    disableNext();
    return false;
  } else {
    enableNext();
    return true;
  }
}

function initTimer() {
  if (globalTimeout) clearTimeout(globalTimeout);
  globalTimeout = setTimeout(updateButton, 400);
}

$("#schedule_scan_steps").steps({
  headerTag: "h3",
  bodyTag: "div",
  transitionEffect: "slide",
  cssClass: "pill wizard",
  enableKeyNavigation: false,
  onStepChanging: updateButton,
  labels: { finish: "Schedule Scan" },
  onInit: function (event, current) {
    $('a[role="menuitem"]').addClass("text-white");
    $(".actions ul li:nth-child(3) a").attr(
      "onclick",
      `$(this).closest('form').submit()`
    );
    flatpickr(document.getElementById("clockedTime"), {
      enableTime: true,
      dateFormat: "Y-m-d H:i",
    });
    // $(".basic").select2({
    //   minimumResultsForSearch: -1
    // });
  },
  onStepChanged: function (event, currentIndex, priorIndex) {
    if (currentIndex == 1) {
      $("input[type=radio][name=scan_mode]").change(initTimer).keyup(initTimer);
      disableNext();
    }
  },
});

$("#excludedPaths").selectize({
  persist: false,
  createOnBlur: true,
  create: true,
});
