function delete_target(id, domain_name) {
    const delAPI = "../delete/"+id;
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

function scanMultipleTargets() {
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
    multipleScanForm.action = '../../start_scan/start/multiple/';
    multipleScanForm.submit();
  }
}

function deleteMultipleTargets() {
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
    swal.queue([{
        title: 'Are you sure you want to delete '+ checkedCount() +' targets?',
        text: "This action is irreversible.\nThis will also delete all the scan history and vulnerabilities related to the targets.",
        type: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Delete',
        padding: '2em',
        showLoaderOnConfirm: true,
        preConfirm: function() {
          deleteForm = document.getElementById("multiple_targets_form");
          deleteForm.action = "../delete/multiple";
          deleteForm.submit();
        }
    }])
  }
}

function toggleMultipleTargetButton() {
  if (checkedCount() > 0) {
    document.getElementsByClassName('multiple_targets_button')[0].style.visibility = 'visible';
  }
  else
  {
    document.getElementsByClassName('multiple_targets_button')[0].style.visibility = 'hidden';
  }
}

function mainCheckBoxSelected() {
  var input = document.querySelector('#head_checkbox');
  if (input.checked) {
    document.getElementsByClassName('multiple_targets_button')[0].style.visibility = 'visible';
  }
  else
 {
    document.getElementsByClassName('multiple_targets_button')[0].style.visibility = 'hidden';
  }
}
