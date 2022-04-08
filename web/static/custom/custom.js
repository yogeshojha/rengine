function checkall(clickchk, relChkbox) {
	var checker = $('#' + clickchk);
	var multichk = $('.' + relChkbox);
	checker.click(function() {
		multichk.prop('checked', $(this).prop('checked'));
	});
}

function multiCheck(tb_var) {
	tb_var.on("change", ".chk-parent", function() {
			var e = $(this).closest("table").find("td:first-child .child-chk"),
				a = $(this).is(":checked");
			$(e).each(function() {
				a ? ($(this).prop("checked", !0), $(this).closest("tr").addClass("active")) : ($(this).prop("checked", !1), $(this).closest("tr").removeClass("active"))
			})
		}),
		tb_var.on("change", "tbody tr .new-control", function() {
			$(this).parents("tr").toggleClass("active")
		})
}

function GetIEVersion() {
	var sAgent = window.navigator.userAgent;
	var Idx = sAgent.indexOf("MSIE");
	// If IE, return version number.
	if(Idx > 0) return parseInt(sAgent.substring(Idx + 5, sAgent.indexOf(".", Idx)));
	// If IE 11 then look for Updated user agent string.
	else if(!!navigator.userAgent.match(/Trident\/7\./)) return 11;
	else return 0; //It is not IE
}

function truncate(str, n) {
	return(str.length > n) ? str.substr(0, n - 1) + '&hellip;' : str;
};

function return_str_if_not_null(val) {
	return val ? val : '';
}
// seperate hostname and url
// Referenced from https://stackoverflow.com/questions/736513/how-do-i-parse-a-url-into-hostname-and-path-in-javascript
function getParsedURL(url) {
	var parser = new URL(url);
	return parser.pathname + parser.search;
};

function getCookie(name) {
	var cookieValue = null;
	if(document.cookie && document.cookie !== '') {
		var cookies = document.cookie.split(';');
		for(var i = 0; i < cookies.length; i++) {
			var cookie = jQuery.trim(cookies[i]);
			// Does this cookie string begin with the name we want?
			if(cookie.substring(0, name.length + 1) === (name + '=')) {
				cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
				break;
			}
		}
	}
	return cookieValue;
}
// Source: https://portswigger.net/web-security/cross-site-scripting/preventing#encode-data-on-output
function htmlEncode(str) {
	return String(str).replace(/[^\w. ]/gi, function(c) {
		return '&#' + c.charCodeAt(0) + ';';
	});
}
// Source: https://portswigger.net/web-security/cross-site-scripting/preventing#encode-data-on-output
function jsEscape(str) {
	return String(str).replace(/[^\w. ]/gi, function(c) {
		return '\\u' + ('0000' + c.charCodeAt(0).toString(16)).slice(-4);
	});
}

function deleteScheduledScan(id) {
	const delAPI = "../delete/scheduled_task/" + id;
	swal.queue([{
		title: 'Are you sure you want to delete this?',
		text: "This action can not be undone.",
		icon: 'warning',
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
			}).then(function(response) {
				return response.json();
			}).then(function(data) {
				// TODO Look for better way
				return location.reload();
			}).catch(function() {
				swal.insertQueueStep({
					icon: 'error',
					title: 'Oops! Unable to delete the scheduled task!'
				})
			})
		}
	}])
}

function change_scheduled_task_status(id, checkbox) {
	if(checkbox.checked) {
		text_msg = 'Schedule Scan Started';
	} else {
		text_msg = 'Schedule Scan Stopped';
	}
	Snackbar.show({
		text: text_msg,
		pos: 'top-right',
		duration: 2500
	});
	const taskStatusApi = "../toggle/scheduled_task/" + id;
	return fetch(taskStatusApi, {
		method: 'POST',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken")
		}
	})
}

function change_vuln_status(id) {
	const vulnStatusApi = "../toggle/vuln_status/" + id;
	return fetch(vulnStatusApi, {
		method: 'POST',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken")
		}
	})
}
// splits really long strings into multiple lines
// Souce: https://stackoverflow.com/a/52395960
function split_into_lines(str, maxWidth) {
	const newLineStr = "</br>";
	done = false;
	res = '';
	do {
		found = false;
		// Inserts new line at first whitespace of the line
		for(i = maxWidth - 1; i >= 0; i--) {
			if(test_white_space(str.charAt(i))) {
				res = res + [str.slice(0, i), newLineStr].join('');
				str = str.slice(i + 1);
				found = true;
				break;
			}
		}
		// Inserts new line at maxWidth position, the word is too long to wrap
		if(!found) {
			res += [str.slice(0, maxWidth), newLineStr].join('');
			str = str.slice(maxWidth);
		}
		if(str.length < maxWidth) done = true;
	} while (!done);
	return res + str;
}

function test_white_space(x) {
	const white = new RegExp(/^\s$/);
	return white.test(x.charAt(0));
};
// span values function will seperate the values by comma and put badge around it
function parse_comma_values_into_span(data, color, outline = null) {
	if(data) {
		var badge = `<span class='badge badge-soft-` + color + ` m-1'>`;
		var data_with_span = "";
		data.split(/\s*,\s*/).forEach(function(split_vals) {
			data_with_span += badge + split_vals + "</span>";
		});
		return data_with_span;
	}
	return '';
}

function get_severity_badge(severity) {
	switch(severity) {
		case 'Info':
			return "<span class='badge badge-soft-primary'>&nbsp;&nbsp;INFO&nbsp;&nbsp;</span>";
			break;
		case 'Low':
			return "<span class='badge badge-low'>&nbsp;&nbsp;LOW&nbsp;&nbsp;</span>";
			break;
		case 'Medium':
			return "<span class='badge badge-soft-warning'>&nbsp;&nbsp;MEDIUM&nbsp;&nbsp;</span>";
			break;
		case 'High':
			return "<span class='badge badge-soft-danger'>&nbsp;&nbsp;HIGH&nbsp;&nbsp;</span>";
			break;
		case 'Critical':
			return "<span class='badge badge-critical'>&nbsp;&nbsp;CRITICAL&nbsp;&nbsp;</span>";
			break;
		default:
			return "";
	}
}
// Source: https://stackoverflow.com/a/54733055
function typingEffect(words, id, i) {
	let word = words[i].split("");
	var loopTyping = function() {
		if(word.length > 0) {
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
		if(word.length > 0) {
			word.pop();
			document.getElementById(id).setAttribute('placeholder', word.join(""));
		} else {
			if(words.length > (i + 1)) {
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

function fullScreenDiv(id, btn) {
	let fullscreen = document.querySelector(id);
	let button = document.querySelector(btn);
	document.fullscreenElement && document.exitFullscreen() || document.querySelector(id).requestFullscreen()
	fullscreen.setAttribute("style", "overflow:auto");
}

function get_randid() {
	return '_' + Math.random().toString(36).substr(2, 9);
}

function delete_all_scan_results() {
	const delAPI = "../scan/delete/scan_results/";
	swal.queue([{
		title: 'Are you sure you want to delete all scan results?',
		text: "You won't be able to revert this!",
		icon: 'warning',
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
			}).then(function(response) {
				return response.json();
			}).then(function(data) {
				// TODO Look for better way
				return location.reload();
			}).catch(function() {
				swal.insertQueueStep({
					icon: 'error',
					title: 'Oops! Unable to delete Delete scan results!'
				})
			})
		}
	}])
}

function delete_all_screenshots() {
	const delAPI = "../scan/delete/screenshots/";
	swal.queue([{
		title: 'Are you sure you want to delete all Screenshots?',
		text: "You won't be able to revert this!",
		icon: 'warning',
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
			}).then(function(response) {
				return response.json();
			}).then(function(data) {
				// TODO Look for better way
				return location.reload();
			}).catch(function() {
				swal.insertQueueStep({
					icon: 'error',
					title: 'Oops! Unable to delete Empty Screenshots!'
				})
			})
		}
	}])
}

