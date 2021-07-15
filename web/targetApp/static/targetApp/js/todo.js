$('.input-search').on('keyup', function() {
  var rex = new RegExp($(this).val(), 'i');
  $('.todo-box .todo-item').hide();
  $('.todo-box .todo-item').filter(function() {
    return rex.test($(this).text());
  }).show();
});

const taskViewScroll = new PerfectScrollbar('.task-text', {
  wheelSpeed:.5,
  swipeEasing:!0,
  minScrollbarLength:40,
  maxScrollbarLength:300,
  suppressScrollX : true
});
function dynamicBadgeNotification( setTodoCategoryCount ) {
  var todoCategoryCount = setTodoCategoryCount;

  // Get Parents Div(s)
  var get_ParentsDiv = $('.todo-item');
  var get_TodoAllListParentsDiv = $('.todo-item.all-list');
  var get_TodoCompletedListParentsDiv = $('.todo-item.todo-task-done');
  var get_TodoImportantListParentsDiv = $('.todo-item.todo-task-important');

  // Get Parents Div(s) Counts
  var get_TodoListElementsCount = get_TodoAllListParentsDiv.length;
  var get_CompletedTaskElementsCount = get_TodoCompletedListParentsDiv.length;
  var get_ImportantTaskElementsCount = get_TodoImportantListParentsDiv.length;

  // Get Badge Div(s)
  var getBadgeTodoAllListDiv = $('#all-list .todo-badge');
  var getBadgeCompletedTaskListDiv = $('#todo-task-done .todo-badge');
  var getBadgeImportantTaskListDiv = $('#todo-task-important .todo-badge');


  if (todoCategoryCount === 'allList') {
    if (get_TodoListElementsCount === 0) {
      getBadgeTodoAllListDiv.text('');
      return;
    }
    if (get_TodoListElementsCount > 9) {
      getBadgeTodoAllListDiv.css({
        padding: '2px 0px',
        height: '25px',
        width: '25px'
      });
    } else if (get_TodoListElementsCount <= 9) {
      getBadgeTodoAllListDiv.removeAttr('style');
    }
    getBadgeTodoAllListDiv.text(get_TodoListElementsCount);
  }
  else if (todoCategoryCount === 'completedList') {
    if (get_CompletedTaskElementsCount === 0) {
      getBadgeCompletedTaskListDiv.text('');
      return;
    }
    if (get_CompletedTaskElementsCount > 9) {
      getBadgeCompletedTaskListDiv.css({
        padding: '2px 0px',
        height: '25px',
        width: '25px'
      });
    } else if (get_CompletedTaskElementsCount <= 9) {
      getBadgeCompletedTaskListDiv.removeAttr('style');
    }
    getBadgeCompletedTaskListDiv.text(get_CompletedTaskElementsCount);
  }
  else if (todoCategoryCount === 'importantList') {
    if (get_ImportantTaskElementsCount === 0) {
      getBadgeImportantTaskListDiv.text('');
      return;
    }
    if (get_ImportantTaskElementsCount > 9) {
      getBadgeImportantTaskListDiv.css({
        padding: '2px 0px',
        height: '25px',
        width: '25px'
      });
    } else if (get_ImportantTaskElementsCount <= 9) {
      getBadgeImportantTaskListDiv.removeAttr('style');
    }
    getBadgeImportantTaskListDiv.text(get_ImportantTaskElementsCount);
  }
}

new dynamicBadgeNotification('allList');
new dynamicBadgeNotification('completedList');
new dynamicBadgeNotification('importantList');

$('.mail-menu').on('click', function(event) {
  $('.tab-title').addClass('mail-menu-show');
  $('.mail-overlay').addClass('mail-overlay-show');
})
$('.mail-overlay').on('click', function(event) {
  $('.tab-title').removeClass('mail-menu-show');
  $('.mail-overlay').removeClass('mail-overlay-show');
})
$('#addTask').on('click', function(event) {
  event.preventDefault();

  $('#task').val('');
  $('#taskdescription').val('');

  $('.add-tsk').show();
  $('.edit-tsk').hide();
  $('#addTaskModal').modal('show');
  const ps = new PerfectScrollbar('.todo-box-scroll', {
    suppressScrollX : true
  });
});
const ps = new PerfectScrollbar('.todo-box-scroll', {
  suppressScrollX : true
});

const todoListScroll = new PerfectScrollbar('.todoList-sidebar-scroll', {
  suppressScrollX : true
});

function checkCheckbox() {
  $('.todo-item input[type="checkbox"]').click(function() {
    if ($(this).is(":checked")) {
      $(this).parents('.todo-item').addClass('todo-task-done');
    }
    else if ($(this).is(":not(:checked)")) {
      $(this).parents('.todo-item').removeClass('todo-task-done');
    }
    new dynamicBadgeNotification('completedList');
  });
}

