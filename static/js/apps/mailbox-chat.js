$('.search > input').on('keyup', function() {
  var rex = new RegExp($(this).val(), 'i');
    $('.people .person').hide();
    $('.people .person').filter(function() {
        return rex.test($(this).text());
    }).show();
});

$('.user-list-box .person').on('click', function(event) {
    if ($(this).hasClass('.active')) {
        return false;
    } else {
        var findChat = $(this).attr('data-chat');
        var personName = $(this).find('.user-name').text();
        var personImage = $(this).find('img').attr('src');
        var hideTheNonSelectedContent = $(this).parents('.chat-system').find('.chat-box .chat-not-selected').hide();
        var showChatInnerContent = $(this).parents('.chat-system').find('.chat-box .chat-box-inner').show();

        if (window.innerWidth <= 767) {
          $('.chat-box .current-chat-user-name .name').html(personName.split(' ')[0]);
        } else if (window.innerWidth > 767) {
          $('.chat-box .current-chat-user-name .name').html(personName);
        }
        $('.chat-box .current-chat-user-name img').attr('src', personImage);
        $('.chat').removeClass('active-chat');
        $('.user-list-box .person').removeClass('active');
        $('.chat-box .chat-box-inner').css('height', '100%');
        $(this).addClass('active');
        $('.chat[data-chat = '+findChat+']').addClass('active-chat');
    }
    if ($(this).parents('.user-list-box').hasClass('user-list-box-show')) {
      $(this).parents('.user-list-box').removeClass('user-list-box-show');
    }
    $('.chat-meta-user').addClass('chat-active');
    $('.chat-box').css('height', 'calc(100vh - 233px)');
    $('.chat-footer').addClass('chat-active');

  const ps = new PerfectScrollbar('.chat-conversation-box', {
    suppressScrollX : true
  });

  const getScrollContainer = document.querySelector('.chat-conversation-box');
  getScrollContainer.scrollTop = 0;
});

const ps = new PerfectScrollbar('.people', {
  suppressScrollX : true
});

function callOnConnect() {
  var getCallStatusText = $('.overlay-phone-call .call-status');
  var getCallTimer = $('.overlay-phone-call .timer');
  var setCallStatusText = getCallStatusText.text('Connected');
  var setCallTimerDiv = getCallTimer.css('visibility', 'visible');
}

$('.phone-call-screen').off('click').on('click', function(event) {
  var getCallingUserName = $(this).parents('.chat-system').find('.person.active .user-name').attr('data-name');
  var getCallingUserImg = $(this).parents('.chat-system').find('.person.active .f-head img').attr('src');
  var setCallingUserName = $(this).parents('.chat-box').find('.overlay-phone-call .user-name').text(getCallingUserName);
  var setCallingUserName = $(this).parents('.chat-box').find('.overlay-phone-call .calling-user-img img').attr('src', getCallingUserImg);
  var applyOverlay = $(this).parents('.chat-box').find('.overlay-phone-call').addClass('phone-call-show');
  setTimeout(callOnConnect, 2000);
})

$('.switch-to-video-call').off('click').on('click', function(event) {
    var getCallerId = $(this).parents('.overlay-phone-call').find('.user-name').text();
    var getCallerImg = $(this).parents('.overlay-phone-call').find('.calling-user-img img').attr('src');
    $(this).parents('.overlay-phone-call').removeClass('phone-call-show');
    $('.overlay-video-call').addClass('video-call-show');
    $('.overlay-video-call').find('.user-name').text(getCallerId);
    $('.overlay-video-call').find('.calling-user-img img').attr('src', getCallerImg);
    var removeOverlay = $(this).parents('.overlay-phone-call').removeClass('phone-call-show');
    var getCallStatusText = $(this).parents('.overlay-phone-call').find('.call-status').text('Calling...');
    var getCallStatusTimer = $(this).parents('.overlay-phone-call').find('.timer').removeAttr('style');
    setTimeout(videoCallOnConnect, 2000);
})
$('.switch-to-microphone').off('click').on('click', function(event) {
  var toggleClass = $(this).toggleClass('micro-off');
})
$('.cancel-call').on('click', function(event) {

    if ($(this).parents('.overlay-phone-call').hasClass('phone-call-show')) {
      var removeOverlay = $(this).parents('.overlay-phone-call').removeClass('phone-call-show');
      var getCallStatusText = $(this).parents('.overlay-phone-call').find('.call-status').text('Calling...');
      var getCallStatusTimer = $(this).parents('.overlay-phone-call').find('.timer').removeAttr('style');
    } else if ($(this).parents('.overlay-video-call').hasClass('video-call-show')) {
      var removeOverlay = $(this).parents('.overlay-video-call').removeClass('video-call-show');
      var setCallStatusText =  $(this).parents('.overlay-video-call').find('.call-status').text('Calling...');
      var removeVideoConnectClass = $(this).parents('.overlay-video-call').removeClass('onConnect');
      var displayCallerImage = $(this).parents('.overlay-video-call').find('.calling-user-img').css('display', 'block');
      var hideVideoCallTimerDiv = $(this).parents('.overlay-video-call').find('.timer').removeAttr('style');
    }
})
$('.go-back-chat').on('click', function(event) {

  if ($(this).parents('.overlay-phone-call').hasClass('phone-call-show')) {
    var removeOverlay = $(this).parents('.chat-box').find('.overlay-phone-call').removeClass('phone-call-show');
  } else if ($(this).parents('.overlay-video-call').hasClass('video-call-show')) {
    var removeOverlay = $(this).parents('.chat-box').find('.overlay-video-call').removeClass('video-call-show')
  }

})

