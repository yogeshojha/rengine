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
			<input class="form-control" type="text" id="cms_detector_input_url" required="" placeholder="https://yourdomain.com" value="https://bbanotes.com">
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
	if (url) {
		cms_detector_api_call(url)
	}
	else{
		swal.fire("Error!", 'Please enter a valid URL!', "warning", {
			button: "Okay",
		});
	}
});


function cms_detector_api_call(url){
	var api_url = `/api/tools/cms_detector/?format=json&url=${url}`
	Swal.fire({
		title: `Detecting CMS details on ${url}...`
	});
	$('.modal').modal('hide');
	swal.showLoading();
	fetch(api_url, {
		method: 'GET',
		credentials: "same-origin",
		headers: {
			"X-CSRFToken": getCookie("csrftoken"),
			"Content-Type": "application/json"
		},
	}).then(response => response.json()).then(function(response) {
		console.log(response);
		if (response.status) {
			swal.close();
			console.log(response);
			// display_whois_on_modal(response, show_add_target_btn=show_add_target_btn);
		} else {
			Swal.fire({
				title: 'Oops!',
				text: `${response['message']}`,
				icon: 'error'
			});
		}
	});
}
