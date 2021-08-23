$(document).ready(function() {
    var table = $('#show-hide-col').DataTable( {
        "searching": false,
        "scrollY": "280px",
        "paging": false,
        "info": false,
        "ordering": false,
        "stripeClasses": [],
        "lengthMenu": [7, 10, 20, 50],
        "pageLength": 7
    } );
    $('a.toggle-vis').on( 'click', function (e) {
        e.preventDefault();
        // Get the column API object
        var column = table.column( $(this).attr('data-column') );
        // Toggle the visibility
        column.visible( ! column.visible() );
    } );

} );


function delete_api(id, item)
{
    var delAPI = 'delete/'+id;
    swal.queue([{
        title: 'Are you sure you want to delete this scan engine?',
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
                title: 'Oops! Unable to delete'
              })
            })
        }
    }])
}
