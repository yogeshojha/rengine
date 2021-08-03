function get_important_subdomains(target_id){
  $.getJSON(`/api/querySubdomains/?target_id=${target_id}&only_important&no_lookup_interesting&format=json`, function(data) {
    $('#important-count').empty();
    $('#important-subdomains-list').empty();
    if (data['subdomains'].length > 0){
      $('#important-count').html(`<span class="badge outline-badge-dark">${data['subdomains'].length}</span>`);
      for (var val in data['subdomains']){
        subdomain = data['subdomains'][val];
        div_id = 'important_' + subdomain['id'];
        $("#important-subdomains-list").append(`
          <div id="${div_id}">
          <p>
          <span id="subdomain_${subdomain['id']}"> ${subdomain['name']}
          <span class="">
          <a href="javascript:;" data-clipboard-action="copy" class="m-1 float-right badge-link text-info copyable text-primary" data-toggle="tooltip" data-placement="top" title="Copy Subdomain!" data-clipboard-target="#subdomain_${subdomain['id']}">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-copy"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg></span>
          </a>
          </span>
          </p>
          </div>
          <hr />
          `
        );
      }
    }
    else{
      $('#important-count').html(`<span class="badge outline-badge-dark">0</span>`);
      $('#important-subdomains-list').append(`<p>No subdomains markerd as important!</p>`);
    }
    $('.bs-tooltip').tooltip();
  });
}
