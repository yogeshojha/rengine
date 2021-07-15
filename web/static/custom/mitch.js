
function visualise_scan_results(scan_id)
{
  $.getJSON(`/api/queryAllScanResultVisualise/?scan_id=${scan_id}&format=json`, function(data) {
    $('#visualisation-loader').empty();
    $('#visualisation-filter').show();
    data = data[0];
    var treePlugin = new d3.mitchTree.boxedTree();
    treePlugin
    .setData(data)
    .setMinScale(0.4)
    .setMaxScale(1)
    .setDuration(0)
    .setAllowFocus(false)
    .setAllowNodeCentering(false)
    .setElement(document.getElementById("visualisation"))
    .setIdAccessor(function(data) {
      return data.id;
    })
    .setChildrenAccessor(function(data) {
      return data.children;
    })
    .setBodyDisplayTextAccessor(function(data) {
      return data.description;
    })
    .setTitleDisplayTextAccessor(function(data) {
      return data.title;
    });
    treePlugin.getNodeSettings()
    .setSizingMode('nodesize')
    .setVerticalSpacing(20)
    .setHorizontalSpacing(10)
    .setBodyBoxHeight(50)
    .setBodyBoxWidth(260)
    .setTitleBoxHeight(30)
    .setTitleBoxWidth(80)
    .back()
    treePlugin.initialize();
    treePlugin.getZoomListener().scaleTo(treePlugin.getSvg(), 1);
    treePlugin.on("nodeClick", function(event) {
      if (event.data.http_url) {
        window.open(event.data.http_url, '_blank').focus();
      }
      else if (event.data.screenshot_path){
        $('#exampleModal').modal('show');
        $('.modal-text').empty();
        $('#modal-text-content').append(`<div id="modal-screenshot"></div>`);
        load_image_from_url('/media/' + event.data.screenshot_path, "modal-screenshot")
      }
    });
    treePlugin.update = function(nodeDataItem){
      // Call the original update method
      this.__proto__.update.call(this, nodeDataItem);
      updateTreeClasses(this);
    }

    updateTreeClasses(treePlugin);

    var checkbox = document.querySelector("input[name=expand-nodes-checkbox]");

    checkbox.addEventListener('change', function() {
      if (this.checked) {
        console.log("Expanding nodes");
        var nodes = treePlugin.getNodes();
        nodes.forEach(function(node, index, arr) {
          treePlugin.expand(node);
        });
        treePlugin.update(treePlugin.getRoot());
        console.log("Expanded nodes");
      } else {
        var nodes = treePlugin.getNodes();
        nodes.forEach(function(node, index, arr) {
          treePlugin.collapse(node);
        });
        treePlugin.update(treePlugin.getRoot());
      }
    });

  }).fail(function(){
    $('#visualisation-loader').empty();
    $("#visualisation-loader").append(`<h5 class="text-danger">Sorry, could not visualize.</h5>`);
  });
}

function updateTreeClasses(treePlugin)
{
  treePlugin.getPanningContainer().selectAll("g.node")
  .attr("class", function(data, index, arr) {
    bg_class = '';
    var depthClass = "depth-" + data.depth;
    var existingClasses = this.getAttribute('class');
    if (data.data.http_status >= 400 || data.data.is_uncommon || data.data.description == 'High' || data.data.title == 'Exposed Creds') {
      bg_class = " danger-box "
    }
    else if (data.data.http_status > 200 && data.data.http_status < 400 || data.data.description == 'Medium') {
      bg_class = " warning-box "
    }
    else if (data.data.http_status == 200) {
      bg_class = " success-box "
    }
    else if (data.data.description == 'Critical'){
      bg_class = " critical-box "
    }
    else if (data.data.description == 'Low'){
      bg_class = " low-box "
    }
    else if (data.data.description == 'Informational'){
      bg_class = " info-box "
    }
    if (!existingClasses)
    return depthClass;
    var hasDepthClassAlready = (' ' + existingClasses + ' ').indexOf(' ' + depthClass + ' ') > -1;
    if (hasDepthClassAlready)
    return existingClasses + bg_class;
    return existingClasses + " " + depthClass + bg_class;
  });
}
