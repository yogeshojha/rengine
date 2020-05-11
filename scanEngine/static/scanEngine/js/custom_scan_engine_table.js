$(document).ready(function() {
    var table = $('#show-hide-col').DataTable( {
        "searching": false,
        "scrollY": "200px",
        "paging": false,
        "info": false,
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
