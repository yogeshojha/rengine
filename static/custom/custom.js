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
	console.log(ip, history_id);
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

function parse_technology(data, color, outline=null, scan_id=null)
{
	if(outline)
	{
		var badge = `<span class='badge-link badge badge-pill outline-badge-`+color+` m-1'`;
	}
	else {
		var badge = `<span class='badge-link badge badge-pill badge-`+color+` m-1'`;
	}
	var data_with_span ="";
	for (var key in data){
		if (scan_id){
			data_with_span += badge + ` onclick="get_tech_details('${data[key]['name']}', ${scan_id})">` + data[key]['name'] + "</span>";
		}
		else{
			data_with_span += badge + ">" + data[key]['name'] + "</span>";
		}
	}
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
			{'data': 'technologies'},
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
					if (row['technologies']){
						tech_badge = `</br>` + parse_technology(row['technologies'], "info", outline=true, scan_id=null);
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
			{'data': 'name'},
			{'data': 'page_title'},
			{'data': 'http_status'},
			{'data': 'content_length'},
			{'data': 'change'},
			{'data': 'http_url'},
			{'data': 'is_cdn'},
			{'data': 'is_interesting'},
		],
		"bInfo": false,
		"columnDefs": [
			{
				"targets": [ 5, 6, 7 ],
				"visible": false,
				"searchable": false,
			},
			{"className": "text-center", "targets": [ 2, 4 ]},
			{
				"render": function ( data, type, row ) {
					badges = '';
					cdn_badge = '';
					tech_badge = '';
					interesting_badge = '';
					if (row['is_cdn'])
					{
						cdn_badge = "<span class='m-1 badge badge-pills badge-warning'>CDN</span>"
					}
					if(row['is_interesting'])
					{
						interesting_badge = "<span class='m-1 badge badge-pills badge-danger'>Interesting</span>"
					}
					if(cdn_badge || interesting_badge)
					{
						badges = cdn_badge + interesting_badge + '</br>';
					}
					if (row['http_url']) {
						if (row['cname']) {
							return badges + `<a href="`+row['http_url']+`" class="text-info" target="_blank">`+data+`</a><br><span class="text-dark">CNAME<br><span class="text-warning"> ❯ </span>` + row['cname'].replace(',', '<br><span class="text-warning"> ❯ </span>')+`</span>`;
						}
						return badges + `<a href="`+row['http_url']+`" class="text-info" target="_blank">`+data+`</a>`;
					}
					return badges + `<a href="https://`+data+`" class="text-info" target="_blank">`+data+`</a>`;
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
					if (data){
						return `<span class='text-center' style="display:block; text-align:center; margin:0 auto;">${data}</span>`;
					}
					return "";
				},
				"targets": 3,
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

function get_ips(scan_id){
	$.getJSON(`../api/queryIps/?scan_id=${scan_id}&format=json`, function(data) {
		$('#ip-address-count').empty();
		for (var val in data['ips']){
			ip = data['ips'][val]
			badge_color = ip['is_cdn'] ? 'warning' : 'info';
			$("#ip-address").append(`<span class='badge outline-badge-${badge_color} badge-pills m-1' data-toggle="tooltip" title="${ip['ports'].length} Ports Open." onclick="get_ip_details('${ip['address']}', ${scan_id})">${ip['address']}</span>`);
			// $("#ip-address").append(`<span class='badge outline-badge-${badge_color} badge-pills m-1' data-toggle="modal" data-target="#tabsModal">${ip['address']}</span>`);
		}
		$('#ip-address-count').html(`<span class="badge outline-badge-dark">${data['ips'].length}</span>`);
		$("body").tooltip({ selector: '[data-toggle=tooltip]' });
	});
}

function get_ip_details(ip_address, scan_id){
	// render tab modal
	$('#tab-modal-title').html('Details for IP: <b>' + ip_address + '</b>');
	// add tab modal title
	$('#modal-tabs').empty();
	$('#modal-tabs').append(`<li class="nav-item"><a class="nav-link active" id="open-ports-tab" data-toggle="tab" href="#modal-open-ports" role="tab" aria-controls="home" aria-selected="true"><span id="modal-open-ports-count"></span>Open Ports</a></li>`);
	$('#modal-tabs').append(`<li class="nav-item"><a class="nav-link" id="subdomain-tab" data-toggle="tab" href="#modal-subdomain" role="tab" aria-controls="profile" aria-selected="false"><span id="modal-subdomain-count"></span>Subdomains</a></li>`)
	// add content area
	$('#modal-tab-content').empty();
	$('#modal-tab-content').append(`<div class="tab-pane fade show active" id="modal-open-ports" role="tabpanel" aria-labelledby="open-ports-tab"></div>`);
	$('#modal-open-ports').append(`<div class="modal-text" id="modal-text-open-port"></div>`);
	$('#modal-text-open-port').append(`<ul id="modal-open-port-text"></ul>`);

	$('#modal-tab-content').append(`<div class="tab-pane fade" id="modal-subdomain" role="tabpanel" aria-labelledby="subdomain-tab">`);
	$('#modal-subdomain').append(`<div class="modal-text" id="modal-text-subdomain"></div>`);
	$('#modal-text-subdomain').append(`<ul id="modal-subdomain-text"></ul>`);

	$('#tabsModal').modal('show');
	$.getJSON(`../api/queryPorts/?scan_id=${scan_id}&ip_address=${ip_address}&format=json`, function(data) {
		$('#modal-open-port-text').empty();
		$('#modal-open-port-text').append(`<p> IP Addresses ${ip_address} has ${data['ports'].length} Open Ports`);
		$('#modal-open-ports-count').html(`<b>${data['ports'].length}</b>&nbsp;&nbsp;`);
		for (port in data['ports']){
			port_obj = data['ports'][port];
			badge_color = port_obj['is_uncommon'] ? 'danger' : 'info';
			$("#modal-open-port-text").append(`<li>${port_obj['description']} <b class="text-${badge_color}">(${port_obj['number']}/${port_obj['service_name']})</b></li>`)
		}
	});

	// query subdomains
	$.getJSON(`../api/querySubdomains/?scan_id=${scan_id}&ip_address=${ip_address}&format=json`, function(data) {
		$('#modal-subdomain-text').empty();
		$('#modal-subdomain-text').append(`<p>${data['subdomains'].length} subdomain associated with IP Address: ${ip_address}</p>`);
		$('#modal-subdomain-count').html(`<b>${data['subdomains'].length}</b>&nbsp;&nbsp;`);
		for (subdomain in data['subdomains']){
			subdomain_obj = data['subdomains'][subdomain];
			badge_color = subdomain_obj['http_status'] == 404 ? 'danger' : '';
			if (subdomain_obj['http_url']) {
				$("#modal-subdomain-text").append(`<li><a href='${subdomain_obj['http_url']}' target="_blank" class="text-${badge_color}">${subdomain_obj['name']}</a></li>`)
			}
			else {
				$("#modal-subdomain-text").append(`<li class="text-${badge_color}">${subdomain_obj['name']}</li>`)
			}
		}
		$('#modal-text-subdomain').append(`<span class="float-right text-danger">*Subdomains highlighted are 404 HTTP Status</span>`);
	});
}

function get_port_details(port, scan_id){
	// render tab modal
	$('#tab-modal-title').html('Details for Port: <b>' + port + '</b>');
	// add tab modal title
	$('#modal-tabs').empty();
	$('#modal-tabs').append(`<li class="nav-item"><a class="nav-link active" id="ip-tab" data-toggle="tab" href="#modal-ip" role="tab" aria-controls="home" aria-selected="true"><span id="modal-ip-count"></span>IP Address</a></li>`);
	$('#modal-tabs').append(`<li class="nav-item"><a class="nav-link" id="subdomain-tab" data-toggle="tab" href="#modal-subdomain" role="tab" aria-controls="profile" aria-selected="false"><span id="modal-subdomain-count"></span>Subdomains</a></li>`)
	// add content area
	$('#modal-tab-content').empty();
	$('#modal-tab-content').append(`<div class="tab-pane fade show active" id="modal-ip" role="tabpanel" aria-labelledby="ip-tab"></div>`);
	$('#modal-ip').append(`<div class="modal-text" id="modal-text-ip"></div>`);
	$('#modal-text-ip').append(`<ul id="modal-ip-text"></ul>`);

	$('#modal-tab-content').append(`<div class="tab-pane fade" id="modal-subdomain" role="tabpanel" aria-labelledby="subdomain-tab">`);
	$('#modal-subdomain').append(`<div class="modal-text" id="modal-text-subdomain"></div>`);
	$('#modal-text-subdomain').append(`<ul id="modal-subdomain-text"></ul>`);

	$('#tabsModal').modal('show');
	$.getJSON(`../api/queryIps/?scan_id=${scan_id}&port=${port}&format=json`, function(data) {
		$('#modal-ip-text').empty();
		$('#modal-ip-text').append(`<p>${data['ips'].length} IP Addresses has Port ${port} Open`);
		$('#modal-ip-count').html(`<b>${data['ips'].length}</b>&nbsp;&nbsp;`);
		for (ip in data['ips']){
			ip_obj = data['ips'][ip];
			text_color = ip_obj['is_cdn'] ? 'warning' : '';
			$("#modal-ip-text").append(`<li class='text-${text_color}'>${ip_obj['address']}</li>`)
		}
		$('#modal-text-ip').append(`<span class="float-right text-warning">*IP Address highlighted are CDN IP Address</span>`);
	});

	// query subdomains
	$.getJSON(`../api/querySubdomains/?scan_id=${scan_id}&port=${port}&format=json`, function(data) {
		$('#modal-subdomain-text').empty();
		$('#modal-subdomain-text').append(`<p>${data['subdomains'].length} Subdomain has Port ${port} Open`);
		$('#modal-subdomain-count').html(`<b>${data['subdomains'].length}</b>&nbsp;&nbsp;`);
		for (subdomain in data['subdomains']){
			subdomain_obj = data['subdomains'][subdomain];
			badge_color = subdomain_obj['http_status'] == 404 ? 'danger' : '';
			if (subdomain_obj['http_url']) {
				$("#modal-subdomain-text").append(`<li><a href='${subdomain_obj['http_url']}' target="_blank" class="text-${badge_color}">${subdomain_obj['name']}</a></li>`)
			}
			else {
				$("#modal-subdomain-text").append(`<li class="text-${badge_color}">${subdomain_obj['name']}</li>`);
			}
		}
		$('#modal-text-subdomain').append(`<span class="float-right text-danger">*Subdomains highlighted are 404 HTTP Status</span>`);
	});
}

function get_tech_details(tech, scan_id){
	// render tab modal
	$('.modal-title').html('Details for Technology: <b>' + tech + '</b>');
	$('#exampleModal').modal('show');
	$('.modal-text').empty();
	// query subdomains
	$.getJSON(`../api/querySubdomains/?scan_id=${scan_id}&tech=${tech}&format=json`, function(data) {
		$('#modal-text-content').append(`${data['subdomains'].length} Subdomains using ${tech}`);
		$('#modal-text-content').append(`<ul id="subdomain-modal-ul"></ul>`);
		for (subdomain in data['subdomains']){
			subdomain_obj = data['subdomains'][subdomain];
			badge_color = subdomain_obj['http_status'] == 404 ? 'danger' : '';
			if (subdomain_obj['http_url']) {
				$("#subdomain-modal-ul").append(`<li><a href='${subdomain_obj['http_url']}' target="_blank" class="text-${badge_color}">${subdomain_obj['name']}</a></li>`);
			}
			else {
				$("#subdomain-modal-ul").append(`<li class="text-${badge_color}">${subdomain_obj['name']}</li>`);
			}
		}
		$('#modal-text-content').append(`<span class="float-right text-danger">*Subdomains highlighted are 404 HTTP Status</span>`);
	});
}

function get_technologies(scan_id){
	$.getJSON(`../api/queryTechnologies/?scan_id=${scan_id}&format=json`, function(data) {
		$('#technologies-count').empty();
		for (var val in data['technologies']){
			tech = data['technologies'][val]
			$("#technologies").append(`<span class='badge outline-badge-info badge-pills m-1' data-toggle="tooltip" title="${tech['count']} Subdomains use this technology." onclick="get_tech_details('${tech['name']}', ${scan_id})">${tech['name']}</span>`);
		}
		$('#technologies-count').html(`<span class="badge outline-badge-dark">${data['technologies'].length}</span>`);
		$("body").tooltip({ selector: '[data-toggle=tooltip]' });
	});
}

function get_osint_users(scan_id){
	$.getJSON(`../api/queryOsintUsers/?scan_id=${scan_id}&format=json`, function(data) {
		$('#osint-users-count').empty();
		for (var val in data['users']){
			user = data['users'][val]
			$("#osint-users").append(`<span class='badge outline-badge-info badge-pills m-1'>${user['author']}</span>`);
		}
		$('#osint-users-count').html(`<span class="badge outline-badge-dark">${data['users'].length}</span>`);
		$("body").tooltip({ selector: '[data-toggle=tooltip]' });
	}).fail(function(){
		$('#osint-users-count').empty();
		$("#osint-users").append(`<p>No Users discovered.</p>`);
	});
}

function get_ports(scan_id){
	$.getJSON(`../api/queryPorts/?scan_id=${scan_id}&format=json`, function(data) {
		$('#ports-count').empty();
		for (var val in data['ports']){
			port = data['ports'][val]
			badge_color = port['is_uncommon'] ? 'danger' : 'info';
			$("#ports").append(`<span class='badge outline-badge-${badge_color} badge-pills m-1' data-toggle="tooltip" title="${port['description']}" onclick="get_port_details('${port['number']}', ${scan_id})">${port['number']}/${port['service_name']}</span>`);
		}
		$('#ports-count').html(`<span class="badge outline-badge-dark">${data['ports'].length}</span>`);
		$("body").tooltip({ selector: '[data-toggle=tooltip]' });
	});
}

function get_interesting_count(scan_id){
	$.getJSON(`../api/listInterestingSubdomains/?scan_id=${scan_id}&no_page`, function(data) {
		$('#interesting_subdomain_count_badge').empty();
		$('#interesting_subdomain_count_badge').html(`<span class="badge outline-badge-danger">${data.length}</span>`);
	});
	$.getJSON(`../api/listInterestingEndpoints/?scan_id=${scan_id}&no_page`, function(data) {
		$('#interesting_endpoint_count_badge').empty();
		$('#interesting_endpoint_count_badge').html(`<span class="badge outline-badge-danger">${data.length}</span>`);
	});
}

function get_screenshot(scan_id){
	var port_array = [];
	var service_array = [];
	var tech_array = [];
	var ip_array = [];
	var gridzyElement = document.querySelector('.gridzy');
	gridzyElement.classList.add('gridzySkinBlank');
	gridzyElement.setAttribute('data-gridzy-layout', 'waterfall');
	gridzyElement.setAttribute('data-gridzy-spaceBetween', 10);
	gridzyElement.setAttribute('data-gridzy-desiredwidth', 500);
	gridzyElement.setAttribute('data-gridzySearchField', "#screenshot-search");
	var interesting_badge = `<span class="m-1 float-right badge badge-pills badge-danger">Interesting</span>`;
	$.getJSON(`../api/listSubdomains/?scan_id=${scan_id}&no_page&only_screenshot`, function(data) {
		console.log(data);

		for (var subdomain in data) {
			var figure = document.createElement('figure');
			var link = document.createElement('a');
			// return `<a href="/media/`+data+`" data-lightbox="screenshots" data-title="&lt;a target='_blank' href='`+row['http_url']+`'&gt;&lt;h3 style=&quot;color:white&quot;&gt;`+row['name']+`&lt;/h3&gt;&lt;/a&gt;"><img src="/media/`+data+`" class="img-fluid rounded mb-4 mt-4 screenshot" onerror="removeImageElement(this)"></a>`;
			// currently lookup is supported only for http_status, page title & subdomain name,
			interesting_field = data[subdomain]['is_interesting'] ? 'interesting' : '';
			search_field = `${data[subdomain]['page_title']} ${data[subdomain]['name']} ${data[subdomain]['http_status']} ${interesting_field}`;
			link.setAttribute('data-lightbox', 'screenshot-gallery')
			link.setAttribute('href', '/media/' + data[subdomain]['screenshot_path'])
			link.setAttribute('data-title', `<a target='_blank' href='`+data[subdomain]['http_url']+`'><h3 style="color:white">`+data[subdomain]['name']+`</h3></a>`);
			link.classList.add('img-fluid');
			link.classList.add('rounded');
			link.classList.add('screenshot-gallery');
			link.classList.add('mb-4');
			link.classList.add('mt-4');
			link.setAttribute('data-gridzySearchText', search_field);
			var newImage = document.createElement('img');
			newImage.setAttribute('data-gridzylazysrc', '/media/' + data[subdomain]['screenshot_path']);
			// newImage.setAttribute('data-gridzylazysrc', 'https://placeimg.com/1440/900/any?' + subdomain);
			newImage.setAttribute('height', 500);
			newImage.setAttribute('width', 500);
			newImage.setAttribute('class', 'gridzyImage');
			var figcaption = document.createElement('figcaption');
			figcaption.setAttribute('class', 'gridzyCaption');
			http_status_badge = 'danger';
			if (data[subdomain]['http_status'] >=200 && data[subdomain]['http_status'] < 300){
				http_status_badge = 'success';
			}
			else if (data[subdomain]['http_status'] >=300 && data[subdomain]['http_status'] < 400){
				http_status_badge = 'warning';
			}
			page_title = data[subdomain]['page_title'] ? data[subdomain]['page_title'] + '</br>': '' ;
			subdomain_link = data[subdomain]['http_url'] ? `<a href="${data[subdomain]['http_url']}" target="_blank">${data[subdomain]['name']}</a>` : `<a href="https://${data[subdomain]['name']}" target="_blank">${data[subdomain]['name']}</a>`
			http_status = data[subdomain]['http_status'] ? `<span class="m-1 float-right badge badge-pills badge-${http_status_badge}">${data[subdomain]['http_status']}</span>` : '';
			figcaption.innerHTML = data[subdomain]['is_interesting'] ? page_title + subdomain_link + interesting_badge + http_status : page_title + subdomain_link + http_status;
			figure.appendChild(figcaption);
			link.appendChild(newImage);
			link.appendChild(figure);
			gridzyElement.appendChild(link);

			// add http status to filter values
			filter_values = 'http_' + data[subdomain]['http_status'] + ' ';

			// dynamic filtering menu
			http_status = data[subdomain]['http_status'];
			http_status_select = document.getElementById('http_select_filter');
			if(!$('#http_select_filter').find("option:contains('" + http_status + "')").length){
				var option = document.createElement('option');
				option.value = ".http_" + http_status;
				option.innerHTML = http_status;
				http_status_select.appendChild(option);
			}

			// ip, port and services filtering
			ips = data[subdomain]['ip_addresses']
			for(var ip in ips){
				ip_address = ips[ip]['address'];
				filter_values += 'ip_' + ip_address + ' ';
				if (ip_array.indexOf(ip_address) === -1){
					ip_array.push(ip_address);
				}

				ports = ips[ip]['ports'];
				for(var port in ports){
					port_number = ips[ip]['ports'][port]['number'];
					service_name = ips[ip]['ports'][port]['service_name'];

					filter_values += 'port_' + port_number + ' ';
					if (port_array.indexOf(port_number) === -1){
						port_array.push(port_number);
					}

					filter_values += 'service_' + service_name + ' ';
					if (service_array.indexOf(service_name) === -1){
						service_array.push(service_name);
					}
				}
			}

			// technology stack filtering
			technology = data[subdomain]['technologies'];
			for(var tech in technology){
				tech_name = technology[tech]['name']
				filter_values += 'tech_' + tech_name.replace(/ /g,"_").toLowerCase() + ' ';
				if (tech_array.indexOf(tech_name) === -1){
					tech_array.push(tech_name);
				}

			}

			link.setAttribute('class', filter_values);
		}

		// add port and service and tech to options
		port_array.sort((a, b) => a - b);
		port_select = document.getElementById('ports_select_filter');
		for(var port in port_array){
			if(!$('#ports_select_filter').find("option:contains('" + port_array[port] + "')").length){
				var option = document.createElement('option');
				option.value = ".port_" + port_array[port];
				option.innerHTML = port_array[port];
				port_select.appendChild(option);
			}
		}

		// add ip to select
		ip_select = document.getElementById('ips_select_filter');
		for(var ip in ip_array){
			if(!$('#ips_select_filter').find("option:contains('" + ip_array[ip] + "')").length){
				var option = document.createElement('option');
				option.value = ".ip_" + ip_array[ip];
				option.innerHTML = ip_array[ip];
				ip_select.appendChild(option);
			}
		}

		service_array.sort();
		service_select = document.getElementById('services_select_filter');
		for(var service in service_array){
			if(!$('#services_select_filter').find("option:contains('" + service_array[service] + "')").length){
				var option = document.createElement('option');
				option.value = ".service_" + service_array[service];
				option.innerHTML = service_array[service];
				service_select.appendChild(option);
			}
		}

		tech_select = document.getElementById('tech_select_filter');
		for(var tech in tech_array){
			if(!$('#tech_select_filter').find("option:contains('" + tech_array[tech] + "')").length){
				var option = document.createElement('option');
				option.value = ".tech_" + tech_array[tech].replace(/ /g,"_").toLowerCase();
				option.innerHTML = tech_array[tech];
				tech_select.appendChild(option);
			}
		}

	});

	// search functionality
	var gridzyElements = document.querySelectorAll('.gridzySkinBlank[data-gridzySearchField]'),
	pos = gridzyElements.length;

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

	//filter functionality
	var gridzyInstance = document.querySelector('.gridzySkinBlank').gridzy;
	$('#http_select_filter, #services_select_filter, #ports_select_filter, #tech_select_filter').on('change', function() {
		values = $(this).val();
		console.log(values);
		if(values.length){
			gridzyInstance.setOptions({
				filter: values
			});
		}
		else{
			gridzyInstance.setOptions({
				filter: '*'
			});
		}
	});
}

// Source: https://stackoverflow.com/a/54733055
function typingEffect(words, id, i) {
	let word = words[i].split("");
	var loopTyping = function() {
		if (word.length > 0) {
			let elem = document.getElementById(id);
			elem.setAttribute('placeholder', elem.getAttribute('placeholder') + word.shift());
		} else {
			deletingEffect(words, id, i);
			return false;
		};
		timer = setTimeout(loopTyping, 150);
	};
	loopTyping();
};

function deletingEffect(words, id, i) {
	let word = words[i].split("");
	var loopDeleting = function() {
		if (word.length > 0) {
			word.pop();
			document.getElementById(id).setAttribute('placeholder', word.join(""));
		} else {
			if (words.length > (i + 1)) {
				i++;
			} else {
				i = 0;
			};
			typingEffect(words, id, i);
			return false;
		};
		timer = setTimeout(loopDeleting, 90);
	};
	loopDeleting();
};

function fullScreenDiv(id, btn){
	let fullscreen = document.querySelector(id);
	let button = document.querySelector(btn);

	document.fullscreenElement && document.exitFullscreen() || document.querySelector(id).requestFullscreen()

	fullscreen.setAttribute("style","overflow:auto");
}

function get_randid(){
	return '_' + Math.random().toString(36).substr(2, 9);
}

function get_metadata(scan_id){
	$.getJSON(`../api/queryMetadata/?scan_id=${scan_id}&format=json`, function(data) {
		$('#metadata-count').empty();
		for (var val in data['metadata']){
			doc = data['metadata'][val];
			rand_id = get_randid();
			$('#metadata-table-body').append(`<tr id=${rand_id}></tr>`);
			file_name = `<a href=${doc['url']} target="_blank" class="text-info">${truncate(doc['name'], 30)}</a>`;
			subdomain = `<span class='text-muted'>${doc['subdomain']['name']}</span>`;
			$(`#${rand_id}`).append(`<td class="td-content">${file_name}</br>${subdomain}</td>`);
			if (doc['author']){
				$(`#${rand_id}`).append(`<td class="td-content text-center">${doc['author']}</td>`);
			}
			else{
				$(`#${rand_id}`).append('<td></td>')
			}
			if (doc['producer'] || doc['creator'] || doc['os']) {
				metadata = ''
				metadata += doc['producer'] ? 'Software: ' + doc['producer'] : ''
				metadata += doc['creator'] ? '/' + doc['creator'] : ''
				metadata += doc['os'] ? '<br> <span class=text-warning> OS: ' + doc['os'] + '</span>': ''
				$(`#${rand_id}`).append(`<td class="td-content">${metadata}</td>`);
			}
			else{
				$(`#${rand_id}`).append('<td></td>')
			}
		}
		$('#metadata-count').html(`<span class="badge outline-badge-dark">${data['metadata'].length}</span>`);
	});
}


function get_emails(scan_id){
	$.getJSON(`../api/queryEmails/?scan_id=${scan_id}&format=json`, function(data) {
		$('#emails-count').empty();
		for (var val in data['emails']){
			email = data['emails'][val];
			rand_id = get_randid();
			$('#email-table-body').append(`<tr id=${rand_id}></tr>`);
			$(`#${rand_id}`).append(`<td class="td-content">${email['address']}</td>`);
		}
		$('#emails-count').html(`<span class="badge outline-badge-dark">${data['emails'].length}</span>`);
	});
}


function get_employees(scan_id){
	$.getJSON(`../api/queryEmployees/?scan_id=${scan_id}&format=json`, function(data) {
		$('#employees-count').empty();
		for (var val in data['employees']){
			emp = data['employees'][val];
			rand_id = get_randid();
			console.log(emp);
			$('#employees-table-body').append(`<tr id=${rand_id}></tr>`);
			$(`#${rand_id}`).append(`<td class="td-content">${emp['name']}</td>`);
			$(`#${rand_id}`).append(`<td class="td-content">${emp['designation']}</td>`);
		}
		$('#employees-count').html(`<span class="badge outline-badge-dark">${data['employees'].length}</span>`);
	});
}
