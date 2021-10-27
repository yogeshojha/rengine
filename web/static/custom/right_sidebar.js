function getScanStatusSidebar(reload) {
  $.getJSON('/api/scan_status', function(data) {
    $('#currently_scanning').empty();
    $('#recently_completed_scans').empty();
    $('#upcoming_scans').empty();

    if (data['scanning'].length > 0){
      $('#current_scan_counter').html(data['scanning'].length);
      $('#current_scan_count').html(`${data['scanning'].length} Scans Currently Running`)
      for (var scan in data['scanning']) {
        scan_object = data['scanning'][scan];
        $('#currently_scanning').append(`<a href="/scan/detail/${scan_object.id}" class="mt-2 text-reset item-hovered d-block p-2 bg-soft-info">
        <p class="text-dark mb-0">${scan_object.domain.name}<span class="float-end">${scan_object.current_progress}%</span></p>
        <p class="mb-0"><small>Started ${scan_object.elapsed_time} ago<small></p>
        <h5><span class="badge badge-soft-primary badge-scan_engine-type float-end">${scan_object.scan_type.engine_name}</span></h5>
        <h4 class="text-center">
        <span class="badge-subdomain-count badge badge-soft-info waves-effect waves-light">&nbsp;&nbsp;${scan_object.subdomain_count}&nbsp;&nbsp;</span>
        <span class="badge-endpoint-count badge badge-soft-primary waves-effect waves-light">&nbsp;&nbsp;${scan_object.endpoint_count}&nbsp;&nbsp;</span>
        <span class="badge-vuln-count badge badge-soft-danger waves-effect waves-light">&nbsp;&nbsp;${scan_object.vulnerability_count}&nbsp;&nbsp;</span></h4>
        <div class="progress mt-2" style="height: 4px;">
        <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" role="progressbar" aria-valuenow="${scan_object.current_progress}" aria-valuemin="0" aria-valuemax="100" style="width: ${scan_object.current_progress}%"></div>
        </div>
        </a>`);
      }
    }
    else{
      $('#currently_scanning').html(`<div class="alert alert-warning" role="alert">No Scans are currently running.</div>`);
    }

    if (data['recently_completed_scans'].length > 0){
      for (var scan in data['recently_completed_scans']) {
        scan_object = data['recently_completed_scans'][scan];
        if (scan_object.scan_status == 0 ) {
          bg_color = 'bg-soft-danger';
          status_badge = '<span class="float-end badge bg-danger">Failed</span>';
        }
        else if (scan_object.scan_status == 3) {
          bg_color = 'bg-soft-danger';
          status_badge = '<span class="float-end badge bg-danger">Aborted</span>';
        }
        else if (scan_object.scan_status == 2){
          bg_color = 'bg-soft-success';
          status_badge = '<span class="float-end badge bg-success">Scan Completed</span>';
        }

        $('#recently_completed_scans').append(`<a href="/scan/detail/${scan_object.id}" class="mt-2 text-reset item-hovered d-block p-2 ${bg_color}">
        <p class="text-dark mb-0">${scan_object.domain.name}${status_badge}</p>
        <p class="mb-0"><small>Scan Completed ${scan_object.completed_ago} ago<small></p>
        <h5><span class="badge badge-soft-primary badge-scan_engine-type float-end">${scan_object.scan_type.engine_name}</span></h5>
        <h4 class="text-center">
        <span class="badge-subdomain-count badge badge-soft-info waves-effect waves-light">&nbsp;&nbsp;${scan_object.subdomain_count}&nbsp;&nbsp;</span>
        <span class="badge-endpoint-count badge badge-soft-primary waves-effect waves-light">&nbsp;&nbsp;${scan_object.endpoint_count}&nbsp;&nbsp;</span>
        <span class="badge-vuln-count badge badge-soft-danger waves-effect waves-light">&nbsp;&nbsp;${scan_object.vulnerability_count}&nbsp;&nbsp;</span></h4>
        </a>`);
      }
    }
    else{
      $('#recently_completed_scans').html(`<div class="alert alert-info" role="alert">No scans has been recently completed.</div>`);
    }

    if (data['pending'].length > 0){
      $('#pending_scan_count').html(`${data['pending'].length} Scans Pending`)
      for (var scan in data['pending']) {
        scan_object = data['pending'][scan];
        $('#upcoming_scans').append(`<a class="mt-2 text-reset item-hovered d-block p-2 bg-soft-warning">
        <p class="text-dark mb-0">${scan_object.domain.name}</p>
        <h5><span class="badge badge-soft-primary badge-scan_engine-type">${scan_object.scan_type.engine_name}</span></h5>
        </a>`);
      }
    }
    else{
      $('#upcoming_scans').html(`<div class="alert alert-info" role="alert">No upcoming scans on Queue.</div>`);
    }
  }).done(function() {
    tippy('.badge-subdomain-count', {
      content: 'Subdomains',
    });
    tippy('.badge-endpoint-count', {
      content: 'Endpoints',
    });
    tippy('.badge-vuln-count', {
      content: 'Vulnerabilities',
    });
    tippy('.badge-scan_engine-type', {
      content: 'Scan Engine',
    });
    if(reload){
      Snackbar.show({
        text: 'Scan Status Reloaded.',
        pos: 'top-right',
        actionTextColor: '#42A5F5',
        duration: 1500
      });
    }
  });

}
