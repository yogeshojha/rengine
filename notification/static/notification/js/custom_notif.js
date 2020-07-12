function change_notif_status(id)
{
    const notifStatusAPI = "change/"+id;

    return fetch(notifStatusAPI, {
        method: 'POST',
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": getCookie("csrftoken")
        }
    })

}

function delete_hook(id, hook_name)
{
    const delAPI = "delete/"+id;
    swal.queue([{
        title: 'Are you sure you want to delete '+ hook_name +'?',
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
                title: 'Oops! Unable to delete the hook!'
              })
            })
        }
    }])
}
