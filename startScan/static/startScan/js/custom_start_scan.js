function delete_scan(id, domain_name)
{
		const delAPI = "../delete/scan/"+id;
		swal.queue([{
				title: 'Are you sure you want to delete this scan history?',
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
								title: 'Oops! Unable to delete the scan history!'
							})
						})
				}
		}])
}

function stop_scan(celery_id){

		const stopAPI = "../stop/scan/"+celery_id;
		swal.queue([{
				title: 'Are you sure you want to stop this scan?',
				text: "You won't be able to revert this!",
				type: 'warning',
				showCancelButton: true,
				confirmButtonText: 'Stop',
				padding: '2em',
				showLoaderOnConfirm: true,
				preConfirm: function() {
					return fetch(stopAPI, {
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
								title: 'Oops! Unable to stop the scan'
							})
						})
				}
		}])
}

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
