const subdomain_datatable_columns = [
  { 'data': 'id' }, // 0: Status/Checkbox
  { 'data': 'name' }, // 1: Subdomain
  { 'data': 'endpoint_count' }, // 2: Endpoints
  { 'data': 'id' }, // 3: Vulnerabilities (Placeholder)
  { 'data': 'http_status' }, // 4: Status
  { 'data': 'page_title' }, // 5: Title
  { 'data': 'ip_addresses' }, // 6: IP
  { 'data': 'ip_addresses' }, // 7: Ports
  { 'data': 'content_length' }, // 8: Content Length
  { 'data': 'screenshot_path' }, // 9: Screenshot
  { 'data': 'response_time' }, // 10: Response Time
  { 'data': 'technologies' }, // 11: Technology
  { 'data': 'id' }, // 12: Checked (Placeholder)
  { 'data': 'http_url' }, // 13: HTTP URL
  { 'data': 'cname' }, // 14: CNAME
  { 'data': 'is_interesting' }, // 15: is_interesting
  { 'data': 'info_count' }, // 16: Info
  { 'data': 'low_count' }, // 17: Low
  { 'data': 'medium_count' }, // 18: Medium
  { 'data': 'high_count' }, // 19: High
  { 'data': 'critical_count' }, // 20: Critical
  { 'data': 'todos_count' }, // 21: Todos
  { 'data': 'is_important' }, // 22: Is Important
  { 'data': 'webserver' }, // 23: Webserver
  { 'data': 'id' }, // 24: Action
  { 'data': 'directories_count' }, // 25: Directories Count
  { 'data': 'subscan_count' }, // 26: Subscan Count
];

const subdomain_datatable_page_length = 50;
const subdomain_datatable_length_menu = [[50, 100, 500, 1000, -1], [50, 100, 500, 1000, 'All']];

const subdomain_oLanguage = {
  "oPaginate": { "sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>', "sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' },
  "sInfo": "Showing page _PAGE_ of _PAGES_",
  "sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  "sSearchPlaceholder": "Search...",
  "sLengthMenu": "Results :  _MENU_",
  "sProcessing": "Fetching Subdomains... Please wait..."
};

function subdomain_datatable_col_visibility(subdomain_datatables) {
  if (!$('#sub_http_status_filter_checkbox').is(":checked")) {
    subdomain_datatables.column(get_datatable_col_index('http_status', subdomain_datatable_columns)).visible(false);
  }
  if (!$('#sub_page_title_filter_checkbox').is(":checked")) {
    subdomain_datatables.column(get_datatable_col_index('page_title', subdomain_datatable_columns)).visible(false);
  }
  if (!$('#sub_ip_filter_checkbox').is(":checked")) {
    subdomain_datatables.column(get_datatable_col_index('ip_addresses', subdomain_datatable_columns)).visible(false);
  }
  if (!$('#sub_ports_filter_checkbox').is(":checked")) {
    subdomain_datatables.column(get_datatable_col_index('ip_addresses', subdomain_datatable_columns)).visible(false);
  }
  if (!$('#sub_content_length_filter_checkbox').is(":checked")) {
    subdomain_datatables.column(get_datatable_col_index('content_length', subdomain_datatable_columns)).visible(false);
  }
  if (!$('#sub_response_time_filter_checkbox').is(":checked")) {
    subdomain_datatables.column(get_datatable_col_index('response_time', subdomain_datatable_columns)).visible(false);
  }
  if (!$('#sub_screenshot_filter_checkbox').is(":checked")) {
    subdomain_datatables.column(get_datatable_col_index('screenshot_path', subdomain_datatable_columns)).visible(false);
  }
}
