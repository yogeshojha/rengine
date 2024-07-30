
function populateTodofunction(project=null){
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

    populateScanHistory(project=project);

  });
  const ps = new PerfectScrollbar('.todo-box-scroll', {
    suppressScrollX : true
  });

  const todoListScroll = new PerfectScrollbar('.todoList-sidebar-scroll', {
    suppressScrollX : true
  });

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
  todoItem();
  deleteDropdown();

  $(".add-tsk").click(function(){

    var $_task = document.getElementById('task').value;

    var $_taskDescriptionText = document.getElementById('taskdescription').value;

    var $_taskScanHistory = $("#scanHistoryIDropdown option:selected").text();

    var $_taskSubdomain = $("#subdomainDropdown option:selected").text();

    var $_targetText = '';

    if ($_taskScanHistory != 'Choose Scan History...') {
      $_targetText = $_taskScanHistory;
    }

    if ($_taskSubdomain != 'Choose Subdomain...') {
      $_targetText += ' Subdomain : ' + $_taskSubdomain;
    }

    $html = '<div class="todo-item all-list">'+
    '<div class="todo-item-inner">'+
    '<div class="n-chk text-center">'+
    '<label class="new-control new-checkbox checkbox-primary">'+
    '<input type="checkbox" class="form-check-input inbox-chkbox">'+
    '<span class="new-control-indicator"></span>'+
    '</label>'+
    '</div>'+

    '<div class="todo-content">'+
    '<h5 class="todo-heading">'+htmlEncode($_task)+'</h5>'+
    '<p class="target">'+$_targetText+'</h5>'+
    "<p class='todo-text' >"+htmlEncode($_taskDescriptionText)+"</p>"+
    '</div>'+

    '<div class="action-dropdown custom-dropdown-icon">'+
    '<div class="dropdown dropstart">'+
    '<a class="dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">'+
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-more-vertical"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>'+
    '</a>'+

    '<div class="dropdown-menu">'+
    '<a class="important dropdown-item" href="javascript:void(0);">Toggle Important</a>'+
    '<a class="dropdown-item delete" href="javascript:void(0);">Delete</a>'+
    '</div>'+
    '</div>'+
    '</div>'+

    '</div>'+
    '</div>';


    $("#ct").prepend($html);
    $('#addTaskModal').modal('hide');
    checkCheckbox();
    todoItem();
    importantDropdown();
    deleteDropdown();
    new dynamicBadgeNotification('allList');
    $(".list-actions#all-list").trigger('click');

    data = {
      'title': $_task,
      'description': $_taskDescriptionText
    }

    // if ($("#scanHistoryIDropdown").val() && $("#scanHistoryIDropdown").val() != 'Choose Scan History...') {
    //   data['scan_history'] = parseInt($("#scanHistoryIDropdown").val());
    // }

    if ($("#subdomainDropdown").val() != 'Choose Subdomain...') {
      data['subdomain_id'] = parseInt($("#subdomainDropdown").val());
    }

    if (project) {
      data['project'] = project;
    }

    console.log(data);

    fetch('/api/add/recon_note/', {
      method: 'post',
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    }).then(res => res.json())
    .then(res => console.log(res));
  });

  $('.tab-title .nav-pills a.nav-link').on('click', function(event) {
    $(this).parents('.mail-box-container').find('.tab-title').removeClass('mail-menu-show')
    $(this).parents('.mail-box-container').find('.mail-overlay').removeClass('mail-overlay-show')
  })

}

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

