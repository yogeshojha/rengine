
$('.widget-content .message').on('click', function () {
  swal({
      title: 'Saved succesfully',
      padding: '2em'
    })
})

$('.widget-content .success').on('click', function () {
  swal({
      title: 'Good job!',
      text: "You clicked the!",
      type: 'success',
      padding: '2em'
    })

})

$('.widget-content .html-jquery').on('click', function () {
  swal({
    title: 'Custom animation with Animate.css',
    animation: false,
    customClass: 'animated tada',
    padding: '2em'
  })
})

$('.widget-content .title-text').on('click', function () {
  swal({
      title: 'The Internet?',
      text: "That thing is still around?",
      type: 'question',
      padding: '2em'
  })

})

$('.widget-content .custom-width-padding-background').on('click', function () {
  swal({
    title: 'Custom width, padding, background.',
    width: 600,
    padding: "7em",
    customClass: "background-modal",
    background: '#fff url(assets/img/600x300.jpg) no-repeat 100% 100%',
  })
})

$('.widget-content .warning.confirm').on('click', function () {
  swal({
      title: 'Are you sure?',
      text: "You won't be able to revert this!",
      type: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Delete',
      padding: '2em'
    }).then(function(result) {
      if (result.value) {
        swal(
          'Deleted!',
          'Your file has been deleted.',
          'success'
        )
      }
    })
})

$('.widget-content .warning.cancel').on('click', function () {
  const swalWithBootstrapButtons = swal.mixin({
    confirmButtonClass: 'btn btn-success',
    cancelButtonClass: 'btn btn-danger mr-3',
    buttonsStyling: false,
  })

  swalWithBootstrapButtons({
    title: 'Are you sure?',
    text: "You won't be able to revert this!",
    type: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Yes, delete it!',
    cancelButtonText: 'No, cancel!',
    reverseButtons: true,
    padding: '2em'
  }).then(function(result) {
    if (result.value) {
      swalWithBootstrapButtons(
        'Deleted!',
        'Your file has been deleted.',
        'success'
      )
    } else if (
      // Read more about handling dismissals
      result.dismiss === swal.DismissReason.cancel
    ) {
      swalWithBootstrapButtons(
        'Cancelled',
        'Your imaginary file is safe :)',
        'error'
      )
    }
  })
})

$('.widget-content .html').on('click', function () {
  swal({
    title: '<i>HTML</i> <u>example</u>',
    type: 'info',
    html:
      'You can use <b>bold text</b>, ' +
      '<a href="//github.com">links</a> ' +
      'and other HTML tags',
    showCloseButton: true,
    showCancelButton: true,
    focusConfirm: false,
    confirmButtonText:
      '<i class="flaticon-checked-1"></i> Great!',
    confirmButtonAriaLabel: 'Thumbs up, great!',
    cancelButtonText:
    '<i class="flaticon-cancel-circle"></i> Cancel',
    cancelButtonAriaLabel: 'Thumbs down',
    padding: '2em'
  })

})

$('.widget-content .custom-image').on('click', function () {
  swal({
    title: 'Sweet!',
    text: 'Modal with a custom image.',
    imageUrl: 'assets/img/300x300.jpg',
    imageWidth: 400,
    imageHeight: 200,
    imageAlt: 'Custom image',
    animation: false,
    padding: '2em'
  })
})

$('.widget-content .timer').on('click', function () {
  swal({
    title: 'Auto close alert!',
    text: 'I will close in 2 seconds.',
    timer: 2000,
    padding: '2em',
    onOpen: function () {
      swal.showLoading()
    }
  }).then(function (result) {
    if (
      // Read more about handling dismissals
      result.dismiss === swal.DismissReason.timer
    ) {
      console.log('I was closed by the timer')
    }
  })
})

$('.widget-content .chaining-modals').on('click', function () {
  swal.mixin({
    input: 'text',
    confirmButtonText: 'Next &rarr;',
    showCancelButton: true,
    progressSteps: ['1', '2', '3'],
    padding: '2em',
  }).queue([
    {
      title: 'Question 1',
      text: 'Chaining swal2 modals is easy'
    },
    'Question 2',
    'Question 3'
  ]).then(function(result) {
    if (result.value) {
      swal({
        title: 'All done!',
        padding: '2em',
        html:
          'Your answers: <pre>' +
            JSON.stringify(result.value) +
          '</pre>',
        confirmButtonText: 'Lovely!'
      })
    }
  })
})

$('.widget-content .dynamic-queue').on('click', function () {
  const ipAPI = 'https://api.ipify.org?format=json'
  swal.queue([{
    title: 'Your public IP',
    confirmButtonText: 'Show my public IP',
    text:
      'Your public IP will be received ' +
      'via AJAX request',
    showLoaderOnConfirm: true,
    preConfirm: function() {
      return fetch(ipAPI)
        .then(function (response) { 
            return response.json();
        })
        .then(function(data) {
           return swal.insertQueueStep(data.ip)
        })
        .catch(function() {
          swal.insertQueueStep({
            type: 'error',
            title: 'Unable to get your public IP'
          })
        })
    }
  }])

})

$('.widget-content .footer').on('click', function () {
  swal({
    type: 'error',
    title: 'Oops...',
    text: 'Something went wrong!',
    footer: '<a href>Why do I have this issue?</a>',
    padding: '2em'
  })
})

$('.widget-content .RTL').on('click', function () {
  swal({
    title: 'هل تريد الاستمرار؟',
    confirmButtonText:  'نعم',
    cancelButtonText:  'لا',
    showCancelButton: true,
    showCloseButton: true,
    padding: '2em',
    target: document.getElementById('rtl-container')
  })

})

$('.widget-content .mixin').on('click', function () {
  const toast = swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    padding: '2em'
  });
  toast({
    type: 'success',
    title: 'Signed in successfully',
    padding: '2em',
  })

})