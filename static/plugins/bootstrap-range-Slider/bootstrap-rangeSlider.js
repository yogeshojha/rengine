// Bootstrap range slider

progressBarCount('.progress-range-counter');

function progressBarCount($progressCount) {
    var elements = document.querySelectorAll($progressCount);
    for (var i = 0; i < elements.length; i++) {
        elements[i].addEventListener('input', function(event) {
            getValueOfRangeSlider = this.value;
            getParentElement = this.closest(".custom-progress").querySelector('.range-count-number');

            setValueOfRangeCountValue = getParentElement.innerHTML = getValueOfRangeSlider;
            setValueOfAttributeValue = getParentElement.setAttribute("data-rangeCountNumber", getValueOfRangeSlider)
        });
    }
}
