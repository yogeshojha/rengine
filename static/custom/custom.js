// seperate hostname and url
// Referenced from https://stackoverflow.com/questions/736513/how-do-i-parse-a-url-into-hostname-and-path-in-javascript
function getParsedURL(url) {
	var parser = new URL(url);
	return parser.pathname+parser.search;
};

function getCookie(name) {
	var cookieValue = null;
	if (document.cookie && document.cookie !== '') {
		var cookies = document.cookie.split(';');
		for (var i = 0; i < cookies.length; i++) {
			var cookie = jQuery.trim(cookies[i]);
			// Does this cookie string begin with the name we want?
			if (cookie.substring(0, name.length + 1) === (name + '=')) {
				cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
				break;
			}
		}
	}
	return cookieValue;
}

// Source: https://portswigger.net/web-security/cross-site-scripting/preventing#encode-data-on-output
function htmlEncode(str){
	return String(str).replace(/[^\w. ]/gi, function(c){
		return '&#'+c.charCodeAt(0)+';';
	});
}

function deleteScheduledScan(id, task_name)
{
	const delAPI = "../delete/scheduled_task/"+id;
	swal.queue([{
		title: 'Are you sure you want to delete ' + task_name + '?',
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
					title: 'Oops! Unable to delete the scheduled task!'
				})
			})
		}
	}])
}

function change_scheduled_task_status(id)
{
	const taskStatusApi = "../toggle/scheduled_task/"+id;

	return fetch(taskStatusApi, {
		method: 'POST',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken")
		}
	})
}

function change_vuln_status(id)
{
	const vulnStatusApi = "../toggle/vuln_status/"+id;

	return fetch(vulnStatusApi, {
		method: 'POST',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken")
		}
	})
}

function change_subdomain_status(id)
{
	const subdomainStatusApi = "../toggle/subdomain_status/"+id;

	return fetch(subdomainStatusApi, {
		method: 'POST',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken")
		}
	})
}

function get_ips_from_port(port_number, history_id){
	document.getElementById("detailScanModalLabel").innerHTML='IPs with port ' + port_number + ' OPEN';
	var ip_badge = '';
	fetch('../port/ip/'+port_number+'/'+history_id+'/')
	.then(response => response.json())
	.then(data => render_ips(data));
}

function get_ports_for_ip(ip, history_id){
	document.getElementById("detailScanModalLabel").innerHTML='Open Ports identified for ' + ip;
	var port_badge = '';
	fetch('../ip/ports/'+ip+'/'+history_id+'/')
	.then(response => response.json())
	.then(data => render_ports(data));
}

function render_ports(data)
{
	var port_badge = ''
	ip_address_content = document.getElementById("detailScanModalContent");
	Object.entries(JSON.parse(data)).forEach(([key, value]) => {
		badge_color = value[3] ? 'danger' : 'info';
		title = value[3] ? 'Uncommon Port - ' + value[2] : value[2];
		port_badge += `<span class='m-1 badge badge-pills outline-badge-${badge_color} bs-tooltip' title='${title}'>${value[0]}/${value[1]}</span>`
	});
	ip_address_content.innerHTML = port_badge;
	$('.bs-tooltip').tooltip();
}

function render_ips(data)
{
	var ip_badge = ''
	content = document.getElementById("detailScanModalContent");
	Object.entries(JSON.parse(data)).forEach(([key, value]) => {
		badge_color = value[1] ? 'warning' : 'info';
		title = value[1] ? 'CDN IP Address' : '';
		ip_badge += `<span class='m-1 badge badge-pills outline-badge-${badge_color} bs-tooltip' title='${title}'>${value[0]}</span>`
	});
	content.innerHTML = ip_badge;
	$('.bs-tooltip').tooltip();
}

function collapse_sidebar()
{
	// This function collapses sidebar
	// collapse sidebar only when screen size is > md (bootstrap), for smaller screen theme already hides the sidebar
	if ($(window).width() > 992) {
		$( document ).ready(function() {
			$("html, body").addClass("sidebar-noneoverflow");
			$("#container").addClass("sidebar-closed");
			$("header").addClass("expand-header");
		});
	}
}