function importantDropdown() {
  $('.important').click(function() {
    if(!$(this).parents('.todo-item').hasClass('todo-task-important')){
      $(this).parents('.todo-item').addClass('todo-task-important');
      $(this).html('Back to List');
    }
    else if($(this).parents('.todo-item').hasClass('todo-task-important')){
      $(this).parents('.todo-item').removeClass('todo-task-important');
      $(this).html('Important');
      $(".list-actions#all-list").trigger('click');
    }
    new dynamicBadgeNotification('importantList');
  });
}

function priorityDropdown() {
  $('.priority-dropdown .dropdown-menu .dropdown-item').on('click', function(event) {

    var getClass = $(this).attr('class').split(' ')[1];
    var getDropdownClass = $(this).parents('.p-dropdown').children('.dropdown-toggle').attr('class').split(' ')[1];
    $(this).parents('.p-dropdown').children('.dropdown-toggle').removeClass(getDropdownClass);

    $(this).parents('.p-dropdown').children('.dropdown-toggle').addClass(getClass);
  })
}

function editDropdown() {
  $('.action-dropdown .dropdown-menu .edit.dropdown-item').click(function() {

    event.preventDefault();

    var $_outerThis = $(this);

    $('.add-tsk').hide();
    $('.edit-tsk').show();

    var $_taskTitle = $_outerThis.parents('.todo-item').children().find('.todo-heading').text();
    var $_taskText = $_outerThis.parents('.todo-item').children().find('.todo-text').text();

    $('#task').val($_taskTitle);
    $('#taskdescription').val($_taskText);

    $('.edit-tsk').off('click').on('click', function(event) {
      var $_innerThis = $(this);
      var $_task = document.getElementById('task').value;
      var $_taskDescription = document.getElementById('taskdescription').value;
      var $_taskDescriptionText = document.getElementById('taskdescription').value;
      var $_taskEditedTitle = $_outerThis.parents('.todo-item').children().find('.todo-heading').html($_task);
      var $_taskEditedText = $_outerThis.parents('.todo-item').children().find('.todo-text').html($_taskDescriptionText);
      $('#addTaskModal').modal('hide');
    })
    $('#addTaskModal').modal('show');
  })
}

function todoItem() {
  $('.todo-item .todo-content').on('click', function(event) {
    event.preventDefault();

    var $_taskTitle = $(this).find('.todo-heading').text();
    var $todoDescription = $(this).find('.todo-text').text();

    $('.task-heading').text($_taskTitle);
    $('.task-text').html($todoDescription);

    $('#todoShowListItem').modal('show');
  });
}
var $btns = $('.list-actions').click(function() {
  if (this.id == 'all-list') {
    var $el = $('.' + this.id).fadeIn();
    $('#ct > div').not($el).hide();
  } else {
    var $el = $('.' + this.id).fadeIn();
    $('#ct > div').not($el).hide();
  }
  $btns.removeClass('active');
  $(this).addClass('active');
})

checkCheckbox();
importantDropdown();
priorityDropdown();
editDropdown();
todoItem();

$(".add-tsk").click(function(){

  var $_task = document.getElementById('task').value;

  var $_taskDescriptionText = document.getElementById('taskdescription').value;

  $html = '<div class="todo-item all-list">'+
  '<div class="todo-item-inner">'+
  '<div class="n-chk text-center">'+
  '<label class="new-control new-checkbox checkbox-primary">'+
  '<input type="checkbox" class="new-control-input inbox-chkbox">'+
  '<span class="new-control-indicator"></span>'+
  '</label>'+
  '</div>'+

  '<div class="todo-content">'+
  '<h5 class="todo-heading">'+$_task+'</h5>'+
  "<p class='todo-text' >"+$_taskDescriptionText+"</p>"+
  '</div>'+

  '<div class="action-dropdown">'+
  '<div class="dropdown">'+
  '<a class="dropdown-toggle" href="#" role="button" id="dropdownMenuLink-4" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">'+
  '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-more-vertical"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>'+
  '</a>'+

  '<div class="dropdown-menu" aria-labelledby="dropdownMenuLink-4">'+
  '<a class="dropdown-item edit" href="javascript:void(0);">Edit</a>'+
  '<a class="important dropdown-item" href="javascript:void(0);">Important</a>'+
  '<a class="dropdown-item delete" href="javascript:void(0);">Delete</a>'+
  '<a class="dropdown-item permanent-delete" href="javascript:void(0);">Permanent Delete</a>'+
  '<a class="dropdown-item revive" href="javascript:void(0);">Revive Task</a>'+
  '</div>'+
  '</div>'+
  '</div>'+

  '</div>'+
  '</div>';


  $("#ct").prepend($html);
  $('#addTaskModal').modal('hide');
  checkCheckbox();
  editDropdown();
  priorityDropdown();
  todoItem();
  importantDropdown();
  new dynamicBadgeNotification('allList');
  $(".list-actions#all-list").trigger('click');
});

$('.tab-title .nav-pills a.nav-link').on('click', function(event) {
  $(this).parents('.mail-box-container').find('.tab-title').removeClass('mail-menu-show')
  $(this).parents('.mail-box-container').find('.mail-overlay').removeClass('mail-overlay-show')
})
