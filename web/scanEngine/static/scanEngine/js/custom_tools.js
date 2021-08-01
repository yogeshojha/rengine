function load_gf_template(pattern_name){
  $('#modal-size').removeClass('modal-xl');
  $('#modal-size').addClass('modal-lg');
  $('.modal-title').html(`GF Pattern ` + pattern_name);
  $('#exampleModal').modal('show');
  $('.modal-text').empty();
  $('.modal-text').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  $.getJSON(`/api/listFileContents?gf_pattern&name=${pattern_name}&format=json`, function(data) {
    $('#modal-loader').empty();
    $('#modal-text-content').append(`<pre>${data['content']}</pre>`);
  }).fail(function(){
    $('#modal-loader').empty();
    $("#modal-text-content").append(`<p class='text-danger'>Error loading GF Pattern</p>`);
  });
}


function load_nuclei_template(pattern_name){
  $('#modal-size').removeClass('modal-lg');
  $('#modal-size').addClass('modal-xl');
  $('.modal-title').html(`Nuclei Pattern ` + pattern_name);
  $('#exampleModal').modal('show');
  $('.modal-text').empty();
  $('.modal-text').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  $.getJSON(`/api/listFileContents?nuclei_template&name=${pattern_name}&format=json`, function(data) {
    $('#modal-loader').empty();
    $('#modal-text-content').append(`<pre>${data['content']}</pre>`);
  }).fail(function(){
    $('#modal-loader').empty();
    $("#modal-text-content").append(`<p class='text-danger'>Error loading GF Pattern</p>`);
  });
}
