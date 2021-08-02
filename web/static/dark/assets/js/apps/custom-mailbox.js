$(document).ready(function() {


	var today = new Date();
  	var dd = String(today.getDate()).padStart(2, '0');
  	var mm = String(today.getMonth() + 1).padStart(2, '0'); //January is 0!
  	var yyyy = today.getFullYear();
  	var today = mm + '/' + dd + '/' + yyyy;

  	$('.current-recent-mail').text(today + ' -')


	// Applying Scroll Bar

	const ps = new PerfectScrollbar('.message-box-scroll');
	const mailScroll = new PerfectScrollbar('.mail-sidebar-scroll', {
		suppressScrollX : true
	});

	function mailInboxScroll() {
		$('.mailbox-inbox .collapse').each(function(){ const mailContainerScroll = new PerfectScrollbar($(this)[0], {
			suppressScrollX : true
		}); });
	}
	mailInboxScroll();


	/*
		fn. dynamicBadgeNotification ==> Get the badge count for mail sidebar
	*/
	function dynamicBadgeNotification( setMailCategoryCount ) {
		var mailCategoryCount = setMailCategoryCount;

		// Get Parents Div(s)
		var get_ParentsDiv = $('.mail-item');
		var get_MailInboxParentsDiv = $('.mail-item.mailInbox');
		var get_UnreadMailInboxParentsDiv = $('[id*="unread-"]');
		var get_DraftParentsDiv = $('.mail-item.draft');

		// Get Parents Div(s) Counts
		var get_MailInboxElementsCount = get_MailInboxParentsDiv.length;
		var get_UnreadMailInboxElementsCount = get_UnreadMailInboxParentsDiv.length;
		var get_DraftElementsCount = get_DraftParentsDiv.length;

		// Get Badge Div(s)
		var getBadgeMailInboxDiv = $('#mailInbox .mail-badge');
		var getBadgeDraftMailDiv = $('#draft .mail-badge');

		if (mailCategoryCount === 'mailInbox') {
			if (get_UnreadMailInboxElementsCount === 0) {
				getBadgeMailInboxDiv.text('');
				return;
			}
			getBadgeMailInboxDiv.text(get_UnreadMailInboxElementsCount);
		} else if (mailCategoryCount === 'draftmail') {
			if (get_DraftElementsCount === 0) {
				getBadgeDraftMailDiv.text('');
				return;
			}
			getBadgeDraftMailDiv.text(get_DraftElementsCount);
		}
	}

	dynamicBadgeNotification('mailInbox');
	dynamicBadgeNotification('draftmail');

	// Open Modal on Compose Button Click
	$('#btn-compose-mail').on('click', function(event) {
		$('#btn-send').show();
		$('#btn-reply').hide();
		$('#btn-fwd').hide();
		$('#composeMailModal').modal('show');

		// Save And Reply Save
		$('#btn-save').show();
		$('#btn-reply-save').hide();
		$('#btn-fwd-save').hide();
	})

	/*
		Init. fn. checkAll ==> Checkbox check all
	*/
	document.getElementById('inboxAll').addEventListener('click', function() {
		var getActiveList = document.querySelectorAll('.tab-title .list-actions.active');
		var getActiveListID = '.'+getActiveList[0].id;

		var getItemsCheckboxes = '';

		if (getActiveList[0].id === 'personal' || getActiveList[0].id === 'work' || getActiveList[0].id === 'social' || getActiveList[0].id === 'private') {

			getItemsGroupCheckboxes = document.querySelectorAll(getActiveListID);
			for (var i = 0; i < getItemsGroupCheckboxes.length; i++) {
				getItemsGroupCheckboxes[i].parentNode.parentNode.parentNode;

				getItemsCheckboxes = document.querySelectorAll('.'+getItemsGroupCheckboxes[i].parentNode.parentNode.parentNode.className.split(' ')[0] + ' ' + getActiveListID + ' .inbox-chkbox');
				
				if (getItemsCheckboxes[i].checked) {
					getItemsCheckboxes[i].checked = false;
				} else {
					if (this.checked) {
						getItemsCheckboxes[i].checked = true;
					}
				}
			}

		} else {
			getItemsCheckboxes = document.querySelectorAll('.mail-item'+getActiveListID + ' .inbox-chkbox');
			for (var i = 0; i < getItemsCheckboxes.length; i++ ) {
				if (getItemsCheckboxes[i].checked) {
					getItemsCheckboxes[i].checked = false;
				} else {
					if (this.checked) {
						getItemsCheckboxes[i].checked = true;
					}
				}
			}
		}
	})

	/*
		fn. randomString ==> Generate Random Numbers
	*/
	function randomString(length, chars) {
		var result = '';
		for (var i = length; i > 0; --i) result += chars[Math.round(Math.random() * (chars.length - 1))];
		return result;
	}

	/*
		fn. formatAMPM ==> Get Time in 24hr Format
	*/
	function formatAMPM(date) {
	  var hours = date.getHours();
	  var minutes = date.getMinutes();
	  var ampm = hours >= 12 ? 'PM' : 'AM';
	  hours = hours % 12;
	  hours = hours ? hours : 12; // the hour '0' should be '12'
	  minutes = minutes < 10 ? '0'+minutes : minutes;
	  var strTime = hours + ':' + minutes + ' ' + ampm;
	  return strTime;
	}

	/*
		fn. formatBytes ==> Calculate and convert bytes into ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
	*/
	function formatBytes(bytes, decimals) {
	    if (bytes === 0) return '0 Bytes';
	    const k = 1024;
	    const dm = decimals < 0 ? 0 : decimals;
	    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
	    const i = Math.floor(Math.log(bytes) / Math.log(k));
	    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
	}

	// Search on each key pressed

	$('.input-search').on('keyup', function() {
	  var rex = new RegExp($(this).val(), 'i');
	    $('.message-box .mail-item').hide();
	    $('.message-box .mail-item').filter(function() {
	        return rex.test($(this).text());
	    }).show();
	});

	// Tooltip

	$('[data-toggle="tooltip"]').tooltip({
	    'template': '<div class="tooltip actions-btn-tooltip" role="tooltip"><div class="arrow"></div><div class="tooltip-inner"></div></div>',
	})

	// Triggered when mail is Closed

	$('.close-message').on('click', function(event) {
		event.preventDefault();
		$('.content-box .collapse').collapse('hide')
		$(this).parents('.content-box').css({
			width: '0',
			left: 'auto',
			right: '-46px'
		});
	});

	// Open Mail Sidebar on resolution below or equal to 991px.

	$('.mail-menu').on('click', function(e){
		$(this).parents('.mail-box-container').children('.tab-title').addClass('mail-menu-show')
		$(this).parents('.mail-box-container').children('.mail-overlay').addClass('mail-overlay-show')
	})

	// Close sidebar when clicked on ovelay ( and ovelay itself ).

	$('.mail-overlay').on('click', function(e){
		$(this).parents('.mail-box-container').children('.tab-title').removeClass('mail-menu-show')
		$(this).removeClass('mail-overlay-show')
	})

	/*
		fn. contentBoxPosition ==> Triggered when clicked on any each mail to show the mail content.
	*/
	function contentBoxPosition() {
		$('.content-box .collapse').on('show.bs.collapse', function(event) {
			var getCollpaseElementId = this.id;
			var getSelectedMailTitleElement = $('.content-box').find('.mail-title');
			var getSelectedMailContentTitle = $(this).find('.mail-content').attr('data-mailTitle');
			$(this).parent('.content-box').css({
				width: '100%',
				left: '0',
				right: '100%'
			});
			$(this).parents('#mailbox-inbox').find('.message-box [data-target="#'+getCollpaseElementId+'"]').parents('.mail-item').removeAttr('id');
			getSelectedMailTitleElement.text(getSelectedMailContentTitle);
			getSelectedMailTitleElement.attr('data-selectedMailTitle', getSelectedMailContentTitle);
			dynamicBadgeNotification('mailInbox');
		})
	}
	function stopPropagations() {
		$('.mail-item-heading .mail-item-inner .new-control').on('click', function(e){
		    e.stopPropagation();
		})
	}

	/*
		====================
			Quill Editor
		====================
	*/

	var quill = new Quill('#editor-container', {
	  modules: {
	    toolbar: [
	      [{ header: [1, 2, false] }],
	      ['bold', 'italic', 'underline'],
	      ['image', 'code-block']
	    ]
	  },
	  placeholder: 'Compose an epic...',
	  theme: 'snow'  // or 'bubble'
	});

	// Validating input fields

	var $_getValidationField = document.getElementsByClassName('validation-text');
	var emailReg = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

	getEmailToInput = document.getElementById('m-to');

	getEmailToInput.addEventListener('input', function() {

	  	getEmailToInputValue = this.value;

	    if (getEmailToInputValue == "") {
	      $_getValidationField[0].innerHTML = 'Email Required';
	      $_getValidationField[0].style.display = 'block';
	    } else if((emailReg.test(getEmailToInputValue) == false)) {
	      $_getValidationField[0].innerHTML = 'Invalid Email';
	      $_getValidationField[0].style.display = 'block';
	    } else {
	      $_getValidationField[0].style.display = 'none';
	    }
	})

	getCCEmailInput = document.getElementById('m-cc');
	getCCEmailInput.addEventListener('input', function() {

	    getCCEmailInputValue = this.value;

	    if (!getCCEmailInputValue == "") {
	       if((emailReg.test(getCCEmailInputValue) == false)) {
		      $_getValidationField[1].innerHTML = 'Invalid Email';
		      $_getValidationField[1].style.display = 'block';
		    } else {
		      	$_getValidationField[1].style.display = 'none';
		    }
	    } else {
	      $_getValidationField[1].style.display = 'none';
	    }

	})

	getSubjectInput = document.getElementById('m-subject');

	getSubjectInput.addEventListener('input', function() {

	  getSubjectInput = this.value;

	  if (getSubjectInput == "") {
	    $_getValidationField[2].innerHTML = 'Subject Required';
	    $_getValidationField[2].style.display = 'block';
	  } else {
	    $_getValidationField[2].style.display = 'none';
	  }

	})

	$('#composeMailModal').on('hidden.bs.modal', function (e) {
	    
	  	$(this)
	    .find("input,textarea")
	       .val('')
	       .end();

	    quill.deleteText(0, 2000);

	    for (var i = 0; i < $_getValidationField.length; i++) {
	      e.preventDefault();
	      $_getValidationField[i].style.display = 'none';
	    }
	})

	
	/*
		=========================
			Tab Functionality
		=========================
	*/
	var $listbtns = $('.list-actions').click(function() {
		$(this).parents('.mail-box-container').find('.mailbox-inbox > .content-box').css({
			width: '0',
			left: 'auto',
			right: '-46px'
		});
		$('.content-box .collapse').collapse('hide');
		var getActionCenterDivElement = $(this).parents('.mail-box-container').find('.action-center');
	  	if (this.id == 'mailInbox') {
			var $el = $('.' + this.id).show();
			getActionCenterDivElement.removeClass('tab-trash-active');
			$('#ct > div').not($el).hide();
	  	} else if (this.id == 'personal') {
	  		$el = '.' + $(this).attr('id');
	  		$elShow = $($el).show();
	  		getActionCenterDivElement.removeClass('tab-trash-active');
		    $('#ct > div .mail-item-heading'+$el).parents('.mail-item').show();
		    $('#ct > div .mail-item-heading').not($el).parents('.mail-item').hide();
	  	} else if (this.id == 'work') {
		    $el = '.' + $(this).attr('id');
	  		$elShow = $($el).show();
	  		getActionCenterDivElement.removeClass('tab-trash-active');
		    $('#ct > div .mail-item-heading'+$el).parents('.mail-item').show();
		    $('#ct > div .mail-item-heading').not($el).parents('.mail-item').hide();
	  	} else if (this.id == 'social') {
		    $el = '.' + $(this).attr('id');
	  		$elShow = $($el).show();
	  		getActionCenterDivElement.removeClass('tab-trash-active');
		    $('#ct > div .mail-item-heading'+$el).parents('.mail-item').show();
		    $('#ct > div .mail-item-heading').not($el).parents('.mail-item').hide();
	  	} else if (this.id == 'private') {
		    $el = '.' + $(this).attr('id');
	  		$elShow = $($el).show();
	  		getActionCenterDivElement.removeClass('tab-trash-active');
		    $('#ct > div .mail-item-heading'+$el).parents('.mail-item').show();
		    $('#ct > div .mail-item-heading').not($el).parents('.mail-item').hide();
	  		getActionCenterDivElement.removeClass('tab-trash-active');
	  	} else if (this.id == 'trashed') {
	  		var $el = $('.' + this.id).show();
	  		getActionCenterDivElement.addClass('tab-trash-active');
			$('#ct > div').not($el).hide();
	  	} else {
	    	var $el = $('.' + this.id).show();
	    	getActionCenterDivElement.removeClass('tab-trash-active');
	    	$('#ct > div').not($el).hide();
	  	}
	  	$listbtns.removeClass('active');
	  	$(this).addClass('active');
	})

	setTimeout(function() {
        $(".list-actions#mailInbox").trigger('click');
    },10);

	// Mark As Important
	$(".action-important").on("click", function() {
		var notificationText = '';
		var getCheckedItemlength = $(".inbox-chkbox:checked").length;

		if ($(".inbox-chkbox:checked").parents('.mail-item').hasClass('important')) {
			var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail removed from Important' : getCheckedItemlength + ' Mails removed from Important';
		} else {
			var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail Added to Important' : getCheckedItemlength + ' Mails Added to Important';
		}

	  	$(".inbox-chkbox:checked").parents('.mail-item').toggleClass('important');
 		$(".inbox-chkbox:checked").prop('checked',false);
 		$("#inboxAll:checked").prop('checked',false);
 		$(".list-actions#important").trigger('click');
		Snackbar.show({
	        text: notificationText,
	        width: 'auto',
	        pos: 'top-center',
	        actionTextColor: '#bfc9d4',
	        backgroundColor: '#515365'
	    });
	});

	// Mark as Span
	$(".action-spam").on("click", function() {
		var inboxCheckboxParents = $(".inbox-chkbox:checked").parents('.mail-item');
		var mailItemClass = inboxCheckboxParents.attr('class').split(' ')[1];
		var mailItemClassRemoveClass = inboxCheckboxParents.toggleClass('mailInbox');

		var notificationText = '';
		var getCheckedItemlength = $(".inbox-chkbox:checked").length;

		if ($(".inbox-chkbox:checked").parents('.mail-item').hasClass('spam')) {
			var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail removed from Spam' : getCheckedItemlength + ' Mails removed from Spam';
		} else {
			var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail Added to Spam' : getCheckedItemlength + ' Mails Added to Spam';
		}
	  	inboxCheckboxParents.toggleClass('spam');
 		$(".inbox-chkbox:checked").prop('checked',false);
 		$("#inboxAll:checked").prop('checked',false);
 		$(".list-actions#spam").trigger('click');

 		Snackbar.show({
	        text: notificationText,
	        width: 'auto',
	        pos: 'top-center',
	        actionTextColor: '#bfc9d4',
	        backgroundColor: '#515365'
	    });
	});

	// Mark as read
	$(".action-mark_as_read").on("click", function() {
		var inboxCheckboxParents = $(".inbox-chkbox:checked").parents('.mail-item');

		var notificationText = '';
		var getCheckedItemlength = $(".inbox-chkbox:checked").length;
		var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail marked as Read' : getCheckedItemlength + ' Mails marked as Read';

		inboxCheckboxParents.removeAttr('id');
		dynamicBadgeNotification('mailInbox');
 		$("#inboxAll:checked").prop('checked',false);
 		$(".inbox-chkbox:checked").prop('checked',false);

 		Snackbar.show({
	        text: notificationText,
	        width: 'auto',
	        pos: 'top-center',
	        actionTextColor: '#bfc9d4',
	        backgroundColor: '#515365'
	    });
	})

	// Mark as Unread
	$(".action-mark_as_unRead").on("click", function() {
		var inboxCheckboxParents = $(".inbox-chkbox:checked").parents('.mail-item');
		var getMailTitle = inboxCheckboxParents.find('.mail-title').attr('data-mailtitle');
		var randomAlphaNumeric = randomString(10, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ');

		var notificationText = '';
		var getCheckedItemlength = $(".inbox-chkbox:checked").length;
		var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail marked as UnRead' : getCheckedItemlength + ' Mails marked as UnRead';

		inboxCheckboxParents.attr('id', 'unread-'+getMailTitle.replace(/\s+/g, '-').toLowerCase()+randomAlphaNumeric);
		dynamicBadgeNotification('mailInbox');
 		$("#inboxAll:checked").prop('checked',false);
 		$(".inbox-chkbox:checked").prop('checked',false);

 		Snackbar.show({
	        text: notificationText,
	        width: 'auto',
	        pos: 'top-center',
	        actionTextColor: '#bfc9d4',
	        backgroundColor: '#515365'
	    });

	})

	// Delete a mail
	$(".action-delete").on("click", function() {
		var inboxCheckboxParents = $(".inbox-chkbox:checked").parents('.mail-item');
		var inboxMailItemClass = inboxCheckboxParents.attr('class');
        var getFirstClass = inboxMailItemClass.split(' ')[1];
        var getSecondClass = inboxMailItemClass.split(' ')[2];
        var getThirdClass = inboxMailItemClass.split(' ')[3];
        var getFourthClass = inboxMailItemClass.split(' ')[4];
        var getFifthClass = inboxMailItemClass.split(' ')[5];

        var notificationText = '';
		var getCheckedItemlength = $(".inbox-chkbox:checked").length;

		var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail Deleted' : getCheckedItemlength + ' Mails Deleted';

        if (getFirstClass === 'mailInbox' || getFirstClass === 'sentmail' || getFirstClass === 'draft' || getFirstClass === 'spam') {
          inboxCheckboxParents.removeClass(getFirstClass);
        }
        if (getSecondClass === 'mailInbox' || getSecondClass === 'important') {
          inboxCheckboxParents.removeClass(getSecondClass);
        }
	  	inboxCheckboxParents.addClass('trashed');
 		$(".inbox-chkbox:checked").prop('checked',false);
 		$("#inboxAll:checked").prop('checked',false);
 		$(".list-actions#trashed").trigger('click');

 		Snackbar.show({
	        text: notificationText,
	        width: 'auto',
	        pos: 'top-center',
	        actionTextColor: '#bfc9d4',
	        backgroundColor: '#515365'
	    });
	});

	// Revive Mail from Tash
	$(".revive-mail").on("click", function() {
		var inboxCheckboxParents = $(".inbox-chkbox:checked").parents('.mail-item');
		var inboxMailItemClass = inboxCheckboxParents.attr('class');
		var getFirstClass = inboxMailItemClass.split(' ')[1];

		var notificationText = '';
		var getCheckedItemlength = $(".inbox-chkbox:checked").length;
		var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail restored' : getCheckedItemlength + ' Mails restored';


		inboxCheckboxParents.removeClass(getFirstClass);
		inboxCheckboxParents.addClass('mailInbox');
 		$(".inbox-chkbox:checked").prop('checked',false);
 		$("#inboxAll:checked").prop('checked',false);
 		$(".list-actions#mailInbox").trigger('click');

 		Snackbar.show({
	        text: notificationText,
	        width: 'auto',
	        pos: 'top-center',
	        actionTextColor: '#bfc9d4',
	        backgroundColor: '#515365'
	    });
	})

	// Permanently Delete Mail
	$(".permanent-delete").on("click", function() {
		var inboxCheckboxParents = $(".inbox-chkbox:checked").parents('.mail-item');

		var notificationText = '';
		var getCheckedItemlength = $(".inbox-chkbox:checked").length;
		var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail Permanently Deleted' : getCheckedItemlength + ' Mails Permanently Deleted';

		if (inboxCheckboxParents.hasClass('trashed')) {
			inboxCheckboxParents.remove();
		}
 		$("#inboxAll:checked").prop('checked',false);

 		Snackbar.show({
	        text: notificationText,
	        width: 'auto',
	        pos: 'top-center',
	        actionTextColor: '#bfc9d4',
	        backgroundColor: '#515365'
	    });
	})

	// Mark mail Priority/Groups as [ Personal, Work, Social, Private ]
	$(".label-group-item").on("click", function() {
		var getLabelColor = $(this).attr('class').split(' ')[1];
		var splitLabelColor = getLabelColor.split('-')[1];


		var notificationText = '';
		var getCheckedItemlength = $(".inbox-chkbox:checked").length;

		if ($(".inbox-chkbox:checked").parents('.mail-item-heading').hasClass(splitLabelColor)) {
			var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail removed from '+ splitLabelColor.toUpperCase() +' Group' : getCheckedItemlength + ' Mails removed from '+ splitLabelColor.toUpperCase() +' Group';
		} else {
			var notificationText = getCheckedItemlength < 2 ? getCheckedItemlength + ' Mail Grouped as ' + splitLabelColor.toUpperCase() : getCheckedItemlength + ' Mails Grouped as ' + splitLabelColor.toUpperCase();
		}


	  	$(".inbox-chkbox:checked").parents('.mail-item-heading').toggleClass(splitLabelColor);
 		$(".inbox-chkbox:checked").prop('checked',false);
 		$("#inboxAll:checked").prop('checked',false);

 		Snackbar.show({
	        text: notificationText,
	        width: 'auto',
	        pos: 'top-center',
	        actionTextColor: '#bfc9d4',
	        backgroundColor: '#515365'
	    });
	});

	/*
		fn. $_sendMail ==> Trigger when clicked on Send Mail Button in Modal.
	*/
	function $_sendMail(getDraftTragetID) {
		$("#btn-send").off('click').on('click', function(event) {
			event.preventDefault();
			/* Act on the event */
			draftTragetID = getDraftTragetID;

		  	var $_mailFrom = document.getElementById('m-form').value;
		  	var $_mailTo = document.getElementById('m-to').value;

		  	var $_mailCC = document.getElementById('m-cc').value;
		  	var $_mailAttachment = document.getElementById('mail_File_attachment');
		  	var $_mailSubject = document.getElementById('m-subject').value;
		  	var $_mailDescriptionText = quill.getText();
		  	var $_mailDescriptionInnerHTML = quill.root.innerHTML;

		  	var delta = quill.getContents();
		  	var $_textDelta = JSON.stringify(delta);

		  	var $outerAttachmentHTML = '';
		  	var $innerAttachmentHTML = '';
		  	var getSVG = '';
		  	if ($_mailAttachment.files.length >= 1) {
				for (var i = 0; i < $_mailAttachment.files.length; ++i) {
				  	$outerAttachmentHTML += '<span class="">'+ $_mailAttachment.files.item(i).name +'</span>';

				  	// Dectecting the format/type of the uploaded file for appling the icon/svg accordingly 
					if ($_mailAttachment.files.item(i).type.split('/')[0] === 'image') {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-image"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>';
					} else if ($_mailAttachment.files.item(i).type.split('/')[0] === 'application') {
						if ($_mailAttachment.files.item(i).type.split('/')[1] === 'zip') {
							getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-package"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"></line><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>';
						} else if ($_mailAttachment.files.item(i).type.split('/')[1]  === 'vnd.openxmlformats-officedocument.spreadsheetml.sheet' || $_mailAttachment.files.item(i).type.split('/')[1]  === 'vnd.openxmlformats-officedocument.wordprocessingml.document' ) {
							getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-file-text"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>';
						} else  {
							getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-folder"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>';
						}
					} else if ($_mailAttachment.files.item(i).type.split('/')[0] === 'video') {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-video"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>';
					} else {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-folder"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>';
					}

				  	$innerAttachmentHTML += '<div class="attachment file"> <div class="media"> '+ getSVG +' <div class="media-body"> <p class="file-name">'+ $_mailAttachment.files.item(i).name +'</p> <p class="file-size">'+ formatBytes($_mailAttachment.files.item(i).size, 2) +'</p> </div> </div> </div>';
				}
		  	}

            var outerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $outerAttachmentHTML + '</div>' : "";

            var innerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $innerAttachmentHTML + '</div>' : "";

            var attachmentIcon = $_mailAttachment.files.length >= 1 ? '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-paperclip attachment-indicator"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>' : "";

			var randomAlphaNumeric = randomString(10, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ');

			$html = '<div class="mail-item sentmail">' +
                        '<div class="animated animatedFadeInUp fadeInUp" id="sfdsf">' +
                            '<div class="mb-0">' +
                                '<div class="mail-item-heading collapsed"  data-toggle="collapse" role="navigation" data-target="#'+randomAlphaNumeric+'" aria-expanded="false">' +
                                    '<div class="mail-item-inner">' +

                                        '<div class="d-flex">' +
                                            '<div class="n-chk text-center">' +
                                                '<label class="new-control new-checkbox checkbox-primary">' +
                                                  '<input type="checkbox" class="new-control-input inbox-chkbox">' +
                                                  '<span class="new-control-indicator"></span>' +
                                                '</label>' +
                                            '</div>' +
                                            '<div class="f-body" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >' +
                                                '<div class="meta-mail-time">' +
                                                    '<p class="user-email" data-mailTo="'+$_mailTo+'">'+$_mailTo+'</p>' +
                                                '</div>' +
                                                '<div class="meta-title-tag">' +
                                                    '<p class="mail-content-excerpt" data-mailDescription="'+$_mailDescriptionText+'">'+attachmentIcon+'<span class="mail-title" data-mailTitle="'+$_mailSubject+'">'+$_mailSubject+' - </span>'+$_mailDescriptionText+'</p>' +
                                                    '<div class="tags">' +
                                                        '<span class="g-dot-primary"></span>' +
                                                        '<span class="g-dot-warning"></span>' +
                                                        '<span class="g-dot-success"></span>' +
                                                        '<span class="g-dot-danger"></span>' +
                                                    '</div>' +
                                                    '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>' +
                                                '</div>' +
                                            '</div>' +
                                        '</div>' +
                                    '</div>' +
                                    outerConditionHTML+
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';

			$html2 = '<div id="'+randomAlphaNumeric+'" class="collapse" aria-labelledby="'+randomAlphaNumeric+'" data-parent="#mailbox-inbox">'+
		                '<div class="mail-content-container sentmail" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >'+
		                    '<div class="d-flex justify-content-between mb-3">'+
		                    	'<div class="d-flex user-info">'+
	                                '<div class="f-body">'+
	                                    '<div class="meta-mail-time">'+
	                                        '<div class="">'+
                                                '<p class="user-email" data-mailto="'+$_mailTo+'"><span>To - </span>'+$_mailTo+'</p>, '+
                                                '<p class="user-cc-mail" data-mailcc="'+$_mailCC+'"><span>CC - </span>'+$_mailCC+'</p>'+
                                            '</div>'+
	                                        '<p class="mail-content-meta-date">'+today+' -</p>'+
	                                        '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>'+
	                                    '</div>'+
	                               '</div>'+
	                            '</div>'+
	                            '<div class="action-btns">'+
	                                '<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="" data-original-title="Reply">'+
	                                    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-corner-up-left reply"><polyline points="9 14 4 9 9 4"></polyline><path d="M20 20v-7a4 4 0 0 0-4-4H4"></path></svg>'+
	                                '</a>'+
	                                '<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="" data-original-title="Forward">'+
	                                    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-corner-up-right forward"><polyline points="15 14 20 9 15 4"></polyline><path d="M4 20v-7a4 4 0 0 1 4-4h12"></path></svg>'+
	                                '</a>'+
	                            '</div>'+
	                        '</div>'+

		                    "<p class='mail-content' data-mailTitle='"+$_mailSubject+"' data-mailDescription='"+$_textDelta+"'>"+$_mailDescriptionInnerHTML+"</p>"+

		                    '<p>Best Regards,</p>'+
		                    '<p>Info</p>'+
		                    innerConditionHTML +
		                '</div>'+
		            '</div>';

		    $("#ct").prepend($html);
		    $(".content-box > .msg-close").after($html2);
		    $('#composeMailModal').modal('hide');
		    $(".list-actions#sentmail").trigger('click');
		    swal({
		        title: 'Mail Sent Successfully',
		        type: 'success',
		        padding: '2em'
		    })
		    $_GET_mailItem_Reply();
			$_GET_mailItem_Forward();
			contentBoxPosition();
			stopPropagations();
			mailInboxScroll()
	        if (draftTragetID != "") {
	        	$('[data-target="'+draftTragetID+'"]').parents('.mail-item').remove();
	        	dynamicBadgeNotification('draftmail');
	        }
		});
	}

	/*
		Button Save ==> Trigger when clicked on Save Button in Modal.
	*/
	$("#btn-save").on('click', function(event) {
		event.preventDefault();
		/* Act on the event */

	  	var $_mailFrom = document.getElementById('m-form').value;
	  	var $_mailTo = document.getElementById('m-to').value;
	  	var $_mailCC = document.getElementById('m-cc').value;
	  	var $_mailAttachment = document.getElementById('mail_File_attachment');
	  	var $_mailSubject = document.getElementById('m-subject').value;
	  	var $_mailDescription = quill.getText();

	  	var delta = quill.getContents();
	  	var $_textDelta = JSON.stringify(delta);

	  	$outerAttachmentHTML = '';
	  	if ($_mailAttachment.files.length >= 1) {
			for (var i = 0; i < $_mailAttachment.files.length; ++i) {
			  $outerAttachmentHTML += '<span class="">'+ $_mailAttachment.files.item(i).name +'</span>'
			}
	  	}

        var outerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $outerAttachmentHTML + '</div>' : "";

		var randomAlphaNumeric = randomString(10, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ');

		$html = '<div class="mail-item draft">' +
                        '<div class="animated animatedFadeInUp fadeInUp" id="sfdsf">' +
                            '<div class="mb-0">' +
                                '<div class="mail-item-heading collapsed"  data-toggle="collapse" role="navigation" data-target="#'+randomAlphaNumeric+'" aria-expanded="false">' +
                                    '<div class="mail-item-inner">' +

                                        '<div class="d-flex">' +
                                            '<div class="n-chk text-center">' +
                                                '<label class="new-control new-checkbox checkbox-primary">' +
                                                  '<input type="checkbox" class="new-control-input inbox-chkbox">' +
                                                  '<span class="new-control-indicator"></span>' +
                                                '</label>' +
                                            '</div>' +
                                            '<div class="f-body" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >' +
                                                '<div class="meta-mail-time">' +
                                                    '<p class="user-email" data-mailTo="'+$_mailTo+'">'+$_mailTo+'</p>' +
                                                '</div>' +
                                                '<div class="meta-title-tag">' +
                                                    "<p class='mail-content-excerpt' data-mailDescription='"+$_textDelta+"'><span class='mail-title' data-mailTitle='"+$_mailSubject+"'>Draft: "+$_mailSubject+" - </span>"+$_mailDescription+"</p>" +
                                                    '<div class="tags">' +
                                                        '<span class="g-dot-primary"></span>' +
                                                        '<span class="g-dot-warning"></span>' +
                                                        '<span class="g-dot-success"></span>' +
                                                        '<span class="g-dot-danger"></span>' +
                                                    '</div>' +
                                                    '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>' +
                                                '</div>' +
                                            '</div>' +
                                        '</div>' +
                                    '</div>' +
                                    outerConditionHTML+
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';

	    $("#ct").prepend($html);
	    $('#composeMailModal').modal('hide');
	    $(".list-actions#draft").trigger('click');
	    swal({
	        title: 'Successfully Saved to Draft',
	        type: 'success',
	        padding: '2em'
	    })
	    $_GET_mailItem_Draft();
		contentBoxPosition();
		stopPropagations();
		dynamicBadgeNotification('draftmail');
	});

	/*
		Button Send Reply ==> Trigger when clicked on SEND Button in REPLY Modal.
	*/
	$("#btn-reply").on('click', function(event) {
		event.preventDefault();
		/* Act on the event */

	  	var $_mailFrom = document.getElementById('m-form').value;
	  	var $_mailTo = document.getElementById('m-to').value;
	  	var $_mailCC = document.getElementById('m-cc').value;
	  	var $_mailAttachment = document.getElementById('mail_File_attachment');
	  	var $_mailSubject = document.getElementById('m-subject').value;
	  	var $_mailDescriptionText = quill.getText();
	  	var $_mailDescriptionInnerHTML = quill.root.innerHTML;

	  	var delta = quill.getContents();
	  	var $_textDelta = JSON.stringify(delta);

	  	var $outerAttachmentHTML = '';
	  	var $innerAttachmentHTML = '';
	  	var getSVG = '';
	  	if ($_mailAttachment.files.length >= 1) {
			for (var i = 0; i < $_mailAttachment.files.length; ++i) {
			  	$outerAttachmentHTML += '<span class="">'+ $_mailAttachment.files.item(i).name +'</span>'

			  	// Dectecting the format/type of the uploaded file for appling the icon/svg accordingly 
				if ($_mailAttachment.files.item(i).type.split('/')[0] === 'image') {
					getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-image"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>';
				} else if ($_mailAttachment.files.item(i).type.split('/')[0] === 'application') {
					if ($_mailAttachment.files.item(i).type.split('/')[1] === 'zip') {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-package"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"></line><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>';
					} else if ($_mailAttachment.files.item(i).type.split('/')[1]  === 'vnd.openxmlformats-officedocument.spreadsheetml.sheet' || $_mailAttachment.files.item(i).type.split('/')[1]  === 'vnd.openxmlformats-officedocument.wordprocessingml.document' ) {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-file-text"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>';
					} else  {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-folder"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>';
					}
				} else if ($_mailAttachment.files.item(i).type.split('/')[0] === 'video') {
					getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-video"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>';
				} else {
					getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-folder"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>';
				}

			  	$innerAttachmentHTML += '<div class="attachment file"> <div class="media"> '+ getSVG +' <div class="media-body"> <p class="file-name">'+ $_mailAttachment.files.item(i).name +'</p> <p class="file-size">'+ formatBytes($_mailAttachment.files.item(i).size, 2) +'</p> </div> </div> </div>';
			}
	  	}

        var outerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $outerAttachmentHTML + '</div>' : "";

        var innerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $innerAttachmentHTML + '</div>' : "";

		var randomAlphaNumeric = randomString(10, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ');

		$html = '<div class="mail-item sentmail">' +
            '<div class="animated animatedFadeInUp fadeInUp" id="sfdsf">' +
                '<div class="mb-0">' +
                    '<div class="mail-item-heading collapsed"  data-toggle="collapse" role="navigation" data-target="#'+randomAlphaNumeric+'" aria-expanded="false">' +
                        '<div class="mail-item-inner">' +

                            '<div class="d-flex">' +
                                '<div class="n-chk text-center">' +
                                    '<label class="new-control new-checkbox checkbox-primary">' +
                                      '<input type="checkbox" class="new-control-input inbox-chkbox">' +
                                      '<span class="new-control-indicator"></span>' +
                                    '</label>' +
                                '</div>' +
                                '<div class="f-body" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >' +
                                    '<div class="meta-mail-time">' +
                                        '<p class="user-email" data-mailTo="'+$_mailTo+'">'+$_mailTo+'</p>' +
                                    '</div>' +
                                    '<div class="meta-title-tag">' +
                                        '<p class="mail-content-excerpt" data-mailDescription="'+$_mailDescriptionText+'"><span class="mail-title" data-mailTitle="'+$_mailSubject+'">'+$_mailSubject+' - </span>'+$_mailDescriptionText+'</p>' +
                                        '<div class="tags">' +
                                            '<span class="g-dot-primary"></span>' +
                                            '<span class="g-dot-warning"></span>' +
                                            '<span class="g-dot-success"></span>' +
                                            '<span class="g-dot-danger"></span>' +
                                        '</div>' +
                                        '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>' +
                                    '</div>' +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                        outerConditionHTML+
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>';

		$html2 = '<div id="'+randomAlphaNumeric+'" class="collapse" aria-labelledby="sdfsdaf" data-parent="#mailbox-inbox">'+
	                '<div class="mail-content-container sentmail" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >'+

	                    '<div class="d-flex justify-content-between mb-5">'+
		                    '<div class="d-flex user-info">'+
                                '<div class="f-body">'+
                                    '<div class="meta-mail-time">'+
                                    '<div class="">'+
                                            '<p class="user-email" data-mailto="'+$_mailTo+'"><span>To - </span>'+$_mailTo+'</p>, '+
                                            '<p class="user-cc-mail" data-mailcc="'+$_mailCC+'"><span>CC - </span>'+$_mailCC+'</p>'+
                                        '</div>'+
                                        '<p class="mail-content-meta-date">'+today+' -</p>'+
                                        '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>'+
                                    '</div>'+
                               '</div>'+
                            '</div>'+
                            '<div class="action-btns">'+
                                '<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="" data-original-title="Reply">'+
                                    '<i class="flaticon-reply reply"></i>'+
                                '</a>'+
                                '<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="" data-original-title="Forward">'+
                                    '<i class="flaticon-forward-arrow forward"></i>'+
                                '</a>'+
                            '</div>'+
                        '</div>'+

	                    "<p class='mail-content' data-mailTitle='"+$_mailSubject+"' data-mailDescription='"+$_textDelta+"'>"+$_mailDescriptionInnerHTML+"</p>"+

	                    '<p>Best Regards,</p>'+
	                    '<p>Info</p>'+
		                innerConditionHTML +
	                '</div>'+
	            '</div>';

	    $("#ct").prepend($html);
	    $(".content-box > .msg-close").after($html2);
	    $('#composeMailModal').modal('hide');
	    $(".list-actions#sentmail").trigger('click');
	    swal({
	        title: 'Mail Sent Successfully',
	        type: 'success',
	        padding: '2em'
	    })
	    $_GET_mailItem_Reply();
		$_GET_mailItem_Forward();
		contentBoxPosition();
		stopPropagations();
		mailInboxScroll();
	});

	/*
		Btn Reply Save ==> Trigger when clicked on SAVE Button in REPLY Modal.
	*/
	$("#btn-reply-save").on('click', function(event) {
		event.preventDefault();
		/* Act on the event */

	  	var $_mailFrom = document.getElementById('m-form').value;
	  	var $_mailTo = document.getElementById('m-to').value;
	  	var $_mailCC = document.getElementById('m-cc').value;
	  	var $_mailAttachment = document.getElementById('mail_File_attachment');
	  	var $_mailSubject = document.getElementById('m-subject').value;
	  	var $_mailDescription = quill.getText();

	  	var delta = quill.getContents();
	  	var $_textDelta = JSON.stringify(delta);

	  	$outerAttachmentHTML = '';
	  	if ($_mailAttachment.files.length >= 1) {
			for (var i = 0; i < $_mailAttachment.files.length; ++i) {
			  $outerAttachmentHTML += '<span class="">'+ $_mailAttachment.files.item(i).name +'</span>'
			}
	  	}

        var outerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $outerAttachmentHTML + '</div>' : "";

		var randomAlphaNumeric = randomString(10, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ');

		$html = '<div class="mail-item draft">' +
                        '<div class="animated animatedFadeInUp fadeInUp" id="sfdsf">' +
                            '<div class="mb-0">' +
                                '<div class="mail-item-heading collapsed"  data-toggle="collapse" role="navigation" data-target="#'+randomAlphaNumeric+'" aria-expanded="false">' +
                                    '<div class="mail-item-inner">' +

                                        '<div class="d-flex">' +
                                            '<div class="n-chk text-center">' +
                                                '<label class="new-control new-checkbox checkbox-primary">' +
                                                  '<input type="checkbox" class="new-control-input inbox-chkbox">' +
                                                  '<span class="new-control-indicator"></span>' +
                                                '</label>' +
                                            '</div>' +
                                            '<div class="f-body" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >' +
                                                '<div class="meta-mail-time">' +
                                                    '<p class="user-email" data-mailTo="'+$_mailTo+'">'+$_mailTo+'</p>' +
                                                '</div>' +
                                                '<div class="meta-title-tag">' +
                                                    "<p class='mail-content-excerpt' data-mailDescription='"+$_textDelta+"'><span class='mail-title' data-mailTitle='"+$_mailSubject+"'>Draft: "+$_mailSubject+" - </span>"+$_mailDescription+"</p>" +
                                                    '<div class="tags">' +
                                                        '<span class="g-dot-primary"></span>' +
                                                        '<span class="g-dot-warning"></span>' +
                                                        '<span class="g-dot-success"></span>' +
                                                        '<span class="g-dot-danger"></span>' +
                                                    '</div>' +
                                                    '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>' +
                                                '</div>' +
                                            '</div>' +
                                        '</div>' +
                                    '</div>' +
                                    outerConditionHTML+
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';

	    $("#ct").prepend($html);
	    $('#composeMailModal').modal('hide');
	    $(".list-actions#draft").trigger('click');
	    swal({
	        title: 'Successfully Saved to Draft',
	        type: 'success',
	        padding: '2em'
	    })
	    $_GET_mailItem_Draft();
		contentBoxPosition();
		stopPropagations();
		dynamicBadgeNotification('draftmail');
	});

	/*
		Button Send FWD ==> Trigger when clicked on SEND Button in FWD Modal.
	*/
	$("#btn-fwd").on('click', function(event) {
		event.preventDefault();
		/* Act on the event */
	  	var $_mailFrom = document.getElementById('m-form').value;
	  	var $_mailTo = document.getElementById('m-to').value;
	  	var $_mailCC = document.getElementById('m-cc').value;
	  	var $_mailAttachment = document.getElementById('mail_File_attachment');
	  	var $_mailSubject = document.getElementById('m-subject').value;
	  	var $_mailDescriptionText = quill.getText();
	  	var $_mailDescriptionInnerHTML = quill.root.innerHTML;
	  	var delta = quill.getContents();
	  	var $_textDelta = JSON.stringify(delta);

	  	var $outerAttachmentHTML = '';
	  	var $innerAttachmentHTML = '';
	  	var getSVG = '';
	  	if ($_mailAttachment.files.length >= 1) {
			for (var i = 0; i < $_mailAttachment.files.length; ++i) {
			  	$outerAttachmentHTML += '<span class="">'+ $_mailAttachment.files.item(i).name +'</span>'

			  	// Dectecting the format/type of the uploaded file for appling the icon/svg accordingly 
				if ($_mailAttachment.files.item(i).type.split('/')[0] === 'image') {
					getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-image"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>';
				} else if ($_mailAttachment.files.item(i).type.split('/')[0] === 'application') {
					if ($_mailAttachment.files.item(i).type.split('/')[1] === 'zip') {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-package"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"></line><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>';
					} else if ($_mailAttachment.files.item(i).type.split('/')[1]  === 'vnd.openxmlformats-officedocument.spreadsheetml.sheet' || $_mailAttachment.files.item(i).type.split('/')[1]  === 'vnd.openxmlformats-officedocument.wordprocessingml.document' ) {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-file-text"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>';
					} else  {
						getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-folder"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>';
					}
				} else if ($_mailAttachment.files.item(i).type.split('/')[0] === 'video') {
					getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-video"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>';
				} else {
					getSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-folder"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>';
				}

			  	$innerAttachmentHTML += '<div class="attachment file"> <div class="media"> '+ getSVG +' <div class="media-body"> <p class="file-name">'+ $_mailAttachment.files.item(i).name +'</p> <p class="file-size">'+ formatBytes($_mailAttachment.files.item(i).size, 2) +'</p> </div> </div> </div>';
			}
	  	}

        var outerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $outerAttachmentHTML + '</div>' : "";

        var innerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $innerAttachmentHTML + '</div>' : "";

		var randomAlphaNumeric = randomString(10, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ');

		$html = '<div class="mail-item sentmail">' +
                        '<div class="animated animatedFadeInUp fadeInUp" id="sfdsf">' +
                            '<div class="mb-0">' +
                                '<div class="mail-item-heading collapsed"  data-toggle="collapse" role="navigation" data-target="#'+randomAlphaNumeric+'" aria-expanded="false">' +
                                    '<div class="mail-item-inner">' +

                                        '<div class="d-flex">' +
                                            '<div class="n-chk text-center">' +
                                                '<label class="new-control new-checkbox checkbox-primary">' +
                                                  '<input type="checkbox" class="new-control-input inbox-chkbox">' +
                                                  '<span class="new-control-indicator"></span>' +
                                                '</label>' +
                                            '</div>' +
                                            '<div class="f-body" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >' +
                                                '<div class="meta-mail-time">' +
                                                    '<p class="user-email" data-mailTo="'+$_mailTo+'">'+$_mailTo+'</p>' +
                                                '</div>' +
                                                '<div class="meta-title-tag">' +
                                                    '<p class="mail-content-excerpt" data-mailDescription="'+$_mailDescriptionText+'"><span class="mail-title" data-mailTitle="'+$_mailSubject+'">'+$_mailSubject+' - </span>'+$_mailDescriptionText+'</p>' +
                                                    '<div class="tags">' +
                                                        '<span class="g-dot-primary"></span>' +
                                                        '<span class="g-dot-warning"></span>' +
                                                        '<span class="g-dot-success"></span>' +
                                                        '<span class="g-dot-danger"></span>' +
                                                    '</div>' +
                                                    '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>' +
                                                '</div>' +
                                            '</div>' +
                                        '</div>' +
                                    '</div>' +
                                    outerConditionHTML+
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';

		$html2 = '<div id="'+randomAlphaNumeric+'" class="collapse" aria-labelledby="sdfsdaf" data-parent="#mailbox-inbox">'+
	                '<div class="mail-content-container sentmail" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >'+

	                    '<div class="d-flex justify-content-between mb-5">'+

	                    	'<div class="d-flex user-info">'+
                                '<div class="f-body">'+
                                    '<div class="meta-mail-time">'+
                                    	'<div class="">'+
                                            '<p class="user-email" data-mailto="'+$_mailTo+'"><span>To - </span>'+$_mailTo+'</p>, '+
                                            '<p class="user-cc-mail" data-mailcc="'+$_mailCC+'"><span>CC - </span>'+$_mailCC+'</p>'+
                                        '</div>'+
                                        '<p class="mail-content-meta-date">'+today+' -</p>'+
                                        '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>'+
                                    '</div>'+
                               '</div>'+
                            '</div>'+

                            '<div class="action-btns">'+
                                '<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="" data-original-title="Reply">'+
                                    '<i class="flaticon-reply reply"></i>'+
                                '</a>'+
                                '<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="" data-original-title="Forward">'+
                                    '<i class="flaticon-forward-arrow forward"></i>'+
                                '</a>'+
                            '</div>'+
                        '</div>'+

	                    "<p class='mail-content' data-mailTitle='"+$_mailSubject+"' data-mailDescription='"+$_textDelta+"'>"+$_mailDescriptionInnerHTML+"</p>"+

	                    '<p>Best Regards,</p>'+
	                    '<p>Info</p>'+
	                    innerConditionHTML+
	                '</div>'+
	            '</div>';

	    $("#ct").prepend($html);
	    $(".content-box > .msg-close").after($html2);
	    $('#composeMailModal').modal('hide');
	    $(".list-actions#sentmail").trigger('click');
	    swal({
	        title: 'Mail Sent Successfully',
	        type: 'success',
	        padding: '2em'
	    })
	    $_GET_mailItem_Reply();
		$_GET_mailItem_Forward();
		contentBoxPosition();
		stopPropagations();
		mailInboxScroll();
	});

	/*
		Btn Fwd Save ==> Trigger when clicked on SAVE Button in FWD Modal.
	*/
	$("#btn-fwd-save").on('click', function(event) {
			event.preventDefault();
			/* Act on the event */
		  	var $_mailFrom = document.getElementById('m-form').value;
		  	var $_mailTo = document.getElementById('m-to').value;
		  	var $_mailCC = document.getElementById('m-cc').value;
		  	var $_mailAttachment = document.getElementById('mail_File_attachment');
		  	var $_mailSubject = document.getElementById('m-subject').value;
		  	var $_mailDescription = quill.getText();
		  	var delta = quill.getContents();
		  	var $_textDelta = JSON.stringify(delta);

		  	$outerAttachmentHTML = '';
		  	if ($_mailAttachment.files.length >= 1) {
				for (var i = 0; i < $_mailAttachment.files.length; ++i) {
				  $outerAttachmentHTML += '<span class="">'+ $_mailAttachment.files.item(i).name +'</span>'
				}
		  	}

	        var outerConditionHTML = $_mailAttachment.files.length >= 1 ? '<div class="attachments">' + $outerAttachmentHTML + '</div>' : "";

			var randomAlphaNumeric = randomString(10, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ');

			$html = '<div class="mail-item draft">' +
                        '<div class="animated animatedFadeInUp fadeInUp" id="sfdsf">' +
                            '<div class="mb-0">' +
                                '<div class="mail-item-heading collapsed"  data-toggle="collapse" role="navigation" data-target="#'+randomAlphaNumeric+'" aria-expanded="false">' +
                                    '<div class="mail-item-inner">' +

                                        '<div class="d-flex">' +
                                            '<div class="n-chk text-center">' +
                                                '<label class="new-control new-checkbox checkbox-primary">' +
                                                  '<input type="checkbox" class="new-control-input inbox-chkbox">' +
                                                  '<span class="new-control-indicator"></span>' +
                                                '</label>' +
                                            '</div>' +
                                            '<div class="f-body" data-mailFrom="'+$_mailFrom+'" data-mailTo="'+$_mailTo+'" data-mailCC="'+$_mailCC+'" >' +
                                                '<div class="meta-mail-time">' +
                                                    '<p class="user-email" data-mailTo="'+$_mailTo+'">'+$_mailTo+'</p>' +
                                                '</div>' +
                                                '<div class="meta-title-tag">' +
                                                    "<p class='mail-content-excerpt' data-mailDescription='"+$_textDelta+"'><span class='mail-title' data-mailTitle='"+$_mailSubject+"'>Draft: "+$_mailSubject+" - </span>"+$_mailDescription+"</p>" +
                                                    '<div class="tags">' +
                                                        '<span class="g-dot-primary"></span>' +
                                                        '<span class="g-dot-warning"></span>' +
                                                        '<span class="g-dot-success"></span>' +
                                                        '<span class="g-dot-danger"></span>' +
                                                    '</div>' +
                                                    '<p class="meta-time align-self-center">'+formatAMPM(new Date)+'</p>' +
                                                '</div>' +
                                            '</div>' +
                                        '</div>' +
                                    '</div>' +
                                    outerConditionHTML+
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';

		    $("#ct").prepend($html);
		    $('#composeMailModal').modal('hide');
		    $(".list-actions#draft").trigger('click');
		    swal({
		        title: 'Successfully Saved to Draft',
		        type: 'success',
		        padding: '2em'
		    })
		    $_GET_mailItem_Draft();
			contentBoxPosition();
			stopPropagations();
			dynamicBadgeNotification('draftmail');
	});
	

	/*
		fn. $_GET_mailItem_Draft ==> Trigger when clicked on Draft Button in Modal.
	*/
	function $_GET_mailItem_Draft() {
		$(".mail-item.draft").off('click').on('click', function(event) {

		    $('#btn-send').show();
			$('#btn-reply').hide();
			$('#btn-fwd').hide();
			// Save And Reply Save
			$('#btn-save').show();
			$('#btn-reply-save').hide();
			$('#btn-fwd-save').hide();
			
		    var $_mailFrom =  $(this).find('.f-body').attr('data-mailFrom');
		    var $_mailTo =  $(this).find('.f-body').attr('data-mailTo');
		    var $_mailCC =  $(this).find('.f-body').attr('data-mailCC');
		    var $_mailSubject =  $(this).find('.mail-title').attr('data-mailtitle');
		    var $_mailDataTarget =  $(this).find('.mail-item-heading').attr('data-target');
		    $_sendMail($_mailDataTarget);
		    var $_mailDescription =  JSON.parse($(this).find('.mail-content-excerpt').attr('data-maildescription'));

		    $('#m-form').val($_mailFrom);
		    $('#m-to').val($_mailTo);
		    $('#m-cc').val($_mailCC);
		    $('#m-subject').val($_mailSubject);
		    quill.setContents($_mailDescription);
		    $('#composeMailModal').modal('show');
		})
	}

	/*
		fn. $_GET_mailItem_Reply ==> Trigger when clicked on Reply Button inside Mail Content.
	*/
	function $_GET_mailItem_Reply() {
		$(".reply").on('click', function(event) {

			// Send And Reply
			$('#btn-reply').show();
			$('#btn-send').hide();
			$('#btn-fwd').hide();

			// Save And Reply Save
			$('#btn-reply-save').show();
			$('#btn-fwd-save').hide();
			$('#btn-save').hide();		

			var $_mailFrom =  $(this).parents('.mail-content-container').attr('data-mailFrom');
		    var $_mailTo =  $(this).parents('.mail-content-container').attr('data-mailTo');
		    var $_mailCC =  $(this).parents('.mail-content-container').attr('data-mailCC');
			var $_mailSubject = $(this).parents('.mail-content-container').find('.mail-content').attr('data-mailtitle');
		    var $_mailDescription =  JSON.parse($(this).parents('.mail-content-container').find('.mail-content').attr('data-maildescription'));

		    $('#m-form').val($_mailFrom);
		    $('#m-to').val($_mailTo);
		    $('#m-cc').val($_mailCC);
		    $('#m-subject').val('Re: ' + $_mailSubject);
			quill.setContents($_mailDescription);
			$('#composeMailModal').modal('show');
		})
	}

	/*
		fn. $_GET_mailItem_Forward ==> Trigger when clicked on Forward Button inside Mail Content.
	*/
	function $_GET_mailItem_Forward() {
		$(".forward").on('click', function(event) {

			$('#btn-fwd').show();
			$('#btn-reply').hide();
			$('#btn-send').hide();

			$('#btn-fwd-save').show();
			$('#btn-reply-save').hide();
			$('#btn-save').hide();

			var $_mailFrom =  $(this).parents('.mail-content-container').attr('data-mailFrom');
		    var $_mailTo =  $(this).parents('.mail-content-container').attr('data-mailTo');
		    var $_mailCC =  $(this).parents('.mail-content-container').attr('data-mailCC');
			var $_mailSubject = $(this).parents('.mail-content-container').find('.mail-content').attr('data-mailtitle');
		    var $_mailDescription =  JSON.parse($(this).parents('.mail-content-container').find('.mail-content').attr('data-maildescription'));

		    $('#m-form').val($_mailFrom);
		    $('#m-to').val($_mailTo);
		    $('#m-cc').val($_mailCC);
		    $('#m-subject').val('Fwd: ' + $_mailSubject);
			quill.setContents($_mailDescription);
			$('#composeMailModal').modal('show');
		})
	}

	$_sendMail();
	$_GET_mailItem_Draft();
	$_GET_mailItem_Reply();
	$_GET_mailItem_Forward();
	contentBoxPosition();
	stopPropagations();

	$('.tab-title .nav-pills a.nav-link').on('click', function(event) {
	  $(this).parents('.mail-box-container').find('.tab-title').removeClass('mail-menu-show')
	  $(this).parents('.mail-box-container').find('.mail-overlay').removeClass('mail-overlay-show')
	})
	
});