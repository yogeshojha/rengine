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
