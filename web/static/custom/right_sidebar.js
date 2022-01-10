function getScanStatusSidebar(reload) {
  $.getJSON('/api/scan_status', function(data) {
    // main scans
    $('#currently_scanning').empty();
    $('#completed').empty();
    $('#upcoming_scans').empty();

    // subtasks
    $('#currently_running_tasks').empty();
    $('#completed_tasks').empty();
    $('#upcoming_tasks').empty();
    $('#current_task_count').empty();

    scans = data['scans'];
    tasks = data['tasks'];

    if (scans['scanning'].length > 0){
      $('#current_scan_counter').html(scans['scanning'].length);
      $('#current_scan_count').html(`${scans['scanning'].length} Scans Currently Running`)
      for (var scan in scans['scanning']) {
        scan_object = scans['scanning'][scan];
        $('#currently_scanning').append(`
          <div class="card border-primary border mb-2">
          <div class="card-header bg-soft-primary text-primary">
          ${scan_object.scan_type.engine_name} on ${scan_object.domain.name}
          <span class="badge badge-soft-primary float-end">
          ${scan_object.current_progress}%
          </span>
          </div>
          <div class="card-body mini-card-body">
          <p class="card-text">
          <span class="badge badge-soft-primary float-end scan_status">
          Scanning
          </span>
          <span class="">
          Started ${scan_object.elapsed_time} ago.
          </span>
          </p>
          <h4 class="">
          <span class="badge-subdomain-count badge badge-soft-info waves-effect waves-light">&nbsp;&nbsp;${scan_object.subdomain_count}&nbsp;&nbsp;</span>
          <span class="badge-endpoint-count badge badge-soft-primary waves-effect waves-light">&nbsp;&nbsp;${scan_object.endpoint_count}&nbsp;&nbsp;</span>
          <span class="badge-vuln-count badge badge-soft-danger waves-effect waves-light">&nbsp;&nbsp;${scan_object.vulnerability_count}&nbsp;&nbsp;</span>
          </h4>
          <div class="progress mt-2" style="height: 4px;">
          <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" role="progressbar" aria-valuenow="${scan_object.current_progress}" aria-valuemin="0" aria-valuemax="100" style="width: ${scan_object.current_progress}%"></div>
          </div>
          <a href="#" onclick="stop_scan('${scan_object.celery_id }', true, false)" class="btn btn-soft-danger waves-effect waves-light mt-1 float-end"><i class="fe-alert-triangle"></i> Abort</a>
          <a href="/scan/detail/${scan_object.id}" class="btn btn-soft-primary waves-effect waves-light mt-1 me-1 float-end">View</a>
          </div>
          </div>
          `);
        }
      }
      else{
        $('#currently_scanning').html(`<div class="alert alert-warning" role="alert">No Scans are currently running.</div>`);
      }

      if (scans['completed'].length > 0){
        for (var scan in scans['completed']) {
          scan_object = scans['completed'][scan];
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

          $('#completed').append(`<a href="/scan/detail/${scan_object.id}" class="mt-2 text-reset item-hovered d-block p-2 ${bg_color}">
          <p class="text-dark mb-0">${scan_object.domain.name}${status_badge}</p>
          <p class="mb-0"><small>Scan Completed ${scan_object.completed_ago} ago<small></p>
          <h5><span class="badge badge-soft-primary badge-scan_engine-type float-end">${scan_object.scan_type.engine_name}</span></h5>
          <h4 class="">
          <span class="badge-subdomain-count badge badge-soft-info waves-effect waves-light">&nbsp;&nbsp;${scan_object.subdomain_count}&nbsp;&nbsp;</span>
          <span class="badge-endpoint-count badge badge-soft-primary waves-effect waves-light">&nbsp;&nbsp;${scan_object.endpoint_count}&nbsp;&nbsp;</span>
          <span class="badge-vuln-count badge badge-soft-danger waves-effect waves-light">&nbsp;&nbsp;${scan_object.vulnerability_count}&nbsp;&nbsp;</span></h4>
          </a>`);
        }
      }
      else{
        $('#completed').html(`<div class="alert alert-info" role="alert">No scans have been recently completed.</div>`);
      }

      if (tasks['running'].length > 0){
        $('#current_task_count').html(`${tasks['running'].length} Tasks are currently running`)
        for (var task in tasks['running']) {
          task_object = tasks['running'][task];
          task_name = get_task_name(task_object);
          bg_color = 'bg-soft-info';
          status_badge = '<span class="float-end badge bg-info">Running</span>';

          $('#currently_running_tasks').append(`<a href="/scan/detail/${task_object.scan_history}" class="mt-2 text-reset item-hovered d-block p-2 ${bg_color}">
          <p class="text-dark mb-0"><b>${task_name}</b> on ${task_object.subdomain_name}${status_badge}</p>
          <p class="mb-0"><small>Running Since ${task_object.elapsed_time} ago<small></p>
          </a>`);
        }
      }
      else{
        $('#currently_running_tasks').html(`<div class="alert alert-info" role="alert">No tasks are currently running.</div>`);
      }

      if (tasks['completed'].length > 0){
        for (var task in tasks['completed']) {
          task_object = tasks['completed'][task];
          task_name = get_task_name(task_object);
          if (task_object.status == 0 ) {
            bg_color = 'bg-soft-danger';
            status_badge = '<span class="float-end badge bg-danger">Failed</span>';
          }
          else if (task_object.status == 3) {
            bg_color = 'bg-soft-danger';
            status_badge = '<span class="float-end badge bg-danger">Aborted</span>';
          }
          else if (task_object.status == 2){
            bg_color = 'bg-soft-success';
            status_badge = '<span class="float-end badge bg-success">Task Completed</span>';
          }

          $('#completed_tasks').append(`<a href="/scan/detail/${task_object.scan_history}" class="mt-2 text-reset item-hovered d-block p-2 ${bg_color}">
          <p class="text-dark mb-0"><b>${task_name}</b> on ${task_object.subdomain_name}${status_badge}</p>
          <p class="mb-0"><small>Task Completed ${task_object.completed_ago} ago<small></p>
          <p class="mb-0"><small>Took ${task_object.time_taken}<small></p>
          </a>`);
        }
      }
      else{
        $('#completed_tasks').html(`<div class="alert alert-info" role="alert">No tasks have been recently completed.</div>`);
      }

      if (tasks['pending'].length > 0){
        for (var task in tasks['pending']) {
          task_object = tasks['pending'][task];
          task_name = get_task_name(task_object);

          status_badge = '<span class="float-end badge bg-warning">Upcoming</span>';

          $('#upcoming_tasks').append(`<a href="/scan/detail/${task_object.scan_history}" class="mt-2 text-reset item-hovered d-block p-2 bg-soft-warning">
          <p class="text-dark mb-0"><b>${task_name}</b> on ${task_object.subdomain_name}${status_badge}</p>
          </a>`);
        }
      }
      else{
        $('#upcoming_tasks').html(`<div class="alert alert-info" role="alert">No upcoming tasks.</div>`);
      }

    }).done(function() {
      tippy('.scan_status', {
        content: 'Scan Status',
      });
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


  function get_task_name(data){
    if (data['dir_file_fuzz']) {
      return 'Directory Fuzzing';
    }
    else if (data['port_scan']) {
      return 'Port Scan';
    }
    else if (data['fetch_url']) {
      return 'Endpoint Gathering';
    }
    else if (data['vulnerability_scan']) {
      return 'Vulnerability Scan';
    }
    else if (data['osint']) {
      return 'OSINT';
    }
    else{
      return 'Unknown';
    }
  }
