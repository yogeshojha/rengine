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
