function delete_organization(id) {
    const delAPI = "../../delete/organization/"+id;
    swal.queue([{
        title: gettext('Are you sure you want to delete?'),
        text: gettext("You won't be able to revert this!"),
        type: 'warning',
        showCancelButton: true,
        confirmButtonText: gettext('Delete'),
        cancelButtonText: gettext('Cancel'),
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
                title: gettext('Oops! Unable to delete the target!')
              })
            })
        }
    }])
}