function vuln_status_change(checkbox, id)
{
	if (checkbox.checked) {
		checkbox.parentNode.parentNode.parentNode.className = "table-secondary text-strike";
	}
	else {
		checkbox.parentNode.parentNode.parentNode.classList.remove("table-secondary");
		checkbox.parentNode.parentNode.parentNode.classList.remove("text-strike");
	}
	change_vuln_status(id);
}

// truncate the long string and put ... in the end
function truncate(source, size) {
	return source.length > size ? source.slice(0, size - 1) + "…" : source;
}

// splits really long strings into multiple lines
// Souce: https://stackoverflow.com/a/52395960
function split(str, maxWidth) {
	const newLineStr = "</br>";
	done = false;
	res = '';
	do {
		found = false;
		// Inserts new line at first whitespace of the line
		for (i = maxWidth - 1; i >= 0; i--) {
			if (testWhite(str.charAt(i))) {
				res = res + [str.slice(0, i), newLineStr].join('');
				str = str.slice(i + 1);
				found = true;
				break;
			}
		}
		// Inserts new line at maxWidth position, the word is too long to wrap
		if (!found) {
			res += [str.slice(0, maxWidth), newLineStr].join('');
			str = str.slice(maxWidth);
		}

		if (str.length < maxWidth)
		done = true;
	} while (!done);

	return res + str;
}

function testWhite(x) {
	const white = new RegExp(/^\s$/);
	return white.test(x.charAt(0));
};


function get_response_time_text(response_time){
	var text_color = 'danger';
	if (response_time < 0.5){
		text_color = 'success'
	}
	else if (response_time >= 0.5 && response_time < 1){
		text_color = 'warning'
	}
	return `<span class="text-${text_color}">${response_time.toFixed(4)}s</span>`;
}

// span values function will seperate the values by comma and put badge around it
function parse_comma_values_into_span(data, color, outline=null)
{
	if(outline)
	{
		var badge = `<span class='badge badge-pill outline-badge-`+color+` m-1'>`;
	}
	else {
		var badge = `<span class='badge badge-pill badge-`+color+` m-1'>`;
	}
	var data_with_span ="";
	data.split(/\s*,\s*/).forEach(function(split_vals) {
		data_with_span+=badge + split_vals + "</span>";
	});
	return data_with_span;
}

// span values function will seperate the values by comma and put badge around it
function parse_ip(data, cdn){
	if (cdn)
	{
		var badge = `<span class='badge badge-pill outline-badge-warning m-1 bs-tooltip' title="CDN IP Address">`;
	}
	else{
		var badge = `<span class='badge badge-pill outline-badge-info m-1'>`;
	}
	var data_with_span ="";
	data.split(/\s*,\s*/).forEach(function(split_vals) {
		data_with_span+=badge + split_vals + "</span>";
	});
	return data_with_span;
}

