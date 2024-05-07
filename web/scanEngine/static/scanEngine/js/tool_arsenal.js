function get_external_tool_latest_version(tool_id, tool_name){
  var current_version = document.getElementById(tool_name+'_current').textContent;
  console.log(current_version)
  if (current_version === 'Invalid version lookup command.' || current_version === 'Version Lookup command not provided.'){
    Swal.fire({
      title: gettext('Unable to fetch latest version!'),
      text: gettext(`Since the version lookup command is invalid, reNgine is not able to detect if there's a newer version. But you can still force download the latest version.`),
      icon: 'info',
      confirmButtonText: interpolate('Update %(toolName)s', {toolName: htmlEncode(tool_name)}, true),
    }).then((result) => {
      /* Read more about isConfirmed, isDenied below */
      if (result.isConfirmed) {
        Swal.fire({
          title: gettext('Downloading latest version...'),
          text: gettext('This may take a few minutes.'),
          allowOutsideClick: false
        });
        swal.showLoading();
        fetch('/api/tool/update/?tool_id=' + tool_id)
        .then(response => response.json())
        .then(function (response) {
          swal.close();
          if (response['status']) {
            Swal.fire({
              title: interpolate('%(toolName)s Updated!', {toolName: htmlEncode(tool_name)}, true),
              text: response['message'],
              icon: 'success',
            });
          }
          else{
            Swal.fire({
              title:  interpolate('%(toolName)s could not update!', {toolName: htmlEncode(tool_name)}, true),
              text: response['message'],
              icon: 'fail',
            });
          }
        });
      }
    });
  }
  else{
    Swal.fire({
      title: gettext('Finding latest version...'),
      allowOutsideClick: false
    });
    swal.showLoading();
    fetch('/api/github/tool/get_latest_releases/?tool_id=' + tool_id)
    .then(response => response.json())
    .then(function (response) {
      swal.close();
      if (response['message'] == 'RateLimited') {
        Swal.fire({
          showCancelButton: true,
          title: gettext('Error!'),
          text: gettext('Github API rate limit exceeded, we can not fetch the latest version number, please try again in an hour. But you can force download the latest version.'),
          icon: 'error',
          confirmButtonText: gettext('Force download'),
          cancelButtonText: gettext('Cancel'),
        }).then((result) => {
          if (result.isConfirmed) {
            Swal.fire({
              title: gettext('Downloading latest version...'),
              text: gettext('This may take a few minutes.'),
              allowOutsideClick: false
            });
            swal.showLoading();
            fetch('/api/tool/update/?tool_id=' + tool_id)
            .then(response => response.json())
            .then(function (response) {
              swal.close();
              if (response['status']) {
                Swal.fire({
                  title:  interpolate('%(toolName)s Updated!', {toolName: htmlEncode(tool_name)}, true),
                  text: response['message'],
                  icon: 'success',
                });
              }
              else{
                Swal.fire({
                  title:  interpolate('%(toolName)s could not update!', {toolName: htmlEncode(tool_name)}, true),
                  text: response['message'],
                  icon: 'fail',
                });
              }
            });
          }
        });;
      }
      else if (response['message'] == 'Tool Not found'){
        Swal.fire({
          title: gettext('Oops!'),
          text: gettext('We ran into an error! Please raise github request.'),
          icon: 'error'
        });
      }
      else if (response['message'] == 'Not Found'){
        Swal.fire({
          showCancelButton: true,
          title: gettext('Oops!'),
          text: gettext(`The github URL provided is not valid, or the project doesn't support releases. We are unable to check the latest version number, however, you can still force download the update`),
          icon: 'error',
          confirmButtonText: gettext('Force download'),
          cancelButtonText: gettext('Cancel'),
        }).then((result) => {
          /* Read more about isConfirmed, isDenied below */
          if (result.isConfirmed) {
            Swal.fire({
              title: gettext('Downloading latest version...'),
              text: gettext('This may take a few minutes.'),
              allowOutsideClick: false
            });
            swal.showLoading();
            fetch('/api/tool/update/?tool_id=' + tool_id)
            .then(response => response.json())
            .then(function (response) {
              swal.close();
              if (response['status']) {
                Swal.fire({
                  title:  interpolate('%(toolName)s Updated!', {toolName: htmlEncode(tool_name)}, true),
                  text: response['message'],
                  icon: 'success',
                });
              }
              else{
                Swal.fire({
                  title:  interpolate('%(toolName)s could not update!', {toolName: htmlEncode(tool_name)}, true),
                  text: response['message'],
                  icon: 'fail',
                });
              }
            });
          }
        });;
      }
      else{
        // match current version with installed version
        // sometimes version names can be v1.1.1 or 1.1.1, so for consistency
        // let's remove v from both
        var latest_version = response['name'];
        latest_version = latest_version.charAt(0) == 'v' ? latest_version.substring(1) : latest_version;

        if (current_version === 'Invalid version lookup command.' || current_version === 'Version Lookup command not provided.'){
          Swal.fire({
            title: gettext('Unable to fetch latest version!'),
            text: interpolate(`Since the version lookup command is invalid, reNgine is not able to detect if there's a newer version. But you can still force download the latest version. The latest version is %(latestVersion)s.`, {latestVersion: latest_version}, true),
            icon: 'info',
            confirmButtonText: interpolate('Update %(toolName)s', {toolName: htmlEncode(tool_name)}, true),
            cancelButtonText: gettext('Cancel'),
          }).then((result) => {
            /* Read more about isConfirmed, isDenied below */
            if (result.isConfirmed) {
              Swal.fire({
                title: gettext('Downloading latest version...'),
                text: gettext('This may take a few minutes.'),
                allowOutsideClick: false
              });
              swal.showLoading();
              fetch('/api/tool/update/?tool_id=' + tool_id)
              .then(response => response.json())
              .then(function (response) {
                swal.close();
                Swal.fire({
                  title:  interpolate('%(toolName)s Updated!', {toolName: htmlEncode(tool_name)}, true),
                  text: interpolate(`%(toolName)s has now been updated to v%(latestVersion)s!`, {toolName: htmlEncode(tool_name), latestVersion: latest_version}, true),
                  icon: 'success',
                });
              });
            }
          });
        }
        else{
          current_version = current_version.charAt(0) == 'v' ? current_version.substring(1) : current_version;
          if (current_version == latest_version) {
            Swal.fire({
              title: gettext('No Update available'),
              text: interpolate('Looks like the latest version of %(toolName)s is already installed.', {toolName: htmlEncode(tool_name)}, true),
              icon: 'info'
            });
          }
          else{
            // update available
            Swal.fire({
              title: interpolate('Update available! Version: %(latestVersion)s', {latestVersion: latest_version}, true),
              text: interpolate(`Your current version of %(toolName)s is v%(currentVersion)s, but latest version v%(latestVersion)s is available, please update!`, {toolName: htmlEncode(tool_name), currentVersion: current_version, latestVersion: latest_version}, true),
              icon: 'info',
              confirmButtonText: interpolate('Update %(toolName)s', {toolName: htmlEncode(tool_name)}, true),
            }).then((result) => {
              if (result.isConfirmed) {
                Swal.fire({
                  title: gettext('Downloading latest version...'),
                  text: gettext('This may take a few minutes.'),
                  allowOutsideClick: false
                });
                swal.showLoading();
                fetch('/api/tool/update/?tool_id=' + tool_id)
                .then(response => response.json())
                .then(function (response) {
                  swal.close();
                  Swal.fire({
                    title:  interpolate('%(toolName)s Updated!', {toolName: htmlEncode(tool_name)}, true),
                    text: interpolate(`%(toolName)s has now been updated to v%(lastestVersion)s!`, {toolName: htmlEncode(tool_name), lastestVersion: response.version}, true),
                    icon: 'success',
                  });
                });
              }
            });
          }
        }
      }
    });
  }
}