function deleteDropdown() {
  $('.action-dropdown .dropdown-menu .delete.dropdown-item').click(function() {
    var id = this.id.split('_')[1];
    var main_this = this;
    swal.queue([{
      title: 'Are you sure you want to delete this Recon Note?',
      text: "You won't be able to revert this!",
      type: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Delete',
      padding: '2em',
      showLoaderOnConfirm: true,
      preConfirm: function() {
        return fetch('../delete_note', {
          method: 'POST',
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": getCookie("csrftoken")
          },
          body: JSON.stringify({
            'id': parseInt(id),
          })
        })
        .then(function (response) {
          if(!$(main_this).parents('.todo-item').hasClass('todo-task-trash')) {
            var getTodoParent = $(main_this).parents('.todo-item');
            var getTodoClass = getTodoParent.attr('class');

            var getFirstClass = getTodoClass.split(' ')[1];
            var getSecondClass = getTodoClass.split(' ')[2];
            var getThirdClass = getTodoClass.split(' ')[3];

            if (getFirstClass === 'all-list') {
              getTodoParent.removeClass(getFirstClass);
            }
            if (getSecondClass === 'todo-task-done' || getSecondClass === 'todo-task-important') {
              getTodoParent.removeClass(getSecondClass);
            }
            if (getThirdClass === 'todo-task-done' || getThirdClass === 'todo-task-important') {
              getTodoParent.removeClass(getThirdClass);
            }
            $(main_this).parents('.todo-item').addClass('todo-task-trash');
          } else if($(main_this).parents('.todo-item').hasClass('todo-task-trash')) {
            $(main_this).parents('.todo-item').removeClass('todo-task-trash');
          }
          new dynamicBadgeNotification('allList');
          new dynamicBadgeNotification('completedList');
          new dynamicBadgeNotification('importantList');
        })
        .catch(function() {
          swal.insertQueueStep({
            type: 'error',
            title: 'Oops! Unable to delete todo!'
          })
        })
      }
    }]);
  });
}
function checkCheckbox() {
  $('.inbox-chkbox').click(function() {
    if ($(this).is(":checked")) {
      $(this).parents('.todo-item').addClass('todo-task-done');
    }
    else if ($(this).is(":not(:checked)")) {
      $(this).parents('.todo-item').removeClass('todo-task-done');
    }
    new dynamicBadgeNotification('completedList');
    fetch('../flip_todo_status', {
      method: 'post',
      headers: {
        "X-CSRFToken": getCookie("csrftoken")
      },
      body: JSON.stringify({
        'id': parseInt(this.id.split('_')[1]),
      })
    }).then(res => res.json())
    .then(res => console.log(res));
  });
}

function importantDropdown() {
  $('.important').click(function() {
    badge_id = this.id.split('_')[1];
    if(!$(this).parents('.todo-item').hasClass('todo-task-important')){
      $(this).parents('.todo-item').addClass('todo-task-important');

      var is_important_badge = document.createElement("div");
      is_important_badge.classList.add("priority-dropdown");
      is_important_badge.classList.add("custom-dropdown-icon");
      is_important_badge.id = 'important-badge-' + this.id.split('_')[1];

      badge = `
      <div class="dropdown p-dropdown">
      <span class="text-danger bs-tooltip" title="Important Task">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-alert-octagon"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12" y2="16"></line></svg>
      </span>
      </div>`

      is_important_badge.innerHTML = badge;

      $(this).parents('.todo-item').find('.todo-content').after(is_important_badge);
    }
    else if($(this).parents('.todo-item').hasClass('todo-task-important')){
      $(this).parents('.todo-item').removeClass('todo-task-important');
      $(".list-actions#all-list").trigger('click');
      $("#important-badge-"+badge_id).empty();
    }
    new dynamicBadgeNotification('importantList');
    fetch('../flip_important_status', {
      method: 'post',
      headers: {
        "X-CSRFToken": getCookie("csrftoken")
      },
      body: JSON.stringify({
        'id': parseInt(this.id.split('_')[1]),
      })
    }).then(res => res.json())
    .then(res => console.log(res));
  });
}

function todoItem() {
  $('.todo-item .todo-content').on('click', function(event) {
    event.preventDefault();

    var $_taskTitle = $(this).find('.todo-heading').text();

    var $_taskTarget = $(this).find('.target').text();

    var $todoDescription = $(this).find('.todo-text').text();

    $('.task-heading').text($_taskTitle);
    $('.task-text').html(`<span class="text-success">${$_taskTarget}</span><br>` + htmlEncode($todoDescription));

    $('#todoShowListItem').modal('show');
  });
}

function populateScanHistory(project) {
  scan_history_select = document.getElementById('scanHistoryIDropdown');
  $.getJSON(`/api/listScanHistory/?format=json&project=${project}`, function(data) {
    for (var history in data){
      history_object = data[history];
      var option = document.createElement('option');
      option.value = history_object['id'];
      option.innerHTML = history_object['domain']['name'] + ' - Scanned ' + moment.utc(history_object['start_scan_date']).fromNow();
      scan_history_select.appendChild(option);
    }
  });
}
