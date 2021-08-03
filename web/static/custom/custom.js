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
