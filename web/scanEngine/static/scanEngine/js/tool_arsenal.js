function get_external_tool_latest_version(tool_id, tool_name){
  var current_version = document.getElementById(tool_name+'_current').textContent;
  console.log(current_version)
  if (current_version === 'Invalid version lookup command.' || current_version === 'Version Lookup command not provided.'){
    Swal.fire({
      title: 'Unable to fetch latest version!',
      text: `Since the version lookup command is invalid, reNgine is not able to detect if there's a newer version. But you can still force download the latest version.`,
      icon: 'info',
      confirmButtonText: 'Update ' +  htmlEncode(tool_name)
    }).then((result) => {
      /* Read more about isConfirmed, isDenied below */
      if (result.isConfirmed) {
        Swal.fire({
          title: 'Downloading latest version...',
          text: 'This may take a few minutes.',
          allowOutsideClick: false
        });
        swal.showLoading();
        fetch('/api/tool/update/?tool_id=' + tool_id)
        .then(response => response.json())
        .then(function (response) {
          swal.close();
          if (response['status']) {
            Swal.fire({
              title:  htmlEncode(tool_name) + ' Updated!',
              text: response['message'],
              icon: 'success',
            });
          }
          else{
            Swal.fire({
              title:  htmlEncode(tool_name) + ' could not update!',
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
      title: 'Finding latest version...',
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
          title: 'Error!',
          text: 'Github API rate limit exceeded, we can not fetch the latest version number, please try again in an hour. But you can force download the latest version.',
          icon: 'error',
          confirmButtonText: 'Force download',
        }).then((result) => {
          if (result.isConfirmed) {
            Swal.fire({
              title: 'Downloading latest version...',
              text: 'This may take a few minutes.',
              allowOutsideClick: false
            });
            swal.showLoading();
            fetch('/api/tool/update/?tool_id=' + tool_id)
            .then(response => response.json())
            .then(function (response) {
              swal.close();
              if (response['status']) {
                Swal.fire({
                  title:  htmlEncode(tool_name) + ' Updated!',
                  text: response['message'],
                  icon: 'success',
                });
              }
              else{
                Swal.fire({
                  title:  htmlEncode(tool_name) + ' could not update!',
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
          title: 'Oops!',
          text: 'We ran into an error! Please raise github request.',
          icon: 'error'
        });
      }
      else if (response['message'] == 'Not Found'){
        Swal.fire({
          showCancelButton: true,
          title: 'Oops!',
          text: 'The github URL provided is not valid, or the project doesn\'t support releases. We are unable to check the latest version number, however, you can still force download the update',
          icon: 'error',
          confirmButtonText: 'Force download',
        }).then((result) => {
          /* Read more about isConfirmed, isDenied below */
          if (result.isConfirmed) {
            Swal.fire({
              title: 'Downloading latest version...',
              text: 'This may take a few minutes.',
              allowOutsideClick: false
            });
            swal.showLoading();
            fetch('/api/tool/update/?tool_id=' + tool_id)
            .then(response => response.json())
            .then(function (response) {
              swal.close();
              if (response['status']) {
                Swal.fire({
                  title:  htmlEncode(tool_name) + ' Updated!',
                  text: response['message'],
                  icon: 'success',
                });
              }
              else{
                Swal.fire({
                  title:  htmlEncode(tool_name) + ' could not update!',
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
            title: 'Unable to fetch latest version!',
            text: `Since the version lookup command is invalid, reNgine is not able to detect if there's a newer version. But you can still force download the latest version. The latest version is ${latest_version}.`,
            icon: 'info',
            confirmButtonText: 'Update ' +  htmlEncode(tool_name)
          }).then((result) => {
            /* Read more about isConfirmed, isDenied below */
            if (result.isConfirmed) {
              Swal.fire({
                title: 'Downloading latest version...',
                text: 'This may take a few minutes.',
                allowOutsideClick: false
              });
              swal.showLoading();
              fetch('/api/tool/update/?tool_id=' + tool_id)
              .then(response => response.json())
              .then(function (response) {
                swal.close();
                Swal.fire({
                  title:  htmlEncode(tool_name) + ' Updated!',
                  text: `${tool_name} has now been updated to v${latest_version}!`,
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
              title: 'No Update available',
              text: 'Looks like the latest version of ' +  htmlEncode(tool_name) + ' is already installed.',
              icon: 'info'
            });
          }
          else{
            // update available
            Swal.fire({
              title: 'Update available! Version: ' + latest_version,
              text: `Your current version of ${ htmlEncode(tool_name)} is v${current_version}, but latest version v${latest_version} is available, please update!`,
              icon: 'info',
              confirmButtonText: 'Update ' +  htmlEncode(tool_name)
            }).then((result) => {
              if (result.isConfirmed) {
                Swal.fire({
                  title: 'Downloading latest version...',
                  text: 'This may take a few minutes.',
                  allowOutsideClick: false
                });
                swal.showLoading();
                fetch('/api/tool/update/?tool_id=' + tool_id)
                .then(response => response.json())
                .then(function (response) {
                  swal.close();
                  Swal.fire({
                    title:  htmlEncode(tool_name) + ' Updated!',
                    text: `${ htmlEncode(tool_name)} has now been updated to v${latest_version}!`,
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
    title: 'Are you sure you want to uninstall ' + htmlEncode(tool_name),
    text: `This is not reversible. Please proceed with caution.`,
    icon: 'warning',
    confirmButtonText: 'Uninstall ' +  htmlEncode(tool_name)
  }).then((result) => {
    /* Read more about isConfirmed, isDenied below */
    if (result.isConfirmed) {
      Swal.fire({
        title: 'Uninstalling ' + htmlEncode(tool_name),
        text: 'This may take a few minutes...',
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
          title:  htmlEncode(tool_name) + ' Uninstalled!',
          text: `${tool_name} has been Uninstalled.`,
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
    text: 'Filtered custom tools',
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
    text: 'Filtered default tools',
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
    text: 'Displaying all tools',
    pos: 'top-right',
    duration: 2500
  });
  $('#btn_show_all_tools').addClass('btn-primary').removeClass('btn-light');
  $('#btn_show_custom_tools').addClass('btn-light');
  $('#btn_show_default_tools').addClass('btn-light');
});