function videoCallOnConnect() {
  var getVideoCallingDiv = $('.overlay-video-call');
  var setVideoCallingImage = getVideoCallingDiv.addClass('onConnect');
  var getCallStatusText = $('.overlay-video-call .call-status');
  var getCallStatusImage = $('.overlay-video-call .calling-user-img');
  var getCallTimer = $('.overlay-video-call .timer');
  var setCallStatusText = getCallStatusText.text('Connected');
  var setVideoCallingImage = getCallStatusImage.css('display', 'none');
  var setVideoCallTimerDiv = getCallTimer.css('visibility', 'visible');
}

$('.video-call-screen').off('click').on('click', function(event) {
  var getCallingUserName = $(this).parents('.chat-system').find('.person.active .user-name').attr('data-name');
  var getCallingUserImg = $(this).parents('.chat-system').find('.person.active .f-head img').attr('src');
  var setCallingUserName = $(this).parents('.chat-box').find('.overlay-video-call .user-name').text(getCallingUserName);
  var setCallingUserName = $(this).parents('.chat-box').find('.overlay-video-call .calling-user-img img').attr('src', getCallingUserImg);
  var applyOverlay = $(this).parents('.chat-box').find('.overlay-video-call').addClass('video-call-show');
  setTimeout(videoCallOnConnect, 2000);
})
$('.switch-to-phone-call').off('click').on('click', function(event) {
    var getCallerId = $(this).parents('.overlay-video-call').find('.user-name').text();
    var getCallerImg = $(this).parents('.overlay-video-call').find('.calling-user-img img').attr('src');

    $(this).parents('.overlay-video-call').removeClass('video-call-show');
    $('.overlay-phone-call').addClass('phone-call-show');
    $('.overlay-phone-call').find('.user-name').text(getCallerId);
    $('.overlay-phone-call').find('.calling-user-img img').attr('src', getCallerImg);

    var removeOverlay = $(this).parents('.overlay-video-call').removeClass('video-call-show');
    var setCallStatusText =  $(this).parents('.overlay-video-call').find('.call-status').text('Calling...');
    var removeVideoConnectClass = $(this).parents('.overlay-video-call').removeClass('onConnect');
    var displayCallerImage = $(this).parents('.overlay-video-call').find('.calling-user-img').css('display', 'block');
    var hideVideoCallTimerDiv = $(this).parents('.overlay-video-call').find('.timer').removeAttr('style');
    setTimeout(callOnConnect, 2000);
})

$('.mail-write-box').on('keydown', function(event) {
    if(event.key === 'Enter') {
        var chatInput = $(this);
        var chatMessageValue = chatInput.val();
        if (chatMessageValue === '') { return; }
        $messageHtml = '<div class="bubble me">' + chatMessageValue + '</div>';
        var appendMessage = $(this).parents('.chat-system').find('.active-chat').append($messageHtml);
        const getScrollContainer = document.querySelector('.chat-conversation-box');
        getScrollContainer.scrollTop = getScrollContainer.scrollHeight;
        var clearChatInput = chatInput.val('');
    }
})

$('.hamburger, .chat-system .chat-box .chat-not-selected p').on('click', function(event) {
  $(this).parents('.chat-system').find('.user-list-box').toggleClass('user-list-box-show')
})