function get_endpoints(scan_history_id, gf_tags){
	var lookup_url = `/start_scan/api/listEndpoints/?scan_history=${scan_history_id}&format=datatables`;
	if (gf_tags){
		lookup_url += `&gf_tag=${gf_tags}`
	}
	$('#endpoint_results').DataTable({
		"destroy": true,
		"oLanguage": {
			"oPaginate": { "sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>', "sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' },
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"dom": "<'row'<'col-lg-10 col-md-10 col-12'f><'col-lg-2 col-md-2 col-12'l>>" +
		"<'row'<'col'tr>>" +
		"<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
		"stripeClasses": [],
		"lengthMenu": [20, 50, 100, 500, 1000],
		"pageLength": 20,
		'serverSide': true,
		"ajax": lookup_url,
		"order": [[ 5, "desc" ]],
		"columns": [
			{'data': 'http_url'},
			{'data': 'http_status'},
			{'data': 'page_title'},
			{'data': 'matched_gf_patterns'},
			{'data': 'content_type'},
			{'data': 'content_length', 'searchable': false},
			{'data': 'technology_stack'},
			{'data': 'webserver'},
			{'data': 'response_time', 'searchable': false},
			{'data': 'is_default', 'searchable': false}
		],
		"columnDefs": [
			{
				"targets": [ 9 ],
				"visible": false,
				"searchable": false,
			},
			{
				"render": function ( data, type, row ) {
					// var isDefault = '';
					// if (row['is_default'])
					// {
					// 	isDefault = `</br><span class='badge badge-pills badge-info'>Default</span>`;
					// }
					var url = split(data, 70);
					return "<a href='"+data+"' target='_blank' class='text-info'>"+url+"</a>";
				},
				"targets": 0,
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
					return "<span class='badge badge-pills badge-danger'>"+data+"</span>";

				},
				"targets": 1,
			},
			{
				"render": function ( data, type, row ) {
					if (data){
						return parse_comma_values_into_span(data.toUpperCase(), "info");
					}
					return "";
				},
				"targets": 6,
			},
			{
				"render": function ( data, type, row ) {
					if (data){
						return parse_comma_values_into_span(data, "danger", outline=true);
					}
					return "";
				},
				"targets": 3,
			},
			{
				"render": function ( data, type, row ) {
					if (data){
						return get_response_time_text(data);
					}
					return "";
				},
				"targets": 8,
			},
		],
		drawCallback: function () {
			$('.t-dot').tooltip({ template: '<div class="tooltip status" role="tooltip"><div class="arrow"></div><div class="tooltip-inner"></div></div>' })
			$('.dataTables_wrapper table').removeClass('table-striped');
		}
	});
}


function get_interesting_subdomains(scan_history_id){
	$('#interesting_subdomains').DataTable({
		"oLanguage": {
			"oPaginate": { "sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>', "sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' },
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"dom": "<'row'<'col-lg-10 col-md-10 col-12'f><'col-lg-2 col-md-2 col-12'l>>" +
		"<'row'<'col'tr>>" +
		"<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
		"destroy": true,
		"bInfo": false,
		"stripeClasses": [],
		'serverSide': true,
		"ajax": `/start_scan/api/listInterestingSubdomains/?scan_id=${scan_history_id}&format=datatables`,
		"order": [[ 3, "desc" ]],
		"columns": [
			{'data': 'name'},
			{'data': 'page_title'},
			{'data': 'http_status'},
			{'data': 'content_length'},
			{'data': 'http_url'},
			{'data': 'technology_stack'},
		],
		"columnDefs": [
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
					if (row['technology_stack']){
						tech_badge = `</br>` + parse_comma_values_into_span(row['technology_stack'], "info", outline=true);
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

function get_interesting_endpoint(scan_history_id){
	$('#interesting_endpoints').DataTable({
		"oLanguage": {
			"oPaginate": { "sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>', "sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' },
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"dom": "<'row'<'col-lg-10 col-md-10 col-12'f><'col-lg-2 col-md-2 col-12'l>>" +
		"<'row'<'col'tr>>" +
		"<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
		'serverSide': true,
		"bInfo": false,
		"ajax": `/start_scan/api/listInterestingEndpoints/?scan_id=${scan_history_id}&format=datatables`,
		"order": [[ 3, "desc" ]],
		"columns": [
			{'data': 'http_url'},
			{'data': 'page_title'},
			{'data': 'http_status'},
			{'data': 'content_length'},
		],
		"columnDefs": [
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


function get_subdomain_changes(scan_history_id){
	$('#table-subdomain-changes').DataTable({
		"oLanguage": {
			"oPaginate": { "sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>', "sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' },
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"dom": "<'row'<'col-lg-10 col-md-10 col-12'f><'col-lg-2 col-md-2 col-12'l>>" +
		"<'row'<'col'tr>>" +
		"<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
		"destroy": true,
		"stripeClasses": [],
		'serverSide': true,
		"ajax": `/start_scan/api/listSubdomainChanges/?scan_id=${scan_history_id}&format=datatables`,
		"order": [[ 3, "desc" ]],
		"columns": [
			{'data': 'http_url'},
			{'data': 'page_title'},
			{'data': 'http_status'},
			{'data': 'content_length'},
			{'data': 'change'},
		],
		"bInfo": false,
		"columnDefs": [
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
			{
				"render": function ( data, type, row ) {
					if (data == 'added'){
						return `<span class='badge badge-success'>Added</span>`;
					}
					else{
						return `<span class='badge badge-danger'>Removed</span>`;
					}
				},
				"targets": 4,
			},
		],
	});
}

function get_endpoint_changes(scan_history_id){
	$('#table-endpoint-changes').DataTable({
		"oLanguage": {
			"oPaginate": { "sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>', "sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>' },
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"dom": "<'row'<'col-lg-10 col-md-10 col-12'f><'col-lg-2 col-md-2 col-12'l>>" +
		"<'row'<'col'tr>>" +
		"<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
		"destroy": true,
		"stripeClasses": [],
		'serverSide': true,
		"ajax": `/start_scan/api/listEndPointChanges/?scan_id=${scan_history_id}&format=datatables`,
		"order": [[ 3, "desc" ]],
		"columns": [
			{'data': 'http_url'},
			{'data': 'page_title'},
			{'data': 'http_status'},
			{'data': 'content_length'},
			{'data': 'change'},
		],
		"bInfo": false,
		"columnDefs": [
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
			{
				"render": function ( data, type, row ) {
					if (data == 'added'){
						return `<span class='badge badge-success'>Added</span>`;
					}
					else{
						return `<span class='badge badge-danger'>Removed</span>`;
					}
				},
				"targets": 4,
			},
		],
	});
}

function get_subdomain_changes_values(scan_id){
	// Subdomain Changes
	$.getJSON(`../api/listSubdomainChanges/?scan_id=${scan_id}&no_page`, function(data) {
		if (!data.length){
			$("#subdomain-changes-div").remove();
			return;
		}

		added_count = 0;
		removed_count = 0;
		for (var val in data) {
			if (data[val]['change'] == 'added'){
				added_count++;
			}
			else if (data[val]['change'] == 'removed')
			{
				removed_count++;
			}
		}
		if (added_count){
			$("#subdomain-added-count").html(`${added_count} Subdomains were added`);
			$("#added_subdomain_badge").html(`+${added_count}`);
			$("#added_subdomain_badge").attr("data-original-title", added_count + " Subdomains were added");
		}
		if (removed_count){
			$("#subdomain-removed-count").html(`${removed_count} Subdomains were removed`);
			$("#removed_subdomain_badge").html(`-${removed_count}`);
			$("#removed_subdomain_badge").attr("data-original-title", removed_count + " Subdomains were removed");
		}
		$("#subdomain_change_count").html(added_count+removed_count);
		$("#subdomain-changes-loader").remove();
		get_subdomain_changes(scan_id);
	});
}

function get_endpoint_changes_values(scan_id){
	// Endpoint Changes
	$.getJSON(`../api/listEndPointChanges/?scan_id=${scan_id}&no_page`, function(data) {
		if (!data.length){
			$("#endpoint-changes-div").remove();
			return;
		}

		added_count = 0;
		removed_count = 0;
		for (var val in data) {
			if (data[val]['change'] == 'added'){
				added_count++;
			}
			else if (data[val]['change'] == 'removed')
			{
				removed_count++;
			}
		}
		if (added_count){
			$("#endpoint-added-count").html(`${added_count} Endpoints were added`);
			$("#added_endpoint_badge").html(`+${added_count}`);
			$("#added_endpoint_badge").attr("data-original-title", added_count + " Endpoints were added");
		}
		if (removed_count){
			$("#endpoint-removed-count").html(`${removed_count} Endpoints were removed`);
			$("#removed_endpoint_badge").html(`-${removed_count}`);
			$("#removed_endpoint_badge").attr("data-original-title", removed_count + " Endpoints were added");
		}
		$("#endpoint_change_count").html(added_count+removed_count);
		$("#endpoint-changes-loader").remove();
		get_endpoint_changes(scan_id);
	});
}

function get_interesting_count(scan_id){
	$.getJSON(`../api/listInterestingSubdomains/?scan_id=${scan_id}&no_page`, function(data) {
		$('#interesting_subdomain_count_badge').empty();
		$('#interesting_subdomain_count_badge').html(`<span class="badge badge-danger">${data.length}</span>`);
	});
	$.getJSON(`../api/listInterestingEndpoints/?scan_id=${scan_id}&no_page`, function(data) {
		$('#interesting_endpoint_count_badge').empty();
		$('#interesting_endpoint_count_badge').html(`<span class="badge badge-danger">${data.length}</span>`);
	});
}


function get_screenshot(scan_id){
	var gridzyElement = document.querySelector('.gridzy');
	gridzyElement.setAttribute('class', 'gridzySkinBlank');
	gridzyElement.setAttribute('data-gridzy-layout', 'waterfall');
	gridzyElement.setAttribute('data-gridzy-spaceBetween', 10);
	gridzyElement.setAttribute('data-gridzy-desiredwidth', 450);
	gridzyElement.setAttribute('data-gridzySearchField', "#screenshot-search");
	var interesting_badge = `<span class="m-1 float-right badge badge-pills badge-danger">Interesting</span>`;
	$.getJSON(`../api/listSubdomains/?scan_id=${scan_id}&no_page&only_screenshot`, function(data) {
		for (var subdomain in data) {
			var figure = document.createElement('figure');
			figure.setAttribute('data-gridzySearchText', data[subdomain]['name']);
			var newImage = document.createElement('img');
			// newImage.setAttribute('data-gridzylazysrc', '/media/' + data[subdomain]['screenshot_path']);
			newImage.setAttribute('data-gridzylazysrc', 'https://placeimg.com/1440/900/any?' + subdomain);
			newImage.setAttribute('height', 650);
			newImage.setAttribute('width', 650);
			var figcaption = document.createElement('figcaption');
			figcaption.setAttribute('class', 'gridzyCaption');
			http_status_badge = 'danger';
			if (data[subdomain]['http_status'] >=200 && data[subdomain]['http_status'] < 300){
				http_status_badge = 'success';
			}
			else if (data[subdomain]['http_status'] >=300 && data[subdomain]['http_status'] < 400){
				http_status_badge = 'warning';
			}
			subdomain_link = `<a href="${data[subdomain]['http_url']}" target="_blank">${data[subdomain]['name']}</a>`
			http_status = `<span class="m-1 float-right badge badge-pills badge-${http_status_badge}">${data[subdomain]['http_status']}</span>`;
			figcaption.innerHTML = data[subdomain]['is_interesting'] ? subdomain_link + interesting_badge + http_status : subdomain_link + http_status;
			newImage.setAttribute('class', 'gridzyImage');
			gridzyElement.appendChild(figure);
			figure.appendChild(newImage);
			figure.appendChild(figcaption);
			// figure.insertAfter(figure, gridzyElement.firstChild);
		}
	});

	// search functionality
	var gridzyElements = document.querySelectorAll('.gridzySkinBlank[data-gridzySearchField]'),
	pos = gridzyElements.length;

	console.log(gridzyElements);

	while (pos--) {
		(function(gridzyElement) {
			var searchField = document.querySelector(gridzyElement.getAttribute('data-gridzySearchField'));
			var gridzyInstance = gridzyElement.gridzy;
			var gridzyItems = gridzyElement.children;

			if (searchField) {
				searchField.addEventListener('input', search);
			}

			function search() {
				var pos = gridzyItems.length,
				child,
				itemContent,
				found = false,
				searchValue = searchField.value.toLowerCase();

				if (searchValue) {
					while (pos--) {
						child = gridzyItems[pos];
						itemContent = (child.getAttribute('data-gridzySearchText') || child.innerText).toLowerCase();
						found = -1 < itemContent.search(searchValue);
						child.classList[found ? 'add' : 'remove']('searchResult');
					}
					if (gridzyInstance.getOption('filter') !== '.searchResult') {
						gridzyInstance.setOptions({filter:'.searchResult'});
					}
				} else {
					while (pos--) {
						gridzyItems[pos].classList.remove('searchResult');
					}
					if (gridzyInstance.getOption('filter') !== Gridzy.getDefaultOption('filter')) {
						gridzyInstance.setOptions({filter:null});
					}
				}
			}
		})(gridzyElements[pos]);
	}
}
