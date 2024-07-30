function show_whois_lookup_modal(){
	$('#modal_title').html('WHOIS Lookup');
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-3">
			<label for="whois_domain_name" class="form-label">Domain Name/IP Address</label>
			<input class="form-control" type="text" id="whois_domain_name" required="" placeholder="yourdomain.com">
		</div>
		<div class="mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="search_whois_toolbox_btn" onclick="toolbox_lookup_whois()">Search Whois</button>
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
		swal.fire("Error!", 'Please enter the domain/IP Address!', "warning", {
			button: "Okay",
		});
	}
}


function cms_detector(){
	$('#modal_title').html('Detect CMS');
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-1">
			<label for="cms_detector_input_url" class="form-label">HTTP URL/Domain Name</label>
			<input class="form-control" type="text" id="cms_detector_input_url" required="" placeholder="https://yourdomain.com">
		</div>
		<small class="mb-3 float-end text-muted">(reNgine uses <a href="https://github.com/Tuhinshubhra/CMSeeK" target="_blank">CMSeeK</a> to detect CMS.)</span>
		<div class="mt-3 mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="detect_cms_submit_btn">Detect CMS</button>
		</div>
	`);
	$('#modal_dialog').modal('show');
}


$(document).on('click', '#detect_cms_submit_btn', function(){
	var url = document.getElementById("cms_detector_input_url").value;
	if (!validURL(url)) {
		swal.fire("Error!", 'Please enter a valid URL!', "warning", {
			button: "Okay",
		});
		return;
	}
	cms_detector_api_call(url);
});


function cms_detector_api_call(url){
	var api_url = `/api/tools/cms_detector/?format=json&url=${url}`
	Swal.fire({
		title: `Detecting CMS`,
		text: `reNgine is detecting CMS on ${url} and this may take a while. Please wait...`,
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
			$('#modal_title').html('CMS Details for ' + url);
			$('#modal-content').empty();

			content = `
				<div class="d-flex align-items-start mb-3">
					<img class="d-flex me-3 rounded-circle avatar-lg" src="${response.cms_url}/favicon.ico" alt="${response.cms_name}">
					<div class="w-100">
						<h4 class="mt-0 mb-1">${response.cms_name}</h4>
						<a href="${response.cms_url}" class="btn btn-xs btn-primary" target="_blank">Visit CMS</a>
					</div>
				</div>

				<h5 class="mb-3 mt-4 text-uppercase bg-light p-2"><i class="fe-info"></i>&nbsp;CMS Details</h5>
				<div class="">
					<h4 class="font-13 text-muted text-uppercase">CMS Name :</h4>
					<p class="mb-3">${response.cms_name}</p>

					<h4 class="font-13 text-muted text-uppercase mb-1">CMS URL :</h4>
					<p class="mb-3"><a href="${response.cms_url}">${response.cms_url}</a></p>

					<h4 class="font-13 text-muted text-uppercase mb-1">Detection Method :</h4>
					<p class="mb-3">${response.detection_param}</p>

					<h4 class="font-13 text-muted text-uppercase mb-1">URL :</h4>
					<p class="mb-3">
					<small class="text-muted">(Includes redirected URL)</small><br>
					<a href="${response.url}" target="_blank">${response.url}</a>
					</p>`;


			if (response.wp_license) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Wordpress License :</h4>
				<p class="mb-3">
				<a href="${response.wp_license}" target="_blank">${response.wp_license}</a>
				</p>`;
			}

			if (response.wp_readme_file) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Wordpress Readme file :</h4>
				<p class="mb-3">
				<a href="${response.wp_readme_file}" target="_blank">${response.wp_readme_file}</a>
				</p>`;
			}

			if (response.wp_uploads_directory) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Wordpress Uploads Directory :</h4>
				<p class="mb-3">
				<a href="${response.wp_uploads_directory}" target="_blank">${response.wp_uploads_directory}</a>
				</p>`;
			}

			if (response.wp_users) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Wordpress Users :</h4>
				<p class="mb-3">
				${response.wp_users}
				</p>`;
			}

			if (response.wp_version) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Wordpress Version :</h4>
				<p class="mb-3">
				${response.wp_version}
				</p>`;
			}

			if (response.wp_plugins) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Wordpress Plugins :</h4>
				<p class="mb-3">
				${response.wp_plugins}
				</p>`;
			}

			if (response.wp_themes) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Wordpress Themes :</h4>
				<p class="mb-3">
				${response.wp_themes}
				</p>`;
			}

			if (response.joomla_version) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Joomla Version :</h4>
				<p class="mb-3">
				${response.joomla_version}
				</p>`;
			}

			if (response.joomla_debug_mode) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Joomla Debug Mode :</h4>
				<p class="mb-3">
				${response.joomla_debug_mode}
				</p>`;
			}

			if (response.joomla_readme_file) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Joomla Readme File :</h4>
				<p class="mb-3">
				<a href="${response.joomla_readme_file}" target="_blank">${response.joomla_readme_file}</a>
				</p>`;
			}

			if (response.joomla_backup_files) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Joomla Backup Files :</h4>
				<p class="mb-3">
				<a href="${response.joomla_backup_files}" target="_blank">${response.joomla_backup_files}</a>
				</p>`;
			}

			if (response.directory_listing) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Joomla Directory Listing :</h4>
				<p class="mb-3">
				<a href="${response.directory_listing}" target="_blank">${response.directory_listing}</a>
				</p>`;
			}

			if (response.joomla_config_files) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Joomla Config Files :</h4>
				<p class="mb-3">
				<a href="${response.joomla_config_files}" target="_blank">${response.joomla_config_files}</a>
				</p>`;
			}

			if (response.user_registration_url) {
				content += `<h4 class="font-13 text-muted text-uppercase mb-1">Joomla User Registration :</h4>
				<p class="mb-3">
				<a href="${response.user_registration_url}" target="_blank">${response.user_registration_url}</a>
				</p>`;
			}

			content += `<br><a class="mt-2" data-bs-toggle="collapse" href="#response_json" aria-expanded="false" aria-controls="response_json">Response Json <i class="fe-terminal"></i></a>`;
			content += `<div class="collapse" id="response_json"><ul>`;
			content += `<pre><code>${htmlEncode(JSON.stringify(response, null, 4))}</code></pre>`;
			content += '</ul></div>';


			content += '</div>'

			$('#modal-content').append(content);
			$('#modal_dialog').modal('show');
		} else {
			Swal.fire({
				title: 'Oops!',
				text: `${response['message']}`,
				icon: 'error'
			});
		}
	});
}


