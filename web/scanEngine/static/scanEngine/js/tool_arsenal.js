function get_external_tool_latest_version(tool_id, tool_name){
  Swal.fire({
    title: 'Finding latest version...',
    allowOutsideClick: false
  });
  swal.showLoading();
  fetch('/api/github/tool/get_latest_releases/?tool_id=' + tool_id)
  .then(response => response.json())
  .then(function (response) {
    swal.close();
    console.log(response);
    if (response['description'] == 'RateLimited') {
      Swal.fire({
        showCancelButton: true,
        title: 'Error!',
        text: 'Github API rate limit exceeded, we can not fetch the latest version number, please try again in an hour. But you can force download the latest version.',
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
            Swal.fire({
              title: tool_name + ' Updated!',
              text: `${tool_name} has now been updated to v${latest_version}!`,
              icon: 'success',
            });
          });
        }
      });;
    }
    else if (response['description'] == 'Tool Not found'){
      Swal.fire({
        title: 'Oops!',
        text: 'We ran into an error! Please raise github request.',
        icon: 'error'
      });
    }
    else{
      // match current version with installed version
      // sometimes version names can be v1.1.1 or 1.1.1, so for consistency
      // let's remove v from both

      var current_version = document.getElementById(tool_name+'_current').textContent;
      current_version = current_version.charAt(0) == 'v' ? current_version.substring(1) : current_version;
      console.log(current_version);

      var latest_version = response['name'];
      latest_version = latest_version.charAt(0) == 'v' ? latest_version.substring(1) : latest_version;

      if (current_version == latest_version) {
        Swal.fire({
          title: 'No Update available',
          text: 'Looks like the latest version of ' + tool_name + ' is already installed.',
          icon: 'info'
        });
      }
      else{
        // update available
        Swal.fire({
          title: 'Update available! Version: ' + latest_version,
          text: `Your current version of ${tool_name} is v${current_version}, but latest version v${latest_version} is available, please udpate!`,
          icon: 'info',
          confirmButtonText: 'Update ' + tool_name
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
                title: tool_name + ' Updated!',
                text: `${tool_name} has now been updated to v${latest_version}!`,
                icon: 'success',
              });
            });
          }
        });
      }
    }
  });
}

function get_external_tool_current_version(tool_id, id){
  fetch('/api/external/tool/get_current_release/?tool_id=' + tool_id)
  .then(response => response.json())
  .then(function (response){
    version_number = response['version_number'].charAt(0) == 'v' || response['version_number'].charAt(0) == 'V' ? response['version_number'] : 'v' + response['version_number'];
    document.getElementById(id).innerHTML = version_number;
  });
}


// add new tool modal
$(window).on('load', function() {
  $('#add-tool-modal').modal('show');
});
