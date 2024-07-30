function load_gf_template(pattern_name){
  Swal.fire({
		title: `Fetching GF template ${pattern_name}...`,
	});
	swal.showLoading();

  $.getJSON(`/api/getFileContents?gf_pattern&name=${pattern_name}&format=json`, function(response) {
    swal.close();
    if (response.status) {
      $('#modal_title').empty();
      $('#modal-content').empty();
      $("#modal-footer").empty();

      $('#modal_title').html(`GF Pattern ` + htmlEncode(pattern_name));

      $('#modal-content').append(`<pre>${htmlEncode(response['content'])}</pre>`);
      $('#modal_dialog').modal('show');
    }
    else{
      swal.fire("Error!", response.message, "error", {
        button: "Okay",
      });
    }

  }).fail(function(){
    swal.fire("Error!", 'Error loading gf pattern!', "error", {
      button: "Okay",
    });
  });
}

function load_nuclei_template(pattern_name){
  Swal.fire({
		title: `Fetching Nuclei template ${pattern_name}...`,
	});
	swal.showLoading();

  $.getJSON(`/api/getFileContents?nuclei_template&name=${pattern_name}&format=json`, function(response) {
    swal.close();
    if (response.status) {
      $('#modal_title').empty();
      $('#modal-content').empty();
      $("#modal-footer").empty();

      $('#modal_title').html(`Nuclei Template: ` + htmlEncode(pattern_name));

      $('#modal-content').append(`<pre>${htmlEncode(response['content'])}</pre>`);
      $('#modal_dialog').modal('show');
    }
    else{
      swal.fire("Error!", response.message, "error", {
        button: "Okay",
      });
    }

  }).fail(function(){
    swal.fire("Error!", 'Error loading Nuclei Template!', "error", {
      button: "Okay",
    });
  });
}


// get nuclei config
$.getJSON(`/api/getFileContents?nuclei_config&format=json`, function(data) {
  $("#nuclei_config_text_area").attr("rows", 17);
  $("textarea#nuclei_config_text_area").html(data['content']);
}).fail(function(){
  $("#nuclei_config_text_area").removeAttr("readonly");
  $("textarea#nuclei_config_text_area").html(`# Your nuclei configuration here.`);
  $("#nuclei-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="nuclei-config-submit">');
});

$("#nuclei_config_text_area").dblclick(function() {
  if (!document.getElementById('nuclei-config-submit')) {
    $("#nuclei_config_text_area").removeAttr("readonly");
    $("#nuclei-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="nuclei-config-submit">');
  }
});

// get Subfinder config
$.getJSON(`/api/getFileContents?subfinder_config&format=json`, function(data) {
  $("#subfinder_config_text_area").attr("rows", 14);
  $("textarea#subfinder_config_text_area").html(htmlEncode(data['content']));
}).fail(function(){
  $("#subfinder_config_text_area").removeAttr("readonly");
  $("textarea#subfinder_config_text_area").html(`# Your Subfinder configuration here.`);
  $("#subfinder-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="subfinder-config-submit">');
});

$("#subfinder_config_text_area").dblclick(function() {
  if (!document.getElementById('subfinder-config-submit')) {
    $("#subfinder_config_text_area").removeAttr("readonly");
    $("#subfinder-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="subfinder-config-submit">');
  }
});

// get Naabu config
$.getJSON(`/api/getFileContents?naabu_config&format=json`, function(data) {
  $("#naabu_config_text_area").attr("rows", 14);
  $("textarea#naabu_config_text_area").html(htmlEncode(data['content']));
}).fail(function(){
  $("#naabu_config_text_area").removeAttr("readonly");
  $("textarea#naabu_config_text_area").html(`# Your Naabu configuration here.`);
  $("#naabu-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="naabu-config-submit">');
});

$("#naabu_config_text_area").dblclick(function() {
  if (!document.getElementById('naabu-config-submit')) {
    $("#naabu_config_text_area").removeAttr("readonly");
    $("#naabu-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="naabu-config-submit">');
  }
});


// get amass config
$.getJSON(`/api/getFileContents?amass_config&format=json`, function(data) {
  $("#amass_config_text_area").attr("rows", 14);
  $("textarea#amass_config_text_area").html(htmlEncode(data['content']));
}).fail(function(){
  $("#amass_config_text_area").removeAttr("readonly");
  $("textarea#amass_config_text_area").html(`# Your amass configuration here.`);
  $("#amass-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="amass-config-submit">');
});

$("#amass_config_text_area").dblclick(function() {
  if (!document.getElementById('amass-config-submit')) {
    $("#amass_config_text_area").removeAttr("readonly");
    $("#amass-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="amass-config-submit">');
  }
});

// get theharvester config
$.getJSON(`/api/getFileContents?theharvester_config&format=json`, function(data) {
  $("#theharvester_config_text_area").attr("rows", 14);
  $("textarea#theharvester_config_text_area").html(htmlEncode(data['content']));
}).fail(function(){
  $("#theharvester_config_text_area").removeAttr("readonly");
  $("textarea#theharvester_config_text_area").html(`# Your the Harvester configuration here.`);
  $("#theHarvester-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-right" value="Save Changes" id="theharvester-config-submit">');
});

$("#theharvester_config_text_area").dblclick(function() {
  if (!document.getElementById('theharvester-config-submit')) {
    $("#theharvester_config_text_area").removeAttr("readonly");
    $("#theharvester-config-form").append('<input type="submit" class="btn btn-primary mt-2 float-end" value="Save Changes" id="theharvester-config-submit">');
  }
});