function load_image_from_url(src, append_to_id) {
	img = document.createElement('img');
	img.src = src;
	img.style.width = '100%';
	document.getElementById(append_to_id).appendChild(img);
}

function setTooltip(btn, message) {
	hide_all_tooltips();
	const instance = tippy(document.querySelector(btn));
	instance.setContent(message);
	instance.show();
	setTimeout(function() {
		instance.hide();
	}, 500);
}

function hide_all_tooltips() {
	$(".tooltip").tooltip("hide");
}

function get_response_time_text(response_time) {
	if(response_time) {
		var text_color = 'danger';
		if(response_time < 0.5) {
			text_color = 'success'
		} else if(response_time >= 0.5 && response_time < 1) {
			text_color = 'warning'
		}
		return `<span class="text-${text_color}">${response_time.toFixed(4)}s</span>`;
	}
	return '';
}

function parse_technology(data, color, outline = null, scan_id = null) {
	if(outline) {
		var badge = `<span data-toggle="tooltip" title="Technology" class='badge-link badge badge-soft-` + color + ` mt-1 me-1'`;
	} else {
		var badge = `<span data-toggle="tooltip" title="Technology" class='badge-link badge badge-soft-` + color + ` mt-1 me-1'`;
	}
	var data_with_span = "";
	for(var key in data) {
		if(scan_id) {
			data_with_span += badge + ` onclick="get_tech_details('${data[key]['name']}', ${scan_id})">` + data[key]['name'] + "</span>";
		} else {
			data_with_span += badge + ` onclick="get_tech_details('${data[key]['name']}')">` + data[key]['name'] + "</span>";
		}
	}
	return data_with_span;
}
// span values function will seperate the values by comma and put badge around it
function parse_ip(data, cdn) {
	if(cdn) {
		var badge = `<span class='badge badge-soft-warning m-1 bs-tooltip' title="CDN IP Address">`;
	} else {
		var badge = `<span class='badge badge-soft-primary m-1'>`;
	}
	var data_with_span = "";
	data.split(/\s*,\s*/).forEach(function(split_vals) {
		data_with_span += badge + split_vals + "</span>";
	});
	return data_with_span;
}
//to remove the image element if there is no screenshot captured
function removeImageElement(element) {
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

function vuln_status_change(checkbox, id) {
	if(checkbox.checked) {
		checkbox.parentNode.parentNode.parentNode.className = "table-success text-strike";
	} else {
		checkbox.parentNode.parentNode.parentNode.classList.remove("table-success");
		checkbox.parentNode.parentNode.parentNode.classList.remove("text-strike");
	}
	change_vuln_status(id);
}

function report_hackerone(vulnerability_id, severity) {
	message = ""
	if(severity == 'Info' || severity == 'Low' || severity == 'Medium') {
		message = "We do not recommended sending this vulnerability report to hackerone due to the severity, do you still want to report this?"
	} else {
		message = "This vulnerability report will be sent to Hackerone.";
	}
	const vulnerability_report_api = "../../api/vulnerability/report/?vulnerability_id=" + vulnerability_id;
	swal.queue([{
		title: 'Reporting vulnerability to hackerone',
		text: message,
		icon: 'warning',
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
			}).then(function(response) {
				return response.json();
			}).then(function(data) {
				console.log(data.status)
				if(data.status == 111) {
					swal.insertQueueStep({
						icon: 'error',
						title: 'Target does not has team_handle to send report to.'
					})
				} else if(data.status == 201) {
					swal.insertQueueStep({
						icon: 'success',
						title: 'Vulnerability report successfully submitted to hackerone.'
					})
				} else if(data.status == 400) {
					swal.insertQueueStep({
						icon: 'error',
						title: 'Invalid Report.'
					})
				} else if(data.status == 401) {
					swal.insertQueueStep({
						icon: 'error',
						title: 'Hackerone authentication failed.'
					})
				} else if(data.status == 403) {
					swal.insertQueueStep({
						icon: 'error',
						title: 'API Key forbidden by Hackerone.'
					})
				} else if(data.status == 423) {
					swal.insertQueueStep({
						icon: 'error',
						title: 'Too many requests.'
					})
				}
			}).catch(function() {
				swal.insertQueueStep({
					icon: 'error',
					title: 'Oops! Unable to send vulnerability report to hackerone, check your target team_handle or hackerone configurarions!'
				})
			})
		}
	}])
}

