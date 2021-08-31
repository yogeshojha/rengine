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

// Source: https://portswigger.net/web-security/cross-site-scripting/preventing#encode-data-on-output
function jsEscape(str){
	return String(str).replace(/[^\w. ]/gi, function(c){
		return '\\u'+('0000'+c.charCodeAt(0).toString(16)).slice(-4);
	});

}

function deleteScheduledScan(id)
{
	const delAPI = "../delete/scheduled_task/"+id;
	swal.queue([{
		title: 'Are you sure you want to delete this?',
		text: "This action is irreversible.",
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
			if (test_white_space(str.charAt(i))) {
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

function test_white_space(x) {
	const white = new RegExp(/^\s$/);
	return white.test(x.charAt(0));
};

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

function delete_all_scan_results()
{
	const delAPI = "../start_scan/delete/scan_results/";
	swal.queue([{
		title: 'Are you sure you want to delete all scan results?',
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
					title: 'Oops! Unable to delete Delete scan results!'
				})
			})
		}
	}])
}


function delete_all_screenshots()
{
	const delAPI = "../start_scan/delete/screenshots/";
	swal.queue([{
		title: 'Are you sure you want to delete all Screenshots?',
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
					title: 'Oops! Unable to delete Empty Screenshots!'
				})
			})
		}
	}])
}

function load_image_from_url(src, append_to_id){
	img = document.createElement('img');
	img.src = src;
	img.style.width = '100%';
	document.getElementById(append_to_id).appendChild(img);
}


function setTooltip(btn, message) {
	$(btn).tooltip('hide')
	.attr('data-original-title', message)
	.tooltip('show');
}


function hideTooltip(btn) {
	setTimeout(function() {
		$(btn).tooltip('hide');
	}, 1000);
}


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
			data_with_span += badge + ` onclick="get_tech_details('${data[key]['name']}')">` + data[key]['name'] + "</span>";
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

//to remove the image element if there is no screenshot captured
function removeImageElement(element)
{
	element.parentElement.remove();
}

// https://stackoverflow.com/a/18197341/9338140
function download(filename, text) {
	var element = document.createElement('a');
	element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
	element.setAttribute('download', filename);

	element.style.display = 'none';
	document.body.appendChild(element);

	element.click();

	document.body.removeChild(element);
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


function report_hackerone(vulnerability_id, severity){
	message = ""
	if (severity == 'Info' || severity == 'Low' || severity == 'Medium') {
		message = "We do not recommended sending this vulnerability report to hackerone due to the severity, do you still want to report this?"
	}
	else{
		message = "This vulnerability report will be sent to Hackerone.";
	}
	const vulnerability_report_api = "../../api/vulnerability/report/?vulnerability_id=" + vulnerability_id;
	swal.queue([{
		title: 'Reporting vulnerability to hackerone',
		text: message,
		type: 'warning',
		showCancelButton: true,
		confirmButtonText: 'Report',
		padding: '2em',
		showLoaderOnConfirm: true,
		preConfirm: function() {
			return fetch(vulnerability_report_api, {
				method: 'GET',
				credentials: "same-origin",
				headers: {
					"X-CSRFToken": getCookie("csrftoken")
				}
			})
			.then(function (response) {
				return response.json();
			})
			.then(function(data) {
				console.log(data.status)
				if (data.status == 111) {
					swal.insertQueueStep({
						type: 'error',
						title: 'Target does not has team_handle to send report to.'
					})
				}
				else if (data.status == 201) {
					swal.insertQueueStep({
						type: 'success',
						title: 'Vulnerability report successfully submitted to hackerone.'
					})
				}
				else if (data.status == 400) {
					swal.insertQueueStep({
						type: 'error',
						title: 'Invalid Report.'
					})
				}
				else if (data.status == 401) {
					swal.insertQueueStep({
						type: 'error',
						title: 'Hackerone authentication failed.'
					})
				}
				else if (data.status == 403) {
					swal.insertQueueStep({
						type: 'error',
						title: 'API Key forbidden by Hackerone.'
					})
				}
				else if (data.status == 423) {
					swal.insertQueueStep({
						type: 'error',
						title: 'Too many requests.'
					})
				}
			})
			.catch(function() {
				swal.insertQueueStep({
					type: 'error',
					title: 'Oops! Unable to send vulnerability report to hackerone, check your target team_handle or hackerone configurarions!'
				})
			})
		}
	}])
}

function get_interesting_subdomains(target_id, scan_history_id){
	if (target_id) {
		url = `/api/listInterestingEndpoints/?target_id=${target_id}&format=datatables`;
		non_orderable_targets = [0, 1, 2, 3];
	}
	else if (scan_history_id) {
		url  = `/api/listInterestingSubdomains/?scan_id=${scan_history_id}&format=datatables`;
		non_orderable_targets = [];
	}
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
		"ajax": url,
		"order": [[3, "desc"]],
		"columns": [
			{'data': 'name'},
			{'data': 'page_title'},
			{'data': 'http_status'},
			{'data': 'content_length'},
			{'data': 'http_url'},
			{'data': 'technologies'},
		],
		"columnDefs": [
			{ "orderable": false, "targets": non_orderable_targets},
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

function get_interesting_endpoint(target_id, scan_history_id){
	if (target_id) {
		url = `/api/listInterestingEndpoints/?target_id=${target_id}&format=datatables`;
		non_orderable_targets = [0, 1, 2, 3];
	}
	else if (scan_history_id) {
		url = `/api/listInterestingEndpoints/?scan_id=${scan_history_id}&format=datatables`;
		non_orderable_targets = [0, 1, 2, 3];
	}
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
		"ajax": url,
		"order": [[3, "desc"]],
		"columns": [
			{'data': 'http_url'},
			{'data': 'page_title'},
			{'data': 'http_status'},
			{'data': 'content_length'},
		],
		"columnDefs": [
			{ "orderable": false, "targets": non_orderable_targets},
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


function get_important_subdomains(target_id, scan_history_id){
	if (target_id) {
		url = `/api/querySubdomains/?target_id=${target_id}&only_important&no_lookup_interesting&format=json`;
	}
	else if (scan_history_id) {
		url = `/api/querySubdomains/?scan_id=${scan_history_id}&only_important&no_lookup_interesting&format=json`;
	}
	$.getJSON(url, function(data) {
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


function mark_important_subdomain(subdomain_id, target_summary){
	if (target_summary) {
		subdomainImpApi = "../../scan/toggle/subdomain/important/" + subdomain_id;
	}
	else{
		subdomainImpApi = "../toggle/subdomain/important/" + subdomain_id;
	}
  if($("#important_subdomain_" + subdomain_id).length == 0) {
    $("#subdomain-"+subdomain_id).prepend(`<span id="important_subdomain_${subdomain_id}" class="text-danger bs-tooltip" title="Important Subdomain">
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-alert-triangle"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
    </span>`);
    setTooltip("#subdomain-"+subdomain_id, 'Marked Important!');
  }
  else{
    $("#important_subdomain_" + subdomain_id).remove();
    setTooltip("#subdomain-"+subdomain_id, 'Marked Un-Important!');
  }
  hideTooltip("#subdomain-"+subdomain_id);

  return fetch(subdomainImpApi, {
    method: 'POST',
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    }
  });
}