function get_external_tool_current_version(tool_id, id){
  fetch('/api/external/tool/get_current_release/?tool_id=' + tool_id)
  .then(response => response.json())
  .then(function (response){
    if (response['status']){
      version_number = response['version_number'].charAt(0) == 'v' || response['version_number'].charAt(0) == 'V' ? response['version_number'] : 'v' + response['version_number'];
      document.getElementById(id).innerHTML = '<span class="badge badge-soft-primary">' + version_number + '</span>';
    }
    else{
      document.getElementById(id).innerHTML = '<span class="badge badge-soft-danger">' + response['message'] + '</span>';
    }
  });
}

function uninstall_tool(tool_id, tool_name){
  Swal.fire({
    title: interpolate('Are you sure you want to uninstall %(toolName)s', {toolName: htmlEncode(tool_name)}, true),
    text: gettext(`This is not reversible. Please proceed with caution.`),
    icon: 'warning',
    confirmButtonText: interpolate('Uninstall %(toolName)s', {toolName: htmlEncode(tool_name)}, true),
  }).then((result) => {
    /* Read more about isConfirmed, isDenied below */
    if (result.isConfirmed) {
      Swal.fire({
        title: interpolate('Uninstalling %(toolName)s', {toolName: htmlEncode(tool_name)}, true),
        text: gettext('This may take a few minutes...'),
        allowOutsideClick: false
      });
      swal.showLoading();
      fetch('/api/tool/uninstall/?tool_id=' + tool_id)
      .then(response => response.json())
      .then(function (response) {
        console.log(response);
        swal.close();
        $("#tool_card_" + tool_name).remove();
        Swal.fire({
          title:  interpolate('%(toolName)s Uninstalled!', {toolName: htmlEncode(tool_name)}, true),
          text: interpolate(`%(toolName)s has been Uninstalled.`, {toolName: htmlEncode(tool_name)}, true),
          icon: 'success',
        });
      });
    }
  });
}


// show hide tools
$('#btn_show_custom_tools').on('click', function () {
  $('.custom_tool').show();
  $('.default_tool').hide();
  Snackbar.show({
    text: gettext('Filtered custom tools'),
    pos: 'top-right',
    duration: 2500
  });
  $('#btn_show_custom_tools').addClass('btn-primary').removeClass('btn-light');
  $('#btn_show_all_tools').addClass('btn-light');
  $('#btn_show_default_tools').addClass('btn-light');
});

$('#btn_show_default_tools').on('click', function () {
  $('.custom_tool').hide();
  $('.default_tool').show();
  Snackbar.show({
    text: gettext('Filtered default tools'),
    pos: 'top-right',
    duration: 2500
  });
  $('#btn_show_default_tools').addClass('btn-primary').removeClass('btn-light');
  $('#btn_show_custom_tools').addClass('btn-light');
  $('#btn_show_all_tools').addClass('btn-light');
});

$('#btn_show_all_tools').on('click', function () {
  $('.custom_tool').show();
  $('.default_tool').show();
  Snackbar.show({
    text: gettext('Displaying all tools'),
    pos: 'top-right',
    duration: 2500
  });
  $('#btn_show_all_tools').addClass('btn-primary').removeClass('btn-light');
  $('#btn_show_custom_tools').addClass('btn-light');
  $('#btn_show_default_tools').addClass('btn-light');
});
