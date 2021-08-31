function todoCheckboxListener(){
  $('input[type="checkbox"]').click(function() {
    var note_id = parseInt(this.id.split('_')[1]);
    console.log(note_id);
    if ($(this).is(":checked")) {
      $("#todo_parent_"+note_id).addClass('text-strike');
    }
    else if ($(this).is(":not(:checked)")) {
      $("#todo_parent_"+note_id).removeClass('text-strike');
    }
    fetch('../../recon_note/flip_todo_status', {
      method: 'post',
      headers: {
        "X-CSRFToken": getCookie("csrftoken")
      },
      body: JSON.stringify({
        'id': note_id,
      })
    }).then(res => res.json())
    .then(res => console.log(res));
  });
}

function delete_todo(todo_id){
  scan_id = parseInt(document.getElementById('summary_identifier_val').value);
  swal.queue([{
    title: 'Are you sure you want to delete this Recon Todo?',
    text: "You won't be able to revert this!",
    type: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Delete',
    padding: '2em',
    showLoaderOnConfirm: true,
    preConfirm: function() {
      return fetch('../../recon_note/delete_note', {
        method: 'POST',
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({
          'id': parseInt(todo_id),
        })
      })
      .then(function (response) {
        Snackbar.show({
          text: 'Recon Todo Deleted.',
          pos: 'top-right',
          duration: 1500,
        });
        get_recon_notes(scan_id);
      })
      .catch(function() {
        swal.insertQueueStep({
          type: 'error',
          title: 'Oops! Unable to delete todo!'
        })
      })
    }
  }]);
}

function change_todo_priority(todo_id, imp_type){
  if (imp_type == 0) {
    snackbar_text = 'Todo Marked as Unimportant';
  }
  else if (imp_type == 1) {
    snackbar_text = 'Todo Marked as Important';
  }
  scan_id = parseInt(document.getElementById('summary_identifier_val').value);
  fetch('../../recon_note/flip_important_status', {
    method: 'post',
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      'id': todo_id,
    })
  }).then(function (response) {
    $(".tooltip").tooltip("hide");
    Snackbar.show({
      text: snackbar_text,
      pos: 'top-right',
      duration: 1500,
    });
    get_recon_notes(scan_id);
  });
}


function list_subdomain_todos(subdomain_id, subdomain_name){
  $('.modal-title').html(`Todos for subdomain ${subdomain_name}`);
  $('#exampleModal').modal('show');
  $('.modal-text').empty(); $('#modal-footer').empty();
  $('.modal-text').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  // query subdomains
  $.getJSON(`/api/listTodoNotes/?subdomain_id=${subdomain_id}&format=json`, function(data) {
    $('#modal-loader').empty();
    $('#modal-text-content').empty();
    $('#modal-text-content').append(`<ul id="todo-modal-content-ul"></ul>`);
    for (todo in data['notes']){
      todo_obj = data['notes'][todo];
      important_badge = '';
      if (todo_obj['is_important']) {
        important_badge = `<span class="text-danger bs-tooltip" title="Important Task">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-alert-octagon"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12" y2="16"></line></svg>
        </span>`;
      }
      is_done = '';
      if (todo_obj['is_done']) {
        is_done = 'text-strike'
      }

      $("#todo-modal-content-ul").append(`<li class="${is_done}">
      ${important_badge}<b>&nbsp;${htmlEncode(todo_obj['title'])}</b>
      <br />
      ${htmlEncode(todo_obj['description'])}

      </li>`);
    }
    $('.bs-tooltip').tooltip();
  }).fail(function(){
    $('#modal-loader').empty();
  });
}

function get_task_details(todo_id){
  $('#exampleModal').modal('show');
  $('.modal-text').empty(); $('#modal-footer').empty();
  $('.modal-text').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  $.getJSON(`/api/listTodoNotes/?todo_id=${todo_id}&format=json`, function(data) {
    $('.modal-text').empty(); $('#modal-footer').empty();
    note = data['notes'][0];
    subdomain_name = '';
    if (note['subdomain_name']) {
      subdomain_name = '<small class="text-success">Subdomain: ' + note['subdomain_name'] + '</small></br>';
    }
    $('.modal-title').html(`<b>${split(htmlEncode(note['title']), 80)}</b>`);
    $('#modal-text-content').append(`<p>${subdomain_name} ${htmlEncode(note['description'])}</p>`);
  });
}

function get_recon_notes(target_id, scan_id){
  if (target_id) {
    url = `/api/listTodoNotes/?target_id=${target_id}&format=json`;
  }
  else if (scan_id) {
    url = `/api/listTodoNotes/?scan_id=${scan_id}&format=json`
  }
  $.getJSON(url, function(data) {
    $('#tasks-count').empty();
    $('#recon-task-list').empty();
    if (data['notes'].length > 0){
      $('#recon-task-list').append(`<div id="todo_list_${target_id}"></div>`);
      for (var val in data['notes']){
        note = data['notes'][val];
        div_id = 'todo_' + note['id'];
        subdomain_name = '';
        if (note['subdomain_name']) {
          subdomain_name = '<small class="text-success">Subdomain: ' + note['subdomain_name'] + '</small></br>';
        }
        done_strike = '';
        checked = '';
        if (note['is_done']) {
          done_strike = 'text-strike';
          checked = 'checked';
        }
        important_badge = '';
        mark_important = ''
        if (note['is_important']) {
          important_badge = `<span class="text-danger bs-tooltip" title="" data-original-title="Important Task">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-alert-octagon"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12" y2="16"></line></svg>
          </span>`;
          mark_important = `<span class="text-dark float-right bs-tooltip" title="" data-original-title="Mark Unimportant" onclick="change_todo_priority(${note['id']}, 0)">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="feather feather-alert-octagon"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12" y2="16"></line></svg>
          </span>`;
        }
        else{
          mark_important = `<span class="text-warning float-right bs-tooltip" title="" data-original-title="Mark Important" onclick="change_todo_priority(${note['id']}, 1)">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-alert-octagon"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12" y2="16"></line></svg>
          </span>`;
        }
        $(`#todo_list_${target_id}`).append(`<div id="todo_parent_${note['id']}">
        <div class="badge-link custom-control custom-checkbox">
        <input type="checkbox" class="custom-control-input todo-item" ${checked} name="${div_id}" id="${div_id}">
        <label for="${div_id}" class="${done_strike} custom-control-label text-dark">${important_badge}<b>${truncate(htmlEncode(note['title']), 20)}</b>
        </label>
        <span class="float-right text-danger bs-tooltip" title="Delete Todo" onclick="delete_todo(${note['id']})">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="feather feather-trash-2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
        </span>
        ${mark_important}
        <p class="${done_strike}" onclick="get_task_details(${note['id']})">${subdomain_name} ${truncate(htmlEncode(note['description']), 100)}
        </p>
        </div>
        </div>
        <hr/>`);
      }
      $('#tasks-count').html(`<span class="badge outline-badge-dark">${data['notes'].length}</span>`);
    }
    else{
      $('#tasks-count').html(`<span class="badge outline-badge-dark">0</span>`);
      $('#recon-task-list').append(`<p>No todos or notes...</p>`);
    }
    $('.bs-tooltip').tooltip();
    todoCheckboxListener();
  });
}