function get_interesting_subdomains(target_id, scan_history_id) {
	if(target_id) {
		url = `/api/listInterestingEndpoints/?target_id=${target_id}&format=datatables`;
		non_orderable_targets = [0, 1, 2, 3];
	} else if(scan_history_id) {
		url = `/api/listInterestingSubdomains/?scan_id=${scan_history_id}&format=datatables`;
		non_orderable_targets = [];
	}
	var interesting_subdomain_table = $('#interesting_subdomains').DataTable({
		"drawCallback": function(settings, start, end, max, total, pre) {
			// if no interesting subdomains are found, hide the datatable and show no interesting subdomains found badge
			if(this.fnSettings().fnRecordsTotal() == 0) {
				$('#interesting_subdomain_div').empty();
				// $('#interesting_subdomain_div').append(`<div class="card-header bg-primary py-3 text-white">
				// <div class="card-widgets">
				// <a href="#" data-toggle="remove"><i class="mdi mdi-close"></i></a>
				// </div>
				// <h5 class="card-title mb-0 text-white"><i class="mdi mdi-fire-alert me-2"></i>Interesting subdomains could not be identified</h5>
				// </div>
				// <div id="cardCollpase4" class="collapse show">
				// <div class="card-body">
				// reNgine could not identify any interesting subdomains. You can customize interesting subdomain keywords <a href="/scanEngine/interesting/lookup/">from here</a> and this section would be automatically updated.
				// </div>
				// </div>`);
			} else {
				// show nav bar
				$('.interesting-tab-show').removeAttr('style');
				$('#interesting_subdomain_alert_count').html(`${this.fnSettings().fnRecordsTotal()} Interesting Subdomains`)
				$('#interesting_subdomain_count_badge').empty();
				$('#interesting_subdomain_count_badge').html(`<span class="badge badge-soft-primary me-1">${this.fnSettings().fnRecordsTotal()}</span>`);
			}
		},
		"oLanguage": {
			"oPaginate": {
				"sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>',
				"sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>'
			},
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"processing": true,
		"dom": "<'dt--top-section'<'row'<'col-12 col-sm-6 d-flex justify-content-sm-start justify-content-center'f><'col-12 col-sm-6 d-flex justify-content-sm-end justify-content-center'l>>>" + "<'table-responsive'tr>" + "<'dt--bottom-section d-sm-flex justify-content-sm-between text-center'<'dt--pages-count  mb-sm-0 mb-3'i><'dt--pagination'p>>",
		"destroy": true,
		"bInfo": false,
		"stripeClasses": [],
		'serverSide': true,
		"ajax": url,
		"order": [
			[3, "desc"]
		],
		"lengthMenu": [5, 10, 20, 50, 100],
		"pageLength": 10,
		"columns": [{
			'data': 'name'
		}, {
			'data': 'page_title'
		}, {
			'data': 'http_status'
		}, {
			'data': 'content_length'
		}, {
			'data': 'http_url'
		}, {
			'data': 'technologies'
		}, ],
		"columnDefs": [{
			"orderable": false,
			"targets": non_orderable_targets
		}, {
			"targets": [4],
			"visible": false,
			"searchable": false,
		}, {
			"targets": [5],
			"visible": false,
			"searchable": true,
		}, {
			"className": "text-center",
			"targets": [2]
		}, {
			"render": function(data, type, row) {
				tech_badge = '';
				if(row['technologies']) {
					// tech_badge = `</br>` + parse_technology(row['technologies'], "primary", outline=true, scan_id=null);
				}
				if(row['http_url']) {
					return `<a href="` + row['http_url'] + `" class="text-primary" target="_blank">` + data + `</a>` + tech_badge;
				}
				return `<a href="https://` + data + `" class="text-primary" target="_blank">` + data + `</a>` + tech_badge;
			},
			"targets": 0
		}, {
			"render": function(data, type, row) {
				// display badge based on http status
				// green for http status 2XX, orange for 3XX and warning for everything else
				if(data >= 200 && data < 300) {
					return "<span class='badge badge-pills badge-soft-success'>" + data + "</span>";
				} else if(data >= 300 && data < 400) {
					return "<span class='badge badge-pills badge-soft-warning'>" + data + "</span>";
				} else if(data == 0) {
					// datatable throws error when no data is returned
					return "";
				}
				return `<span class='badge badge-pills badge-soft-danger'>` + data + `</span>`;
			},
			"targets": 2,
		}, ],
	});
}

function get_interesting_endpoint(target_id, scan_history_id) {
	var non_orderable_targets = [];
	if(target_id) {
		url = `/api/listInterestingEndpoints/?target_id=${target_id}&format=datatables`;
		// non_orderable_targets = [0, 1, 2, 3];
	} else if(scan_history_id) {
		url = `/api/listInterestingEndpoints/?scan_id=${scan_history_id}&format=datatables`;
		// non_orderable_targets = [0, 1, 2, 3];
	}
	$('#interesting_endpoints').DataTable({
		"drawCallback": function(settings, start, end, max, total, pre) {
			if(this.fnSettings().fnRecordsTotal() == 0) {
				$('#interesting_endpoint_div').remove();
			} else {
				$('.interesting-tab-show').removeAttr('style');
				$('#interesting_endpoint_alert_count').html(`, ${this.fnSettings().fnRecordsTotal()} Interesting Endpoints`)
				$('#interesting_endpoint_count_badge').empty();
				$('#interesting_endpoint_count_badge').html(`<span class="badge badge-soft-primary me-1">${this.fnSettings().fnRecordsTotal()}</span>`);
			}
		},
		"oLanguage": {
			"oPaginate": {
				"sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>',
				"sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>'
			},
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"processing": true,
		"dom": "<'dt--top-section'<'row'<'col-12 col-sm-6 d-flex justify-content-sm-start justify-content-center'f><'col-12 col-sm-6 d-flex justify-content-sm-end justify-content-center'l>>>" + "<'table-responsive'tr>" + "<'dt--bottom-section d-sm-flex justify-content-sm-between text-center'<'dt--pages-count  mb-sm-0 mb-3'i><'dt--pagination'p>>",
		'serverSide': true,
		"destroy": true,
		"bInfo": false,
		"ajax": url,
		"order": [
			[3, "desc"]
		],
		"lengthMenu": [5, 10, 20, 50, 100],
		"pageLength": 10,
		"columns": [{
			'data': 'http_url'
		}, {
			'data': 'page_title'
		}, {
			'data': 'http_status'
		}, {
			'data': 'content_length'
		}, ],
		"columnDefs": [{
			"orderable": false,
			"targets": non_orderable_targets
		}, {
			"className": "text-center",
			"targets": [2]
		}, {
			"render": function(data, type, row) {
				var url = split_into_lines(data, 70);
				return "<a href='" + data + "' target='_blank' class='text-primary'>" + url + "</a>";
			},
			"targets": 0
		}, {
			"render": function(data, type, row) {
				// display badge based on http status
				// green for http status 2XX, orange for 3XX and warning for everything else
				if(data >= 200 && data < 300) {
					return "<span class='badge badge-pills badge-soft-success'>" + data + "</span>";
				} else if(data >= 300 && data < 400) {
					return "<span class='badge badge-pills badge-soft-warning'>" + data + "</span>";
				} else if(data == 0) {
					// datatable throws error when no data is returned
					return "";
				}
				return `<span class='badge badge-pills badge-soft-danger'>` + data + `</span>`;
			},
			"targets": 2,
		}, ],
	});
}

function get_important_subdomains(target_id, scan_history_id) {
	if(target_id) {
		url = `/api/querySubdomains/?target_id=${target_id}&only_important&no_lookup_interesting&format=json`;
	} else if(scan_history_id) {
		url = `/api/querySubdomains/?scan_id=${scan_history_id}&only_important&no_lookup_interesting&format=json`;
	}
	$.getJSON(url, function(data) {
		$('#important-count').empty();
		$('#important-subdomains-list').empty();
		if(data['subdomains'].length > 0) {
			$('#important-count').html(`<span class="badge badge-soft-primary ms-1 me-1">${data['subdomains'].length}</span>`);
			for(var val in data['subdomains']) {
				subdomain = data['subdomains'][val];
				div_id = 'important_' + subdomain['id'];
				$("#important-subdomains-list").append(`
					<div id="${div_id}">
					<p>
					<span id="subdomain_${subdomain['id']}"> ${subdomain['name']}
					<span class="">
					<a href="javascript:;" data-clipboard-action="copy" class="m-1 float-end badge-link text-info copyable text-primary" data-toggle="tooltip" data-placement="top" title="Copy Subdomain!" data-clipboard-target="#subdomain_${subdomain['id']}">
					<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-copy"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg></span>
					</a>
					</span>
					</p>
					</div>
					<hr />
					`);
			}
		} else {
			$('#important-count').html(`<span class="badge badge-soft-primary ms-1 me-1">0</span>`);
			$('#important-subdomains-list').append(`<p>No subdomains markerd as important!</p>`);
		}
		$('.bs-tooltip').tooltip();
	});
}

function mark_important_subdomain(row, subdomain_id, target_summary) {
	if(row) {
		parentNode = row.parentNode.parentNode.parentNode;
		if(parentNode.classList.contains('table-danger')) {
			parentNode.classList.remove('table-danger');
		} else {
			parentNode.className = "table-danger";
		}
	}
	if(target_summary) {
		subdomainImpApi = "../../scan/toggle/subdomain/important/" + subdomain_id;
	} else {
		subdomainImpApi = "../toggle/subdomain/important/" + subdomain_id;
	}
	if($("#important_subdomain_" + subdomain_id).length == 0) {
		$("#subdomain-" + subdomain_id).prepend(`<span id="important_subdomain_${subdomain_id}"></span>`);
		setTooltip("#subdomain-" + subdomain_id, 'Marked Important!');
	} else {
		$("#important_subdomain_" + subdomain_id).remove();
		setTooltip("#subdomain-" + subdomain_id, 'Marked Un-Important!');
	}
	return fetch(subdomainImpApi, {
		method: 'POST',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken")
		}
	});
}

function delete_scan(id) {
	const delAPI = "../delete/scan/" + id;
	swal.queue([{
		title: 'Are you sure you want to delete this scan history?',
		text: "You won't be able to revert this!",
		icon: 'warning',
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
			}).then(function(response) {
				return response.json();
			}).then(function(data) {
				// TODO Look for better way
				return location.reload();
			}).catch(function() {
				swal.insertQueueStep({
					icon: 'error',
					title: 'Oops! Unable to delete the scan history!'
				})
			})
		}
	}]);
}