function toolbox_cve_detail(){
	$('#modal_title').html('CVE Details Lookup');
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-1">
			<label for="cve_id" class="form-label">CVE ID</label>
			<input class="form-control" type="text" id="cve_id" required="" placeholder="CVE-XXXX-XXXX">
		</div>
		<div class="mt-3 mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="cve_detail_submit_btn">Lookup CVE</button>
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
		swal.fire("Error!", 'Please enter CVE ID!', "warning", {
			button: "Okay",
		});
	}
});


function toolbox_waf_detector(){
	$('#modal_title').html('WAF Detector');
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-1">
			<label for="cms_detector_input_url" class="form-label">HTTP URL/Domain Name</label>
			<input class="form-control" type="text" id="waf_detector_input_url" required="" placeholder="https://yourdomain.com">
		</div>
		<small class="mb-3 float-end text-muted">(reNgine uses <a href="https://github.com/EnableSecurity/wafw00f" target="_blank">wafw00f</a> to detect WAF.)</span>
		<div class="mt-3 mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="detect_waf_submit_btn">Detect WAF</button>
		</div>
	`);
	$('#modal_dialog').modal('show');
}


$(document).on('click', '#detect_waf_submit_btn', function(){
	var url = document.getElementById("waf_detector_input_url").value;
	if (!validURL(url)) {
		swal.fire("Error!", 'Please enter a valid URL!', "warning", {
			button: "Okay",
		});
		return;
	}
	waf_detector_api_call(url);
});


function waf_detector_api_call(url){
	var api_url = `/api/tools/waf_detector/?format=json&url=${url}`
	Swal.fire({
		title: `Detecting WAF`,
		text: `reNgine is detecting WAF on ${url} and this may take a while. Please wait...`,
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
