const subdomain_datatable_columns = [
  {'data': 'id'},
  {'data': 'name'},
  {'data': 'endpoint_count'},
  {'data': 'endpoint_count'},
  {'data': 'http_status'},
  {'data': 'page_title'},
  {'data': 'ip_addresses'},
  {'data': 'ip_addresses'},
  {'data': 'content_length', 'searchable': false},
  {'data': 'screenshot_path', 'searchable': false},
  {'data': 'response_time'},
  {'data': 'technologies'},
  {'data': 'http_url'},
  {'data': 'cname'},
  {'data': 'is_interesting'},
  {'data': 'info_count'},
  {'data': 'low_count'},
  {'data': 'medium_count'},
  {'data': 'high_count'},
  {'data': 'critical_count'},
  {'data': 'todos_count'},
  {'data': 'is_important'},
  {'data': 'webserver'},
  {'data': 'content_type'},
  {'data': 'id'},
  {'data': 'directories_count'},
  {'data': 'subscan_count'},
  {'data': 'waf'},
  {'data': 'attack_surface'},
];

const subdomain_datatable_page_length = 50;
const subdomain_datatable_length_menu = [[50, 100, 500, 1000, -1], [50, 100, 500, 1000, 'All']];

const subdomain_oLanguage = {
  "zeroRecords": gettext("No Subdomain detected"),
  "infoEmpty": gettext("No Subdomain detected"),
};

function subdomain_datatable_col_visibility(subdomain_datatables){
  if(!$('#sub_http_status_filter_checkbox').is(":checked")){
    subdomain_datatables.column(get_datatable_col_index('http_status', subdomain_datatable_columns)).visible(false);
  }
  if(!$('#sub_page_title_filter_checkbox').is(":checked")){
    subdomain_datatables.column(get_datatable_col_index('page_title', subdomain_datatable_columns)).visible(false);
  }
  if(!$('#sub_ip_filter_checkbox').is(":checked")){
    subdomain_datatables.column(get_datatable_col_index('ip_addresses', subdomain_datatable_columns)).visible(false);
  }
  if(!$('#sub_ports_filter_checkbox').is(":checked")){
    subdomain_datatables.column(get_datatable_col_index('ip_addresses', subdomain_datatable_columns)).visible(false);
  }
  if(!$('#sub_content_length_filter_checkbox').is(":checked")){
    subdomain_datatables.column(get_datatable_col_index('content_length', subdomain_datatable_columns)).visible(false);
  }
  if(!$('#sub_http_status_filter_checkbox').is(":checked")){
    subdomain_datatables.column(get_datatable_col_index('http_status', subdomain_datatable_columns)).visible(false);
  }
  if(!$('#sub_response_time_filter_checkbox').is(":checked")){
    subdomain_datatables.column(get_datatable_col_index('response_time', subdomain_datatable_columns)).visible(false);
  }
  if(!$('#sub_screenshot_filter_checkbox').is(":checked")){
    subdomain_datatables.column(get_datatable_col_index('screenshot_path', subdomain_datatable_columns)).visible(false);
  }
}