function stop_scan(celery_id, is_scan = true, reload_scan_bar = true, reload_location = false) {
	const stopAPI = "/api/action/stop/scan/";
	data = {
		'celery_id': celery_id,
		'is_scan': is_scan
	}
	swal.queue([{
		title: 'Are you sure you want to stop this scan?',
		text: "You won't be able to revert this!",
		icon: 'warning',
		showCancelButton: true,
		confirmButtonText: 'Stop',
		padding: '2em',
		showLoaderOnConfirm: true,
		preConfirm: function() {
			return fetch(stopAPI, {
				method: 'POST',
				credentials: "same-origin",
				body: JSON.stringify(data),
				headers: {
					"X-CSRFToken": getCookie("csrftoken"),
					"Content-Type": 'application/json',
				}
			}).then(function(response) {
				return response.json();
			}).then(function(data) {
				// TODO Look for better way
				if(data.status) {
					Snackbar.show({
						text: 'Scan Successfully Aborted.',
						pos: 'top-right',
						duration: 1500
					});
					if(reload_scan_bar) {
						getScanStatusSidebar();
					}
					if(reload_location) {
						window.location.reload();
					}
				} else {
					Snackbar.show({
						text: 'Oops! Could not abort the scan.',
						pos: 'top-right',
						duration: 1500
					});
				}
			}).catch(function() {
				swal.insertQueueStep({
					icon: 'error',
					title: 'Oops! Unable to stop the scan'
				})
			})
		}
	}])
}

function extractContent(s) {
	var span = document.createElement('span');
	span.innerHTML = s;
	return span.textContent || span.innerText;
};

function delete_datatable_rows(table_id, rows_id, show_snackbar = true, snackbar_title) {
	// this function will delete the datatables rows after actions such as delete
	// table_id => datatable_id with #
	// rows_ids: list/array => list of all numerical ids to delete, to maintain consistency
	//     rows id will always follow this pattern: datatable_id_row_n
	// show_snackbar = bool => whether to show snackbar or not!
	// snackbar_title: str => snackbar title if show_snackbar = True
	var table = $(table_id).DataTable();
	for(var row in rows_id) {
		table.row(table_id + '_row_' + rows_id[row]).remove().draw();
	}
	Snackbar.show({
		text: snackbar_title,
		pos: 'top-right',
		duration: 1500,
		actionTextColor: '#fff',
		backgroundColor: '#e7515a',
	});
}

function delete_subscan(subscan_id) {
	// This function will delete the sunscans using rest api
	// Supported method: POST
	const delAPI = "/api/action/rows/delete/";
	var data = {
		'type': 'subscan',
		'rows': [subscan_id]
	}
	swal.queue([{
		title: 'Are you sure you want to delete this subscan?',
		text: "You won't be able to revert this!",
		icon: 'warning',
		showCancelButton: true,
		confirmButtonText: 'Delete',
		padding: '2em',
		showLoaderOnConfirm: true,
		preConfirm: function() {
			return fetch(delAPI, {
				method: 'POST',
				credentials: "same-origin",
				headers: {
					"X-CSRFToken": getCookie("csrftoken"),
					"Content-Type": "application/json"
				},
				body: JSON.stringify(data)
			}).then(function(response) {
				return response.json();
			}).then(function(response) {
				if(response['status']) {
					delete_datatable_rows('#subscan_history_table', [subscan_id], show_snackbar = true, '1 Subscan Deleted!')
				}
			}).catch(function() {
				swal.insertQueueStep({
					icon: 'error',
					title: 'Oops! Unable to delete the scan history!'
				})
			})
		}
	}])
}

function show_subscan_results(subscan_id) {
	// This function will popup a modal and show the subscan results
	// modal being used is from base
	var api_url = '/api/fetch/results/subscan?format=json';
	var data = {
		'subscan_id': subscan_id
	};
	Swal.fire({
		title: 'Fetching Results...'
	});
	swal.showLoading();
	fetch(api_url, {
		method: 'POST',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken"),
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(data)
	}).then(response => response.json()).then(function(response) {
		console.log(response);
		swal.close();
		if(response['subscan']['status'] == -1) {
			swal.fire("Error!", "Scan has not yet started! Please wait for other scans to complete...", "warning", {
				button: "Okay",
			});
			return;
		} else if(response['subscan']['status'] == 1) {
			swal.fire("Error!", "Scan is in progress! Please come back later...", "warning", {
				button: "Okay",
			});
			return;
		}
		$('#xl-modal-title').empty();
		$('#xl-modal-content').empty();
		$('#xl-modal-footer').empty();
		var task_name = '';
		if(response['subscan']['task'] == 'port_scan') {
			task_name = 'Port Scan';
		} else if(response['subscan']['task'] == 'vulnerability_scan') {
			task_name = 'Vulnerability Scan';
		} else if(response['subscan']['task'] == 'fetch_url') {
			task_name = 'EndPoint Gathering';
		} else if(response['subscan']['task'] == 'dir_file_fuzz') {
			task_name = 'Directory and Files Fuzzing';
		}
		$('#xl-modal_title').html(`${task_name} Results on ${response['subscan']['subdomain_name']}`);
		var scan_status = '';
		var badge_color = 'danger';
		if(response['subscan']['status'] == 0) {
			scan_status = 'Failed';
		} else if(response['subscan']['status'] == 2) {
			scan_status = 'Successful';
			badge_color = 'success';
		} else if(response['subscan']['status'] == 3) {
			scan_status = 'Aborted';
		} else {
			scan_status = 'Unknown';
		}
		$('#xl-modal-content').append(`<div>Scan Status: <span class="badge bg-${badge_color}">${scan_status}</span></div>`);
		if(response['result'].length > 0) {
			if(response['subscan']['task'] == 'port_scan') {
				$('#xl-modal-content').append(`<div id="port_results_li"></div>`);
				for(var ip in response['result']) {
					var ip_addr = response['result'][ip]['address'];
					var id_name = `ip_${ip_addr}`;
					$('#port_results_li').append(`<h5>IP Address: ${ip_addr}</br></br>${response['result'][ip]['ports'].length} Ports Open</h5>`);
					$('#port_results_li').append(`<ul id="${id_name}"></ul>`);
					for(var port_obj in response['result'][ip]['ports']) {
						var port = response['result'][ip]['ports'][port_obj];
						var port_color = 'primary';
						if(port["is_uncommon"]) {
							port_color = 'danger';
						}
						$('#port_results_li ul').append(`<li><span class="ms-1 mt-1 me-1 badge badge-soft-${port_color}">${port['number']}</span>/<span class="ms-1 mt-1 me-1 badge badge-soft-${port_color}">${port['service_name']}</span>/<span class="ms-1 mt-1 me-1 badge badge-soft-${port_color}">${port['description']}</span></li>`);
					}
				}
				$('#xl-modal-footer').append(`<span class="text-danger">* Uncommon Ports</span>`);
			} else if(response['subscan']['task'] == 'vulnerability_scan') {
				render_vulnerability_in_xl_modal(vuln_count=response['result'].length, subdomain_name=response['subscan']['subdomain_name'], result=response['result']);
			} else if(response['subscan']['task'] == 'fetch_url') {
				render_endpoint_in_xlmodal(endpoint_count = response['result'].length, subdomain_name = response['subscan']['subdomain_name'], result = response['result']);
			} else if(response['subscan']['task'] == 'dir_file_fuzz') {
				if(response['result'][0]['directory_files'].length == 0) {
					$('#xl-modal-content').append(`
						<div class="alert alert-info mt-2" role="alert">
						<i class="mdi mdi-alert-circle-outline me-2"></i> ${task_name} could not fetch any results.
						</div>
					`);
				} else {
					render_directories_in_xl_modal(response['result'][0]['directory_files'].length, response['subscan']['subdomain_name'], response['result'][0]['directory_files']);
				}
			}
		} else {
			$('#xl-modal-content').append(`
				<div class="alert alert-info mt-2" role="alert">
				<i class="mdi mdi-alert-circle-outline me-2"></i> ${task_name} could not fetch any results.
				</div>
				`);
		}
		$('#modal_xl_scroll_dialog').modal('show');
		$("body").tooltip({
			selector: '[data-toggle=tooltip]'
		});
	});
}

