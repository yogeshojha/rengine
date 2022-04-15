function show_whois_lookup_modal(){
	$('#modal_title').html('WHOIS Lookup');
	$('#modal-content').empty();
	$('#modal-content').append(`
		<div class="mb-3">
			<label for="target_name_modal" class="form-label">Domain Name/IP Address</label>
			<input class="form-control" type="text" id="whois_domain_name" required="" placeholder="yourdomain.com">
		</div>
		<div class="mb-3 text-center">
			<button class="btn btn-primary float-end" type="submit" id="search_whois_toolbox_btn" onclick="toolbox_lookup_whois()">Search</button>
		</div>
	`);
	$('#modal_dialog').modal('show');
}

function toolbox_lookup_whois(){
	var domain = document.getElementById("whois_domain_name").value;
	if (domain) {
		get_domain_whois(domain);
	}
	else{
		swal.fire("Error!", 'Please enter the domain/IP Address!', "warning", {
			button: "Okay",
		});
	}
}
