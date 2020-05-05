jQuery(document).ready(function($) {
  
  $('.dropify').dropify({
      messages: { 'default': 'Click to Upload or Drag n Drop', 'remove':  '<i class="flaticon-close-fill"></i>', 'replace': 'Upload or Drag n Drop' }
  });

  // Save notification messagae
  $('#multiple-messages').on('click', function() {
      $.blockUI({
          message: $('.blockui-growl-message'), 
          fadeIn: 700, 
          fadeOut: 700, 
          timeout: 3000, //unblock after 3 seconds
          showOverlay: false, 
          centerY: false, 
          css: { 
              width: '250px',
              backgroundColor: 'transparent',
              top: '80px',
              left: 'auto',
              right: '15px',
              border: 0,
              opacity: .95,
              zIndex: 1200,
          } 
      }); 
  });

  setTimeout(function(){ $('.list-group-item.list-group-item-action').last().removeClass('active'); }, 100);

});

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