function get_http_status_badge(data) {
	if(data >= 200 && data < 300) {
		return "<span class='badge  badge-soft-success'>" + data + "</span>";
	} else if(data >= 300 && data < 400) {
		return "<span class='badge  badge-soft-warning'>" + data + "</span>";
	} else if(data == 0) {
		// datatable throws error when no data is returned
		return "";
	}
	return "<span class='badge  badge-soft-danger'>" + data + "</span>";
}

function render_endpoint_in_xlmodal(endpoint_count, subdomain_name, result) {
	// This function renders endpoints datatable in xl modal
	// Used in Subscan results and subdomain to endpoints modal
	$('#xl-modal-content').append(`<h5> ${endpoint_count} Endpoints Discovered on subdomain ${subdomain_name}</h5>`);
	$('#xl-modal-content').append(`
		<div class="">
		<table id="endpoint-modal-datatable" class="table dt-responsive nowrap w-100">
		<thead>
		<tr>
		<th>HTTP URL</th>
		<th>Status</th>
		<th>Page Title</th>
		<th>Tags</th>
		<th>Content Type</th>
		<th>Content Length</th>
		<th>Response Time</th>
		</tr>
		</thead>
		<tbody id="endpoint_tbody">
		</tbody>
		</table>
		</div>
	`);
	$('#endpoint_tbody').empty();
	for(var endpoint_obj in result) {
		var endpoint = result[endpoint_obj];
		var tech_badge = '';
		var web_server = '';
		if(endpoint['technologies']) {
			tech_badge = '<div>' + parse_technology(endpoint['technologies'], "primary", outline = true);
		}
		if(endpoint['webserver']) {
			web_server = `<span class='m-1 badge badge-soft-info' data-toggle="tooltip" data-placement="top" title="Web Server">${endpoint['webserver']}</span>`;
		}
		var url = split_into_lines(endpoint['http_url'], 70);
		var rand_id = get_randid();
		tech_badge += web_server + '</div>';
		var http_url_td = "<a href='" + endpoint['http_url'] + `' target='_blank' class='text-primary'>` + url + "</a>" + tech_badge;
		$('#endpoint_tbody').append(`
			<tr>
			<td>${http_url_td}</td>
			<td>${get_http_status_badge(endpoint['http_status'])}</td>
			<td>${return_str_if_not_null(endpoint['page_title'])}</td>
			<td>${parse_comma_values_into_span(endpoint['matched_gf_patterns'], "danger", outline=true)}</td>
			<td>${return_str_if_not_null(endpoint['content_type'])}</td>
			<td>${return_str_if_not_null(endpoint['content_length'])}</td>
			<td>${get_response_time_text(endpoint['response_time'])}</td>
			</tr>
		`);
	}
	$("#endpoint-modal-datatable").DataTable({
		"oLanguage": {
			"oPaginate": {
				"sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>',
				"sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>'
			},
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"dom": "<'dt--top-section'<'row'<'col-12 col-sm-6 d-flex justify-content-sm-start justify-content-center'f><'col-12 col-sm-6 d-flex justify-content-sm-end justify-content-center'l>>>" + "<'table-responsive'tr>" + "<'dt--bottom-section d-sm-flex justify-content-sm-between text-center'<'dt--pages-count  mb-sm-0 mb-3'i><'dt--pagination'p>>",
		"order": [
			[5, "desc"]
		],
		drawCallback: function() {
			$(".dataTables_paginate > .pagination").addClass("pagination-rounded")
		}
	});
}

function render_vulnerability_in_xl_modal(vuln_count, subdomain_name, result){
	// This function will render the vulnerability datatable in xl modal
	$('#xl-modal-content').append(`<h5> ${vuln_count} Vulnerabilities Discovered on subdomain ${subdomain_name}</h5>`);
	$('#xl-modal-content').append(`<ol id="vuln_results_ol" class="list-group list-group-numbered"></ol>`);
	$('#xl-modal-content').append(`
		<div class="">
		<table id="vulnerability-modal-datatable" class="table dt-responsive nowrap w-100">
		<thead>
		<tr>
		<th>Type</th>
		<th>Title</th>
		<th class="text-center">Severity</th>
		<th>CVSS Score</th>
		<th>CVE/CWE</th>
		<th>Vulnerable URL</th>
		<th>Description</th>
		<th class="text-center dt-no-sorting">Action</th>
		</tr>
		</thead>
		<tbody id="vuln_tbody">
		</tbody>
		</table>
		</div>
		`);
	$('#vuln_tbody').empty();
	for(var vuln in result) {
		var vuln_obj = result[vuln];
		var vuln_type = vuln_obj['type'] ? `<span class="badge badge-soft-primary">&nbsp;&nbsp;${vuln_obj['type'].toUpperCase()}&nbsp;&nbsp;</span>` : '';
		var tags = '';
		var cvss_metrics_badge = '';
		switch(vuln_obj['severity']) {
			case 'Info':
				color = 'primary'
				badge_color = 'soft-primary'
				break;
			case 'Low':
				color = 'low'
				badge_color = 'soft-warning'
				break;
			case 'Medium':
				color = 'warning'
				badge_color = 'soft-warning'
				break;
			case 'High':
				color = 'danger'
				badge_color = 'soft-danger'
				break;
			case 'Critical':
				color = 'critical'
				badge_color = 'critical'
				break;
			default:
		}
		if(vuln_obj['tags']) {
			tags = '<div>';
			vuln_obj['tags'].forEach(tag => {
				tags += `<span class="badge badge-${badge_color} me-1 mb-1" data-toggle="tooltip" data-placement="top" title="Tags">${tag}</span>`;
			});
			tags += '</div>';
		}
		if(vuln_obj['cvss_metrics']) {
			cvss_metrics_badge = `<div><span class="badge badge-outline-primary my-1" data-toggle="tooltip" data-placement="top" title="CVSS Metrics">${vuln_obj['cvss_metrics']}</span></div>`;
		}
		var vuln_title = `<b class="text-${color}">` + vuln_obj['name'] + `</b>` + cvss_metrics_badge + tags;
		var badge = 'danger';
		var cvss_score = '';
		if(vuln_obj['cvss_score']) {
			if(vuln_obj['cvss_score'] > 0.1 && vuln_obj['cvss_score'] <= 3.9) {
				badge = 'info';
			} else if(vuln_obj['cvss_score'] > 3.9 && vuln_obj['cvss_score'] <= 6.9) {
				badge = 'warning';
			} else if(vuln_obj['cvss_score'] > 6.9 && vuln_obj['cvss_score'] <= 8.9) {
				badge = 'danger';
			}
			cvss_score = `<span class="badge badge-outline-${badge}" data-toggle="tooltip" data-placement="top" title="CVSS Score">${vuln_obj['cvss_score']}</span>`;
		}
		var cve_cwe_badge = '<div>';
		if(vuln_obj['cve_ids']) {
			vuln_obj['cve_ids'].forEach(cve => {
				cve_cwe_badge += `<a href="https://google.com/search?q=${cve.toUpperCase()}" target="_blank" class="badge badge-outline-primary me-1 mt-1" data-toggle="tooltip" data-placement="top" title="CVE ID">${cve.toUpperCase()}</a>`;
			});
		}
		if(vuln_obj['cwe_ids']) {
			vuln_obj['cwe_ids'].forEach(cwe => {
				cve_cwe_badge += `<a href="https://google.com/search?q=${cwe.toUpperCase()}" target="_blank" class="badge badge-outline-primary me-1 mt-1" data-toggle="tooltip" data-placement="top" title="CWE ID">${cwe.toUpperCase()}</a>`;
			});
		}
		cve_cwe_badge += '</div>';
		var http_url = vuln_obj['http_url'].includes('http') ? "<a href='" + htmlEncode(vuln_obj['http_url']) + "' target='_blank' class='text-danger'>" + htmlEncode(vuln_obj['http_url']) + "</a>" : vuln_obj['http_url'];
		var description = vuln_obj['description'] ? `<div>${split_into_lines(vuln_obj['description'], 30)}</div>` : '';
		// show extracted results, and show matcher names, matcher names can be in badges
		if(vuln_obj['matcher_name']) {
			description += `<span class="badge badge-soft-primary" data-toggle="tooltip" data-placement="top" title="Matcher Name">${vuln_obj['matcher_name']}</span>`;
		}
		if(vuln_obj['extracted_results'] && vuln_obj['extracted_results'].length > 0) {
			description += `<br><a class="mt-2" data-bs-toggle="collapse" href="#results_${vuln_obj['id']}" aria-expanded="false" aria-controls="results_${vuln_obj['id']}">Extracted Results <i class="fe-chevron-down"></i></a>`;
			description += `<div class="collapse" id="results_${vuln_obj['id']}"><ul>`;
			vuln_obj['extracted_results'].forEach(results => {
				description += `<li>${results}</li>`;
			});
			description += '</ul></div>';
		}
		if(vuln_obj['references'] && vuln_obj['references'].length > 0) {
			description += `<br><a class="mt-2" data-bs-toggle="collapse" href="#references_${vuln_obj['id']}" aria-expanded="false" aria-controls="references_${vuln_obj['id']}">References <i class="fe-chevron-down"></i></a>`;
			description += `<div class="collapse" id="references_${vuln_obj['id']}"><ul>`;
			vuln_obj['references'].forEach(reference => {
				description += `<li><a href="${reference}" target="_blank">${reference}</a></li>`;
			});
			description += '</ul></div>';
		}
		if(vuln_obj['curl_command']) {
			description += `<br><a class="mt-2" data-bs-toggle="collapse" href="#curl_command_${vuln_obj['id']}" aria-expanded="false" aria-controls="curl_command_${vuln_obj['id']}">CURL command <i class="fe-terminal"></i></a>`;
			description += `<div class="collapse" id="curl_command_${vuln_obj['id']}"><ul>`;
			description += `<li><code>${split_into_lines(htmlEncode(vuln_obj['curl_command']), 30)}</code></li>`;
			description += '</ul></div>';
		}
		var action_icon = vuln_obj['hackerone_report_id'] ? '' : `
		<div class="btn-group mb-2 dropstart">
		<a href="#" class="text-dark dropdown-toggle float-end" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
		<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-more-horizontal"><circle cx="12" cy="12" r="1"></circle><circle cx="19" cy="12" r="1"></circle><circle cx="5" cy="12" r="1"></circle></svg>
		</a>
		<div class="dropdown-menu" style="">
		<a class="dropdown-item" href="javascript:report_hackerone(${vuln_obj['id']}, '${vuln_obj['severity']}');">Report to Hackerone</a>
		</div>
		</div>`;
		$('#vuln_tbody').append(`
			<tr>
			<td>${vuln_type}</td>
			<td>${vuln_title}</td>
			<td class="text-center">${get_severity_badge(vuln_obj['severity'])}</td>
			<td class="text-center">${cvss_score}</td>
			<td>${cve_cwe_badge}</td>
			<td>${http_url}</td>
			<td>${description}</td>
			<td>${action_icon}</td>
			</tr>
		`);
	}
	$("#vulnerability-modal-datatable").DataTable({
		"oLanguage": {
			"oPaginate": {
				"sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>',
				"sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>'
			},
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"dom": "<'dt--top-section'<'row'<'col-12 col-sm-6 d-flex justify-content-sm-start justify-content-center'f><'col-12 col-sm-6 d-flex justify-content-sm-end justify-content-center'l>>>" + "<'table-responsive'tr>" + "<'dt--bottom-section d-sm-flex justify-content-sm-between text-center'<'dt--pages-count  mb-sm-0 mb-3'i><'dt--pagination'p>>",
		"order": [
			[5, "desc"]
		],
		drawCallback: function() {
			$(".dataTables_paginate > .pagination").addClass("pagination-rounded")
		}
	});
}

function render_directories_in_xl_modal(directory_count, subdomain_name, result){
	$('#xl-modal-content').append(`<h5> ${directory_count} Directories Discovered on subdomain ${subdomain_name}</h5>`);
	$('#xl-modal-content').append(`
		<div class="">
		<table id="directory-modal-datatable" class="table dt-responsive nowrap w-100">
		<thead>
		<tr>
		<th>Directory</th>
		<th class="text-center">HTTP Status</th>
		<th>Content Length</th>
		<th>Lines</th>
		<th>Words</th>
		</tr>
		</thead>
		<tbody id="directory_tbody">
		</tbody>
		</table>
		</div>
	`);
	$('#directory_tbody').empty();
	for(var dir_obj in result) {
		var dir = result[dir_obj];
		$('#directory_tbody').append(`
			<tr>
			<td><a href="${dir.url}" target="_blank">${dir.name}</a></td>
			<td class="text-center">${get_http_status_badge(dir.http_status)}</td>
			<td>${dir.length}</td>
			<td>${dir.lines}</td>
			<td>${dir.words}</td>
			</tr>
		`);
	}
	var interesting_keywords_array = [];
	var dir_modal_table = $("#directory-modal-datatable").DataTable({
		"oLanguage": {
			"oPaginate": {
				"sPrevious": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-left"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>',
				"sNext": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-arrow-right"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>'
			},
			"sInfo": "Showing page _PAGE_ of _PAGES_",
			"sSearch": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-search"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
			"sSearchPlaceholder": "Search...",
			"sLengthMenu": "Results :  _MENU_",
		},
		"dom": "<'dt--top-section'<'row'<'col-12 col-sm-6 d-flex justify-content-sm-start justify-content-center'f><'col-12 col-sm-6 d-flex justify-content-sm-end justify-content-center'l>>>" + "<'table-responsive'tr>" + "<'dt--bottom-section d-sm-flex justify-content-sm-between text-center'<'dt--pages-count  mb-sm-0 mb-3'i><'dt--pagination'p>>",
		"order": [
			[2, "desc"]
		],
		drawCallback: function() {
			$(".dataTables_paginate > .pagination").addClass("pagination-rounded");
		}
	});
	// TODO: Find interetsing dirs
	// fetch("/api/listInterestingKeywords")
	// .then(response => {
	// 	return response.json();
	// })
	// .then(data => {
	// 	interesting_keywords_array = data;
	// 	dir_modal_table.rows().every(function(){
	// 		console.log(this.data());
	// 	});
	// });
}


function get_and_render_subscan_history(subdomain_id, subdomain_name){
	// This function displays the subscan history in a modal for any particular subdomain
	var data = {'subdomain_id': subdomain_id};

	fetch('/api/listSubScans/?format=json', {
		method: 'POST',
		credentials: "same-origin",
		body: JSON.stringify(data),
		headers: {
			"X-CSRFToken": getCookie("csrftoken"),
			"Content-Type": 'application/json',
		}
	}).then(function(response) {
		return response.json();
	}).then(function(data) {
		console.log(data);
		if (data['status']) {
			$('#modal_title').html('Subscan History for subdomain ' + subdomain_name);
			$('#modal-content').empty();
			$('#modal-content').append(`<div id="subscan_history_table"></div>`);

			$('#subscan_history_table').empty();

			for (var result in data['results']) {

				var result_obj = data['results'][result];


				var task_name = get_task_name(result_obj);

				if (result_obj.status == 0 ) {
					color = 'danger';
					bg_color = 'bg-soft-danger';
					status_badge = '<span class="float-end badge bg-danger">Failed</span>';
				}
				else if (result_obj.status == 3) {
					color = 'danger';
					bg_color = 'bg-soft-danger';
					status_badge = '<span class="float-end badge bg-danger">Aborted</span>';
				}
				else if (result_obj.status == 2){
					color = 'success';
					bg_color = 'bg-soft-success';
					status_badge = '<span class="float-end badge bg-success">Task Completed</span>';
				}

				$('#subscan_history_table').append(`
					<div class="card border-${color} border mini-card">
					<a href="#" class="text-reset item-hovered" onclick="show_subscan_results(${result_obj['id']})">
					<div class="card-header ${bg_color} text-${color} mini-card-header">
					${task_name} on <b>${result_obj.subdomain_name}</b>
					</div>
					<div class="card-body mini-card-body">
					<p class="card-text">
					${status_badge}
					<span class="">
					Task Completed ${result_obj.completed_ago} ago
					</span>
					Took ${result_obj.time_taken}
					</p>
					</div>
					</a>
					</div>
					`);
			}


			$('#modal_dialog').modal('show');
		}
	});
}

function fetch_whois(domain_name, save_db){
	// this function will fetch WHOIS record for any subdomain and also display
	// snackbar once whois is fetched
	var url = `/api/tools/whois/?format=json&ip_domain=${domain_name}`;
	if (save_db) {
		url += '&save_db';
	}
	$('[data-toggle="tooltip"]').tooltip('hide');
	Snackbar.show({
		text: 'Fetching WHOIS...',
		pos: 'top-right',
		duration: 1500,
	});
	$("#whois_not_fetched_alert").hide();
	$("#whois_fetching_alert").show();
	fetch(``, {}).then(res => res.json())
	.then(function (response) {
		$("#whois_fetching_alert").hide();
		document.getElementById('domain_age').innerHTML = response['domain']['domain_age'] + ' ' + response['domain']['date_created'];
		document.getElementById('ip_address').innerHTML = response['domain']['ip_address'];
		document.getElementById('ip_geolocation').innerHTML = response['domain']['geolocation'];

		document.getElementById('registrant_name').innerHTML = response['registrant']['name'];
		console.log(response['registrant']['organization'])
		document.getElementById('registrant_organization').innerHTML = response['registrant']['organization'] ? response['registrant']['organization'] : ' ';
		document.getElementById('registrant_address').innerHTML = response['registrant']['address'] + ' ' + response['registrant']['city'] + ' ' + response['registrant']['state'] + ' ' + response['registrant']['country'];
		document.getElementById('registrant_phone_numbers').innerHTML = response['registrant']['tel'];
		document.getElementById('registrant_fax').innerHTML = response['registrant']['fax'];

		Snackbar.show({
			text: 'Whois Fetched...',
			pos: 'top-right',
			duration: 3000
		});

		$("#whois_fetched_alert").show();

		$("#whois_fetched_alert").fadeTo(2000, 500).slideUp(1500, function(){
			$("#whois_fetched_alert").slideUp(500);
		});

	});
}

function get_target_whois(domain_name){
	// this function will fetch whois from db, if not fetched, will make a fresh
	// query and will display whois on a modal
	var url = `/api/tools/whois/?format=json&ip_domain=${domain_name}&fetch_from_db`

	Swal.fire({
		title: `Fetching WHOIS details for ${domain_name}...`
	});
	swal.showLoading();
	fetch(url, {
		method: 'GET',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken"),
			'Content-Type': 'application/json'
		},
	}).then(response => response.json()).then(function(response) {
		console.log(response);
		if (response.status) {
			swal.close();
			display_whois_on_modal(response);
		}
		else{
			fetch(`/api/tools/whois/?format=json&ip_domain=${domain_name}&save_db`, {
				method: 'GET',
				credentials: "same-origin",
				headers: {
					"X-CSRFToken": getCookie("csrftoken"),
					'Content-Type': 'application/json'
				},
			}).then(response => response.json()).then(function(response) {
				console.log(response);
				if (response.status) {
					swal.close();
					display_whois_on_modal(response);
				}
				else{
					Swal.fire({
						title: 'Oops!',
						text: `reNgine could not fetch WHOIS records for ${domain_name}!`,
						icon: 'error'
					});
				}
			});
		}
	});
}

function get_domain_whois(domain_name){
	// this function will get whois for domains that are not targets, this will
	// not store whois into db nor create target
	var url = `/api/tools/whois/?format=json&ip_domain=${domain_name}`
	Swal.fire({
		title: `Fetching WHOIS details for ${domain_name}...`
	});
	swal.showLoading();
	fetch(url, {
		method: 'GET',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken"),
			'Content-Type': 'application/json'
		},
	}).then(response => response.json()).then(function(response) {
		console.log(response);
		if (response.status) {
			swal.close();
			display_whois_on_modal(response);
		}
		else{
			Swal.fire({
				title: 'Oops!',
				text: `reNgine could not fetch WHOIS records for ${domain_name}! ${response['message']}`,
				icon: 'error'
			});
		}
	});
}

