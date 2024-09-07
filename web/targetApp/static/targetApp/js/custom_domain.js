function delete_target(id, domain_name) {
  const delAPI = "../../delete/target/" + id;
  swal.queue([{
    title: 'Are you sure you want to delete '+ domain_name +'?',
    text: "You won't be able to revert this!",
    type: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Delete',
    padding: '2em',
    showLoaderOnConfirm: true,
    preConfirm: function() {
      return fetch(delAPI, {
        method: 'POST',
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCookie("csrftoken")
        }
      })
      .then(function (response) {
        return response.json();
      })
      .then(function(data) {
        // TODO Look for better way
        return location.reload();
      })
      .catch(function() {
        swal.insertQueueStep({
          type: 'error',
          title: 'Oops! Unable to delete the target!'
        })
      })
    }
  }])
}

function checkedCount () {
  // this function will count the number of boxes checked
  item = document.getElementsByClassName("targets_checkbox");
  count = 0;
  for (var i = 0; i < item.length; i++) {
    if (item[i].checked) {
      count++;
    }
  }
  return count;
}

function scanMultipleTargets(slug) {
  if (!checkedCount()) {
    swal({
      title: '',
      text: "Oops! No targets has been selected!",
      type: 'error',
      padding: '2em'
    })
  }
  else {
    // atleast one target is selected
    multipleScanForm = document.getElementById("multiple_targets_form");
    multipleScanForm.action = `/scan/${slug}/start/multiple/`;
    multipleScanForm.submit();
  }
}

function deleteMultipleTargets(slug) {
  if (!checkedCount()) {
    Swal.fire({
      title: '',
      text: "Oops! No targets have been selected!",
      icon: 'error',
      padding: '2em'
    });
  } else {
    // At least one target is selected
    Swal.fire({
      title: 'Are you sure you want to delete ' + checkedCount() + ' targets?',
      text: "This action is irreversible.\nThis will also delete all the scan history and vulnerabilities related to the targets.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Delete',
      padding: '2em',
      showLoaderOnConfirm: true,
      preConfirm: () => {
        return new Promise((resolve) => {
          Swal.update({
            title: '',
            text: 'Deleting ' + checkedCount() + ' targets..., this may take a while.',
            icon: 'warning',
            showCancelButton: false,
            showConfirmButton: false,
            allowOutsideClick: false,
          });
          
          setTimeout(() => {
            const deleteForm = document.getElementById("multiple_targets_form");
            deleteForm.action = `/target/${slug}/delete/multiple`;
            deleteForm.submit();
          }, 500);  // 500ms delay
        });
      }
    });
  }
}




function toggleMultipleTargetButton() {
  if (checkedCount() > 0) {
    $("#scan_multiple_button").removeClass("disabled");
    $("#delete_multiple_button").removeClass("disabled");
  }
  else
  {
    $("#scan_multiple_button").addClass("disabled");
    $("#delete_multiple_button").addClass("disabled");
  }
}

function mainCheckBoxSelected() {
  var input = document.querySelector('#head_checkbox');
  if (input.checked) {
    $("#scan_multiple_button").removeClass("disabled");
    $("#delete_multiple_button").removeClass("disabled");
    $(".targets_checkbox").prop('checked', true);
  }
  else
  {
    $("#scan_multiple_button").addClass("disabled");
    $("#delete_multiple_button").addClass("disabled");
    $(".targets_checkbox").prop('checked', false);
  }
}
