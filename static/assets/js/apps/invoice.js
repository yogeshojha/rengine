$('.search > input').on('keyup', function() {
  var rex = new RegExp($(this).val(), 'i');
    $('.nav .nav-item').hide();
    $('.nav .nav-item').filter(function() {
        return rex.test($(this).text());
    }).show();
});

$('[data-toggle="tooltip"]').tooltip({
  'template': '<div class="tooltip actions-btn-tooltip" role="tooltip"><div class="arrow"></div><div class="tooltip-inner"></div></div>',
})

var $btns = $('.list-actions').click(function() {

  var getDataInvoiceAttr = $(this).attr('data-invoice-id');
  var getParentDiv = $(this).parents('.doc-container');
  var getParentInvListContainer = $(this).parents('.inv-list-container');

  var $el = $('.' + this.id).show();
  $('#ct > div').not($el).hide();
  var setInvoiceNumber = getParentDiv.find('.invoice-inbox .inv-number').text('#'+ getDataInvoiceAttr);
  var showInvHeaderSection = getParentDiv.find('.invoice-inbox .invoice-header-section').css('display', 'flex');
  var showInvContentSection = getParentDiv.find('.invoice-inbox #ct').css('display', 'block');
  var showInvContentSection = getParentDiv.find('.invoice-inbox').css('height', 'calc(100vh - 197px)');
  var hideInvEmptyContent = getParentDiv.find('.invoice-inbox .inv-not-selected').css('display', 'none');
  var hideInvEmptyContent = getParentDiv.find('.invoice-container .inv--thankYou').css('display', 'block');
  if ($(this).parents('.tab-title').hasClass('open-inv-sidebar')) {
    $(this).parents('.tab-title').removeClass('open-inv-sidebar');
  }
  $btns.removeClass('active');
  $(this).addClass('active');

  var myDiv = document.getElementsByClassName('invoice-inbox')[0];
  myDiv.scrollTop = 0;
})

$('.action-print').on('click', function(event) {
  event.preventDefault();
  /* Act on the event */
  window.print();
});

const ps = new PerfectScrollbar('.inv-list-container', {
  suppressScrollX : true
});


const inv_container = new PerfectScrollbar('.invoice-inbox', {
  suppressScrollX : true
});

if (window.innerWidth >= 768) {
  const inv_container = new PerfectScrollbar('.invoice-inbox', {
    suppressScrollX : true
  });
} else if (window.innerWidth < 768) {
  inv_container.destroy();
}


$('.hamburger, .inv-not-selected p').on('click', function(event) {
  $('.doc-container').find('.tab-title').toggleClass('open-inv-sidebar')
})