function display_whois_on_modal(response){
	// this function will display whois data on modal, should be followed after get_domain_whois()
	$('#modal_dialog').modal('show');
	$('#modal-content').empty();
	$("#modal-footer").empty();

	console.log(response);

	content = `<div class="row mt-3">
		<div class="col-sm-3">
			<div class="nav flex-column nav-pills nav-pills-tab" id="v-pills-tab" role="tablist" aria-orientation="vertical">
				<a class="nav-link active show mb-1" id="v-pills-domain-tab" data-bs-toggle="pill" href="#v-pills-domain" role="tab" aria-controls="v-pills-domain-tab" aria-selected="true">Domain info</a>
				<a class="nav-link mb-1" id="v-pills-whois-tab" data-bs-toggle="pill" href="#v-pills-whois" role="tab" aria-controls="v-pills-whois" aria-selected="false">Whois</a>
				<a class="nav-link mb-1" id="v-pills-nameserver-tab" data-bs-toggle="pill" href="#v-pills-nameserver" role="tab" aria-controls="v-pills-nameserver"aria-selected="false">Nameservers</a>
				<a class="nav-link mb-1" id="v-pills-history-tab" data-bs-toggle="pill" href="#v-pills-history" role="tab" aria-controls="v-pills-history"aria-selected="false">NS History</a>
				<a class="nav-link mb-1" id="v-pills-related-tab" data-bs-toggle="pill" href="#v-pills-related" role="tab" aria-controls="v-pills-related"aria-selected="false">Related Domains`;

	if (response['related_domains'].length) {
		content += `<span class="badge badge-soft-info float-end">${response['related_domains'].length}</span>`
	}

	content += `</a>
			</div>
		</div> <!-- end col-->
		<div class="col-sm-9">
			<div class="tab-content pt-0">
				<div class="tab-pane fade active show" id="v-pills-domain" role="tabpanel" aria-labelledby="v-pills-domain-tab" data-simplebar style="max-height: 300px; min-height: 300px;">
					<h4 class="header-title">Domain Information</h4>
					<table class="domain_details_table table table-hover table-borderless">
						<tr style="display: none">
							<th>&nbsp;</th>
							<th>&nbsp;</th>
						</tr>
						<tr>
							<td>Domain Name</td>
							<td>${response['ip_domain'] ? response['ip_domain']: "-"}</td>
						</tr>
						<tr>
							<td>Domain age</td>
							<td>${response['domain']['domain_age'] ? response['domain']['domain_age']: "-"}</td>
						</tr>
						<tr>
							<td>IP Address</td>
							<td>${response['domain']['ip_address'] ? response['domain']['ip_address']: "-" }</td>
						</tr>
						<tr>
							<td>IP Geolocation</td>
							<td>
							${response['domain']['geolocation_iso'] ? `<img src="https://domainbigdata.com/img/flags-iso/flat/24/${response['domain']['geolocation_iso']}.png" alt="${response['domain']['geolocation_iso']}">` : ""}
							&nbsp;&nbsp;${response['domain']['geolocation'] ? response['domain']['geolocation'] : "-"}</td>
						</tr>
					</table>
					<h4 class="header-title mt-3">Registrant Information</h4>
					<table class="domain_details_table table table-hover table-borderless">
						<tr style="display: none">
							<th>&nbsp;</th>
							<th>&nbsp;</th>
						</tr>
						<tr>
							<td>Name</td>
							<td>${response['registrant']['name'] ? response['registrant']['name']: "-"}</td>
						</tr>
						<tr>
							<td>Email</td>
							<td>${response['registrant']['email'] ? response['registrant']['email']: "-"}</td>
						</tr>
						<tr>
							<td>Organization</td>
							<td>${response['registrant']['organization'] ? response['registrant']['organization']: "-"}</td>
						</tr>
						<tr>
							<td>Address</td>
							<td>${response['registrant']['address'] ? response['registrant']['address']: "-"}</td>
						</tr>
						<tr>
							<td>Phone Numbers</td>
							<td>${response['registrant']['tel'] ? response['registrant']['tel']: "-"}</td>
						</tr>
						<tr>
							<td>Fax</td>
							<td>${response['registrant']['fax'] ? response['registrant']['fax']: "-"}</td>
						</tr>
					</table>
				</div>
				<div class="tab-pane fade" id="v-pills-whois" role="tabpanel" aria-labelledby="v-pills-whois-tab">
					<pre data-simplebar style="max-height: 310px; min-height: 310px;">${response['whois'] ? response['whois'] : "No Whois Data found!"}</pre>
				</div>
				<div class="tab-pane fade" id="v-pills-history" role="tabpanel" aria-labelledby="v-pills-history-tab" data-simplebar style="max-height: 300px; min-height: 300px;">`;
				if (response['nameserver']['history'].length) {
					content += `<table class="table table-striped mb-0">
							<thead class="table-dark">
								<td>Date</td>
								<td>Action</td>
								<td>NameServer</td>
							</thead>
							<tbody>`;

					for (var history in response['nameserver']['history']) {
						var obj = response['nameserver']['history'][history];
						content += `
						<tr>
							<td>${obj['date']? obj['date'] : '-'}</td>
							<td>${obj['action']? obj['action'] : '-'}</td>
							<td>${obj['server']? obj['server'] : '-'}</td>
						</tr>
						`;
					}

					content += `</tbody></table>`
				}
				else{
					content += 'No DNS history records found.';
				}
				content += `
				</div>
				<div class="tab-pane fade" id="v-pills-nameserver" role="tabpanel" aria-labelledby="v-pills-nameserver-tab" data-simplebar style="max-height: 300px; min-height: 300px;">`;

				if (response['nameserver']['records'].length) {
					content += `<table class="table table-striped mb-0">
						<thead class="table-dark">
							<td>Type</td>
							<td>Hostname</td>
							<td>Address</td>
							<td>TTL</td>
							<td>Class</td>
							<td>Preference</td>
						</thead>
						<tbody>`;

						for (var record in response['nameserver']['records']) {
							var obj = response['nameserver']['records'][record];
							content += `
							<tr>
								<td><span class="badge badge-soft-primary me-1 ms-1">${obj['type']? obj['type'] : '-'}</span</td>
								<td>${obj['hostname']? obj['hostname'] : '-'}</td>
								<td>${obj['address']? obj['address'] : '-'}</td>
								<td>${obj['ttl']? obj['ttl'] : '-'}</td>
								<td>${obj['ns_class']? obj['ns_class'] : '-'}</td>
								<td>${obj['preference']? obj['preference'] : '-'}</td>
							</tr>`;
						}
						content += `</tbody></table>`;
				}
				else{
					content += `No DNS history records found.`;
				}

				content += `
				</div>
				<div class="tab-pane fade" id="v-pills-related" role="tabpanel" aria-labelledby="v-pills-related-tab" data-simplebar style="max-height: 300px; min-height: 300px;">
				`;

				for (var domain in response['related_domains']) {
					var domain_obj = response['related_domains'][domain];
					content += `<span class="btn btn-primary rounded-pill waves-effect waves-light me-1 mb-1" data-toggle="tooltip" title="Add ${domain_obj} as target." onclick="add_target('${domain_obj}')">${domain_obj}</span>`
				}
				content += `
				</div>
			</div>
		</div>
	</div>`;

	$('#modal-content').append(content);

}

