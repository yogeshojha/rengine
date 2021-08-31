function get_important_subdomains(target_id){
  $.getJSON(`/api/querySubdomains/?target_id=${target_id}&only_important&no_lookup_interesting&format=json`, function(data) {
    $('#important-count').empty();
    $('#important-subdomains-list').empty();
    if (data['subdomains'].length > 0){
      $('#important-count').html(`<span class="badge outline-badge-dark">${data['subdomains'].length}</span>`);
      for (var val in data['subdomains']){
        subdomain = data['subdomains'][val];
        div_id = 'important_' + subdomain['id'];
        $("#important-subdomains-list").append(`
          <div id="${div_id}">
          <p>
          <span id="subdomain_${subdomain['id']}"> ${subdomain['name']}
          <span class="">
          <a href="javascript:;" data-clipboard-action="copy" class="m-1 float-right badge-link text-info copyable text-primary" data-toggle="tooltip" data-placement="top" title="Copy Subdomain!" data-clipboard-target="#subdomain_${subdomain['id']}">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-copy"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg></span>
          </a>
          </span>
          </p>
          </div>
          <hr />
          `
        );
      }
    }
    else{
      $('#important-count').html(`<span class="badge outline-badge-dark">0</span>`);
      $('#important-subdomains-list').append(`<p>No subdomains markerd as important!</p>`);
    }
    $('.bs-tooltip').tooltip();
  });
}

function get_interesting_subdomains(target_id){
  var interesting_subdomain_table = $('#interesting_subdomains').DataTable({
    "drawCallback": function(settings, start, end, max, total, pre) {
      $('#interesting_subdomain_count_badge').empty();
      $('#interesting_subdomain_count_badge').html(`<span class="badge outline-badge-danger">${this.fnSettings().fnRecordsTotal()}</span>`);
    },
    "oLanguage": {
      "oPaginate": { "sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>', "sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' },
      "sInfo": "Showing page _PAGE_ of _PAGES_",
      "sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
      "sSearchPlaceholder": "Search...",
      "sLengthMenu": "Results :  _MENU_",
      "sProcessing": "Processing... Please wait..."
    },
    "processing": true,
    "dom": "<'row'<'col-lg-10 col-md-10 col-12'f><'col-lg-2 col-md-2 col-12'l>>" +
    "<'row'<'col'tr>>" +
    "<'dt--bottom-section d-sm-flex justify-content-sm-between text-center'<'dt--pages-count  mb-sm-0 mb-3'i><'dt--pagination'p>>",
    "destroy": true,
    "bInfo": false,
    "stripeClasses": [],
    'serverSide': true,
    "ajax": `/api/listInterestingSubdomains/?target_id=${target_id}&format=datatables`,
    "columns": [
      {'data': 'name'},
      {'data': 'page_title'},
      {'data': 'http_status'},
      {'data': 'content_length'},
      {'data': 'http_url'},
      {'data': 'technologies'},
    ],
    "columnDefs": [
      { "orderable": false, "targets": [0, 1, 2, 3]},
      {
        "targets": [ 4 ],
        "visible": false,
        "searchable": false,
      },
      {
        "targets": [ 5 ],
        "visible": false,
        "searchable": true,
      },
      {"className": "text-center", "targets": [ 2 ]},
      {
        "render": function ( data, type, row ) {
          tech_badge = '';
          if (row['technologies']){
            tech_badge = `</br>` + parse_technology(row['technologies'], "info", outline=true, target_id=null);
          }
          if (row['http_url']) {
            return `<a href="`+row['http_url']+`" class="text-info" target="_blank">`+data+`</a>` + tech_badge;
          }
          return `<a href="https://`+data+`" class="text-info" target="_blank">`+data+`</a>` + tech_badge;
        },
        "targets": 0
      },
      {
        "render": function ( data, type, row ) {
          // display badge based on http status
          // green for http status 2XX, orange for 3XX and warning for everything else
          if (data >= 200 && data < 300) {
            return "<span class='badge badge-pills badge-success'>"+data+"</span>";
          }
          else if (data >= 300 && data < 400) {
            return "<span class='badge badge-pills badge-warning'>"+data+"</span>";
          }
          else if (data == 0){
            // datatable throws error when no data is returned
            return "";
          }
          return `<span class='badge badge-pills badge-danger'>`+data+`</span>`;
        },
        "targets": 2,
      },
    ],
  });
}


function get_interesting_endpoint(target_id){
  $('#interesting_endpoints').DataTable({
    "drawCallback": function(settings, start, end, max, total, pre) {
      $('#interesting_endpoint_count_badge').empty();
      $('#interesting_endpoint_count_badge').html(`<span class="badge outline-badge-danger">${this.fnSettings().fnRecordsTotal()}</span>`);
    },
    "oLanguage": {
      "oPaginate": { "sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>', "sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' },
      "sInfo": "Showing page _PAGE_ of _PAGES_",
      "sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
      "sSearchPlaceholder": "Search...",
      "sLengthMenu": "Results :  _MENU_",
      "sProcessing": "Processing... Please wait..."
    },
    "processing":true,
    "dom": "<'row'<'col-lg-10 col-md-10 col-12'f><'col-lg-2 col-md-2 col-12'l>>" +
    "<'row'<'col'tr>>" +
    "<'dt--bottom-section d-sm-flex justify-content-sm-between text-center'<'dt--pages-count  mb-sm-0 mb-3'i><'dt--pagination'p>>",
    'serverSide': true,
    "bInfo": false,
    "ajax": `/api/listInterestingEndpoints/?target_id=${target_id}&format=datatables`,
    "columns": [
      {'data': 'http_url'},
      {'data': 'page_title'},
      {'data': 'http_status'},
      {'data': 'content_length'},
    ],
    "columnDefs": [
      { "orderable": false, "targets": [0, 1, 2, 3]},
      {"className": "text-center", "targets": [ 2 ]},
      {
        "render": function ( data, type, row ) {
          var url = split(data, 70);
          return "<a href='"+data+"' target='_blank' class='text-info'>"+url+"</a>";
        },
        "targets": 0
      },
      {
        "render": function ( data, type, row ) {
          // display badge based on http status
          // green for http status 2XX, orange for 3XX and warning for everything else
          if (data >= 200 && data < 300) {
            return "<span class='badge badge-pills badge-success'>"+data+"</span>";
          }
          else if (data >= 300 && data < 400) {
            return "<span class='badge badge-pills badge-warning'>"+data+"</span>";
          }
          else if (data == 0){
            // datatable throws error when no data is returned
            return "";
          }
          return `<span class='badge badge-pills badge-danger'>`+data+`</span>`;
        },
        "targets": 2,
      },
    ],
  });
}
