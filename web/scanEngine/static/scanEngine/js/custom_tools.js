function load_gf_template(pattern_name){
  $('#modal-size').removeClass('modal-xl');
  $('#modal-size').addClass('modal-lg');
  $('.modal-title').html(`GF Pattern ` + pattern_name);
  $('#exampleModal').modal('show');
  $('.modal-text').empty();
  $('.modal-text').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  $.getJSON(`/api/getFileContents?gf_pattern&name=${pattern_name}&format=json`, function(data) {
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
  $.getJSON(`/api/getFileContents?nuclei_template&name=${pattern_name}&format=json`, function(data) {
    $('#modal-loader').empty();
    $('#modal-text-content').append(`<pre>${data['content']}</pre>`);
  }).fail(function(){
    $('#modal-loader').empty();
    $("#modal-text-content").append(`<p class='text-danger'>Error loading Nuclei Template</p>`);
  });
}


// get nuclei config
$.getJSON(`/api/getFileContents?nuclei_config&format=json`, function(data) {
  $("#nuclei_config_text_area").attr("rows", 17);
  $("textarea#nuclei_config_text_area").html(data['content']);
}).fail(function(){
  $("#text-area-nuclei-config").empty();
  $("#text-area-nuclei-config").append(`<div class="alert alert-light-danger border-0 mb-4" role="alert">
  Sorry, Nuclei config could not be retrieved!
  </div> `);
});

$("#nuclei_config_text_area").dblclick(function() {
  if (!document.getElementById('nuclei-config-submit')) {
    $("#nuclei_config_text_area").removeAttr("readonly");
    $("#nuclei-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="nuclei-config-submit">')
  }
});