function show_quick_add_target_modal(){
	// this function will display the modal to add  target
	$('#modal_title').html('Add target');
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-3">
			<label for="target_name_modal" class="form-label">Target Name</label>
			<input class="form-control" type="text" id="target_name_modal" required="" placeholder="yourdomain.com">
		</div>

		<div class="mb-3">
			<label for="target_description_modal" class="form-label">Description (Optional)</label>
			<input class="form-control" type="text" id="target_description_modal" required="" placeholder="Target Description">
		</div>

		<div class="mb-3">
			<label for="h1_handle_modal" class="form-label">Hackerone Target Team Handle (Optional)</label>
			<input class="form-control" type="text" id="h1_handle_modal" placeholder="hackerone.com/team_handle, Only enter team_handle after /">
		</div>

		<div class="mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="add_target_modal" onclick="add_quick_target()">Add Target</button>
		</div>

	`);
	$('#modal_dialog').modal('show');
}

function add_quick_target(){
	// this function will be a onclick for add target button on add_target modal
	$('#modal_dialog').modal('hide');
	var domain_name = $('#target_name_modal').val();
	var description = $('#target_description_modal').val();
	var h1_handle = $('#h1_handle_modal').val();

	const data = {
			'domain_name': domain_name,
			'h1_team_handle': h1_handle,
			'description': description
	};
	add_target(domain_name, h1_handle=h1_handle, description=description);
}


function add_target(domain_name, h1_handle=null, description=null){
	// this function will add domain_name as target
	const add_api = '/api/add/target/?format=json';
	const data = {
			'domain_name': domain_name,
			'h1_team_handle': h1_handle,
			'description': description
		};

	swal.queue([{
		title: 'Add Target',
		text: `Would you like to add ${domain_name} as target?`,
		icon: 'info',
		showCancelButton: true,
		confirmButtonText: 'Add Target',
		padding: '2em',
		showLoaderOnConfirm: true,
		preConfirm: function() {
			return fetch(add_api, {
				method: 'POST',
				credentials: "same-origin",
				headers: {
					'X-CSRFToken': getCookie("csrftoken"),
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(data)
			}).then(function(response) {
				return response.json();
			}).then(function(data) {
				if (data.status) {

					swal.queue([{
						title: 'Target Successfully added!',
						text: `Do you wish to initiate the scan on new target?`,
						icon: 'success',
						showCancelButton: true,
						confirmButtonText: 'Initiate Scan',
						padding: '2em',
						showLoaderOnConfirm: true,
						preConfirm: function() {
							window.location = `/scan/start/${data.domain_id}`;
						}
					}]);
				}
				else{
					swal.insertQueueStep({
						icon: 'error',
						title: data.message
					});
				}
			}).catch(function() {
				swal.insertQueueStep({
					icon: 'error',
					title: 'Oops! Unable to delete the scan history!'
				});
			})
		}
	}]);
}
