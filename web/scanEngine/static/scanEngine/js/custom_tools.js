function load_gf_template(pattern_name){
  $('#modal-size').removeClass('modal-xl');
  $('#modal-size').addClass('modal-lg');
  $('.modal-title').html(`GF Pattern ` + htmlEncode(pattern_name));
  $('#exampleModal').modal('show');
  $('.modal-text').empty();
  $('.modal-text').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  $.getJSON(`/api/getFileContents?gf_pattern&name=${pattern_name}&format=json`, function(data) {
    $('#modal-loader').empty();
    $('#modal-text-content').append(`<pre>${htmlEncode(data['content'])}</pre>`);
  }).fail(function(){
    $('#modal-loader').empty();
    $("#modal-text-content").append(`<p class='text-danger'>Error loading GF Pattern</p>`);
  });
}


function load_nuclei_template(pattern_name){
  $('#modal-size').removeClass('modal-lg');
  $('#modal-size').addClass('modal-xl');
  $('.modal-title').html(`Nuclei Pattern ` + htmlEncode(pattern_name));
  $('#exampleModal').modal('show');
  $('.modal-text').empty();
  $('.modal-text').append(`<div class='outer-div' id="modal-loader"><span class="inner-div spinner-border text-info align-self-center loader-sm"></span></div>`);
  $.getJSON(`/api/getFileContents?nuclei_template&name=${pattern_name}&format=json`, function(data) {
    $('#modal-loader').empty();
    $('#modal-text-content').append(`<pre>${htmlEncode(data['content'])}</pre>`);
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
  $("#nuclei_config_text_area").removeAttr("readonly");
  $("textarea#nuclei_config_text_area").html(`# Your nuclei configuration here.`);
  $("#nuclei-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="nuclei-config-submit">');
});

$("#nuclei_config_text_area").dblclick(function() {
  if (!document.getElementById('nuclei-config-submit')) {
    $("#nuclei_config_text_area").removeAttr("readonly");
    $("#nuclei-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="nuclei-config-submit">');
  }
});

// get Subfinder config
$.getJSON(`/api/getFileContents?subfinder_config&format=json`, function(data) {
  $("#subfinder_config_text_area").attr("rows", 14);
  $("textarea#subfinder_config_text_area").html(htmlEncode(data['content']));
}).fail(function(){
  $("#subfinder_config_text_area").removeAttr("readonly");
  $("textarea#subfinder_config_text_area").html(`# Your Subfinder configuration here.`);
  $("#subfinder-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="subfinder-config-submit">');
});

$("#subfinder_config_text_area").dblclick(function() {
  if (!document.getElementById('subfinder-config-submit')) {
    $("#subfinder_config_text_area").removeAttr("readonly");
    $("#subfinder-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="subfinder-config-submit">');
  }
});

// get Naabu config
$.getJSON(`/api/getFileContents?naabu_config&format=json`, function(data) {
  $("#naabu_config_text_area").attr("rows", 14);
  $("textarea#naabu_config_text_area").html(htmlEncode(data['content']));
}).fail(function(){
  $("#naabu_config_text_area").removeAttr("readonly");
  $("textarea#naabu_config_text_area").html(`# Your Naabu configuration here.`);
  $("#naabu-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="naabu-config-submit">');
});

$("#naabu_config_text_area").dblclick(function() {
  if (!document.getElementById('naabu-config-submit')) {
    $("#naabu_config_text_area").removeAttr("readonly");
    $("#naabu-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="naabu-config-submit">');
  }
});


// get amass config
$.getJSON(`/api/getFileContents?amass_config&format=json`, function(data) {
  $("#amass_config_text_area").attr("rows", 14);
  $("textarea#amass_config_text_area").html(htmlEncode(data['content']));
}).fail(function(){
  $("#amass_config_text_area").removeAttr("readonly");
  $("textarea#amass_config_text_area").html(`# Your amass configuration here.`);
  $("#amass-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="amass-config-submit">');
});

$("#amass_config_text_area").dblclick(function() {
  if (!document.getElementById('amass-config-submit')) {
    $("#amass_config_text_area").removeAttr("readonly");
    $("#amass-config-form").append('<input type="submit" class="btn btn-info mt-2 float-right" value="Save Changes" id="amass-config-submit">');
  }
});
