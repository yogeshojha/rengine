function show_whois_lookup_modal(){
	$('#modal_title').html(gettext('WHOIS Lookup'));
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-3">
			<label for="whois_domain_name" class="form-label">` + gettext("Domain Name/IP Address") + `</label>
			<input class="form-control" type="text" id="whois_domain_name" required="" placeholder="` + gettext("yourdomain.com") + `">
		</div>
		<div class="mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="search_whois_toolbox_btn" onclick="toolbox_lookup_whois()">` + gettext("Search Whois") + `</button>
		</div>
	`);
	$('#modal_dialog').modal('show');
}

function toolbox_lookup_whois(){
	var domain = document.getElementById("whois_domain_name").value;
	if (domain) {
		get_domain_whois(domain, show_add_target_btn=true);
	}
	else{
		swal.fire(gettext("Error!"), gettext('Please enter the domain/IP Address!'), "warning", {
			button: "Okay",
		});
	}
}


function cms_detector(){
	$('#modal_title').html(gettext('Detect CMS'));
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-1">
			<label for="cms_detector_input_url" class="form-label">` + gettext("HTTP URL/Domain Name") + `</label>
			<input class="form-control" type="text" id="cms_detector_input_url" required="" placeholder="` + gettext("https://yourdomain.com") + `">
		</div>
		<small class="mb-3 float-end text-muted">` + gettext(`(reNgine uses <a href="https://github.com/Tuhinshubhra/CMSeeK" target="_blank">CMSeeK</a> to detect CMS.)`) + `</span>
		<div class="mt-3 mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="detect_cms_submit_btn">` + gettext("Detect CMS") + `</button>
		</div>
	`);
	$('#modal_dialog').modal('show');
}


$(document).on('click', '#detect_cms_submit_btn', function(){
	var url = document.getElementById("cms_detector_input_url").value;
	if (!validURL(url)) {
		swal.fire(gettext("Error!"), gettext('Please enter a valid URL!'), "warning", {
			button: gettext("Okay"),
		});
		return;
	}
	cms_detector_api_call(url);
});


function cms_detector_api_call(url){
	var api_url = `/api/tools/cms_detector/?format=json&url=${url}`
	Swal.fire({
		title: gettext(`Detecting CMS`),
		text: interpolate(`reNgine is detecting CMS on %(url)s and this may take a while. Please wait...`, {url: url}, true),
		allowOutsideClick: false
	});
	swal.showLoading();
	fetch(api_url, {
		method: 'GET',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken"),
			"Content-Type": "application/json"
		},
	}).then(response => response.json()).then(function(response) {
		if (response.status) {
			swal.close();
			$('#modal_title').html(interpolate('CMS Details for %(url)s', {url: url}, true));
			$('#modal-content').empty();

			content = `
				<div class="d-flex align-items-start mb-3">
					<img class="d-flex me-3 rounded-circle avatar-lg" src="${response.cms_url}/favicon.ico" alt="${response.cms_name}">
					<div class="w-100">
						<h4 class="mt-0 mb-1">${response.cms_name}</h4>
						<a href="${response.cms_url}" class="btn btn-xs btn-primary" target="_blank">` + gettext("Visit CMS") + `</a>
					</div>
				</div>

				<h5 class="mb-3 mt-4 text-uppercase bg-light p-2"><i class="fe-info"></i>&nbsp;` + gettext("CMS Details") + `</h5>
				<div class="">
					<h4 class="font-13 text-muted text-uppercase">` + gettext("CMS Name :") + `</h4>
					<p class="mb-3">${response.cms_name}</p>

					<h4 class="font-13 text-muted text-uppercase mb-1">` + gettext("CMS URL :") + `</h4>
					<p class="mb-3"><a href="${response.cms_url}">${response.cms_url}</a></p>

					<h4 class="font-13 text-muted text-uppercase mb-1">` + gettext("Detection Method :") + `</h4>
					<p class="mb-3">${response.detection_param}</p>

					<h4 class="font-13 text-muted text-uppercase mb-1">` + gettext("URL :") + `</h4>
					<p class="mb-3">
					<small class="text-muted">` + gettext("(Includes redirected URL)") + `</small><br>
					<a href="${response.url}" target="_blank">${response.url}</a>
					</p>`;

			let infos = {
				wp_linkable: [
					{ name: "wp_license", desc: gettext("Wordpress License") },
					{ name: "wp_readme_file", desc: gettext("Wordpress Readme File") },
					{ name: "wp_uploads_directory", desc: gettext("Wordpress Uploads Directory") }
				],
				wp_enum: [
					{name: "wp_users", desc: gettext("Wordpress Users") },
					{name: "wp_version", desc: gettext("Wordpress Version") },
					{name: "wp_plugins", desc: gettext("Wordpress Plugins")},
					{name: "wp_themes", desc: gettext("Wordpress Themes")}
				],
				joomla_enum: [
					{ name: "joomla_version", desc: gettext("Joomla Version") },
					{ name: "joomla_debug_mode", desc: gettext("Joomla Debug Mode") }
				],
				joomla_linkable: [
					{ name: "joomla_readme_file", desc: gettext("Joomla Readme File") },
					{ name: "joomla_backup_files", desc: gettext("Joomla Backup Files") },
					{ name: "directory_listing", desc: gettext("Joomla Directory Listing") },
					{ name: "joomla_config_files", desc: gettext("Joomla Config Files") },
					{ name: "user_registration_url", desc: gettext("Joomla User Registration") },
				]
			}

			for (const obj of infos.wp_linkable) {
				if (response[obj.name]) {
					content += `<h4 class="font-13 text-muted text-uppercase mb-1">` + obj.desc + `</h4>
					<p class="mb-3">
					<a href="${response[obj.name]}" target="_blank">${response[obj.name]}</a>
					</p>`;
				}
			}
			
			for (const obj of infos.wp_enum) {
				if (response[obj.name]) {
					content += `<h4 class="font-13 text-muted text-uppercase mb-1">` + obj.desc + `</h4>
					<p class="mb-3">
					${response[obj.name]}
					</p>`;
				}
			}
			
			for (const obj of infos.joomla_enum) {
				if (response[obj.name]) {
					content += `<h4 class="font-13 text-muted text-uppercase mb-1">` + obj.desc + `</h4>
					<p class="mb-3">
					${response[obj.name]}
					</p>`;
				}
			}

			for (const obj of infos.joomla_linkable) {
				if (response[obj.name]) {
					content += `<h4 class="font-13 text-muted text-uppercase mb-1">` + obj.desc + `</h4>
					<p class="mb-3">
					<a href="${response[obj.name]}" target="_blank">${response[obj.name]}</a>
					</p>`;
				}
			}

			content += `<br><a class="mt-2" data-bs-toggle="collapse" href="#response_json" aria-expanded="false" aria-controls="response_json">` + gettext("Response Json") + ` <i class="fe-terminal"></i></a>`;
			content += `<div class="collapse" id="response_json"><ul>`;
			content += `<pre><code>${htmlEncode(JSON.stringify(response, null, 4))}</code></pre>`;
			content += '</ul></div>';


			content += '</div>'

			$('#modal-content').append(content);
			$('#modal_dialog').modal('show');
		} else {
			Swal.fire({
				title: gettext('Oops!'),
				text: `${response['message']}`,
				icon: 'error'
			});
		}
	});
}


