function todoCheckboxListener(){
  $('.detail-scan-todo-item').click(function() {
    var note_id = parseInt(this.id.split('_')[1]);
    console.log(note_id);
    if ($(this).is(":checked")) {
      $("#todo_parent_"+note_id).addClass('text-strike');
    }
    else if ($(this).is(":not(:checked)")) {
      $("#todo_parent_"+note_id).removeClass('text-strike');
    }
    fetch('../../../recon_note/flip_todo_status', {
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
      return fetch('../../../recon_note/delete_note', {
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
        get_recon_notes(null, scan_id);
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
  fetch('../../../recon_note/flip_important_status', {
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
    get_recon_notes(null, scan_id);
  });
}


function list_subdomain_todos(subdomain_id, subdomain_name){
  $('.modal-title').html(`Todos for subdomain ${subdomain_name}`);
  $('#modal_dialog').modal('show');
  $('#modal-content').empty();
   $('#modal-footer').empty();
  $('#modal-content').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  // query subdomains
  $.getJSON(`/api/listTodoNotes/?subdomain_id=${subdomain_id}&format=json`, function(data) {
    $('#modal-loader').empty();
    $('#modal-content').empty();
    $('#modal-content').append(`<ul id="todo-modal-content-ul"></ul>`);
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
  $('#modal_dialog').modal('show');
  $('.modal-text').empty(); $('#modal-footer').empty();
  $('.modal-text').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  $.getJSON(`/api/listTodoNotes/?todo_id=${todo_id}&format=json`, function(data) {
    $('.modal-text').empty(); $('#modal-footer').empty();
    note = data['notes'][0];
    subdomain_name = '';
    if (note['subdomain_name']) {
      subdomain_name = '<small class="text-success"> Subdomain: ' + note['subdomain_name'] + '</small></br>';
    }
    $('.modal-title').html(`<b>${htmlEncode(note['title'])}</b>`);
    $('#modal-content').append(`<p>${subdomain_name} ${htmlEncode(note['description'])}</p>`);
  });
}

function get_recon_notes(target_id, scan_id){
  var url = `/api/listTodoNotes/?`;

  if (target_id) {
    url += `target_id=${target_id}`;
  }
  else if (scan_id) {
    url += `scan_id=${scan_id}`;
  }

  url += `&format=json`;

  // <li class="list-group-item border-0 ps-0"><div class="form-check"><input type="checkbox" class="form-check-input todo-done" id="8"><label class="form-check-label" for="8">dd</label></div></li>
  $.getJSON(url, function(data) {
    $('#tasks-count').empty();
    $('#todo-list').empty();
    if (data['notes'].length > 0){
      $('#todo-list').append(`<li class="list-group-item border-0 ps-0" id="todo_list_${target_id}"></li>`);
      for (var val in data['notes']){
        note = data['notes'][val];
        div_id = 'todo_' + note['id'];
        subdomain_name = '';
        if (note['subdomain_name']) {
          subdomain_name = '<small class="text-success"> Subdomain: ' + note['subdomain_name'] + '</small></br>';
        }
        strike_tag = 'span';
        checked = '';
        if (note['is_done']) {
          strike_tag = 'del';
          checked = 'checked';
        }
        important_badge = '';
        mark_important = ''
        if (note['is_important']) {
          important_badge = `<i class="fe-alert-triangle text-danger me-1"></i>&nbsp;`;
          mark_important = `<a class="dropdown-item" onclick="change_todo_priority(${note['id']}, 0)">Mark UnImportant</a>`;
        }
        else{
          mark_important = `<a class="dropdown-item" onclick="change_todo_priority(${note['id']}, 1)">Mark Important</a>`;
        }
        $(`#todo_list_${target_id}`).append(`<div id="todo_parent_${note['id']}">
        <div class="d-flex align-items-start">
        <div class="w-100" onclick="get_task_details(${note['id']})">
        <input type="checkbox" class="me-1 form-check-input todo-done todo-item detail-scan-todo-item" ${checked} name="${div_id}" id="${div_id}">
        <label for="${div_id}" class="form-check-label">${important_badge}<${strike_tag}>${htmlEncode(note['title'])}</${strike_tag}></label>
        <${strike_tag}><p>${subdomain_name} <small>${truncate(htmlEncode(note['description']), 150)}</small></p></${strike_tag}>
        </div>
        <div class="btn-group dropstart float-end">
        <a href="#" class="text-dark dropdown-toggle float-start" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
        <i class="fe-more-vertical"></i>
        </a>
        <div class="dropdown-menu" style="">
        ${mark_important}
        <a class="dropdown-item" onclick="delete_todo(${note['id']})">Delete Todo</a>
        </div>
        </div>
        </div>
        <hr/>
        `);
      }
      $('#tasks-count').html(`<span class="badge badge-soft-primary">${data['notes'].length}</span>`);
    }
    else{
      $('#tasks-count').html(`<span class="badge badge-soft-primary me-1">0</span>`);
      $('#todo-list').append(`<p>No todos or notes...</br>You can add todo for individual subdomains or you can also add using + symbol above.</p>`);
    }
    $('.bs-tooltip').tooltip();
    todoCheckboxListener();
  });
}