function toolbox_cve_detail(){
	$('#modal_title').html(gettext('CVE Details Lookup'));
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-1">
			<label for="cve_id" class="form-label">` + gettext("CVE ID") + `</label>
			<input class="form-control" type="text" id="cve_id" required="" placeholder="` + gettext("CVE-XXXX-XXXX") + `">
		</div>
		<div class="mt-3 mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="cve_detail_submit_btn">` + gettext("Lookup CVE") + `</button>
		</div>
	`);
	$('#modal_dialog').modal('show');
}



$(document).on('click', '#cve_detail_submit_btn', function(){
	var cve_id = document.getElementById("cve_id").value;
	if (cve_id) {
		get_and_render_cve_details(cve_id);
	}
	else{
		swal.fire(gettext("Error!"), gettext('Please enter CVE ID!'), "warning", {
			button: "Okay",
		});
	}
});


function toolbox_waf_detector(){
	$('#modal_title').html(gettext('WAF Detector'));
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-1">
			<label for="cms_detector_input_url" class="form-label">`+ gettext("HTTP URL/Domain Name") + `</label>
			<input class="form-control" type="text" id="waf_detector_input_url" required="" placeholder="` + gettext("https://yourdomain.com") + `">
		</div>
		<small class="mb-3 float-end text-muted">` + gettext(`(reNgine uses <a href="https://github.com/EnableSecurity/wafw00f" target="_blank">wafw00f</a> to detect WAF.)`) + `</span>
		<div class="mt-3 mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="detect_waf_submit_btn">` + gettext("Detect WAF") + `</button>
		</div>
	`);
	$('#modal_dialog').modal('show');
}


$(document).on('click', '#detect_waf_submit_btn', function(){
	var url = document.getElementById("waf_detector_input_url").value;
	if (!validURL(url)) {
		swal.fire(gettext("Error!"), gettext('Please enter a valid URL!'), "warning", {
			button: "Okay",
		});
		return;
	}
	waf_detector_api_call(url);
});


function waf_detector_api_call(url){
	var api_url = `/api/tools/waf_detector/?format=json&url=${url}`
	Swal.fire({
		title: gettext(`Detecting WAF`),
		text: interpolate(`reNgine is detecting WAF on %(url)s and this may take a while. Please wait...`, {url: url}, true),
		allowOutsideClick: false
	});
	swal.showLoading();
	fetch(api_url, {
		method: 'GET',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken"),
			"Content-Type": "application/json"
		},
	}).then(response => response.json()).then(function(response) {
		if (response.status) {
			swal.close()
			Swal.fire({
				title: 'WAF Detected!',
				text: `${url} is running ${response.results}`,
				icon: 'info'
			});
		} else {
			Swal.fire({
				title: 'Oops!',
				text: `${response['message']}`,
				icon: 'error'
			});
		}
	});
}
