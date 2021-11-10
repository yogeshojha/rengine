function visualise_scan_results(scan_id)
{
  // Set the dimensions and margins of the diagram
  var screen_width = window.innerWidth
  || document.documentElement.clientWidth
  || document.body.clientWidth;

  var screen_height = window.innerHeight
  || document.documentElement.clientHeight
  || document.body.clientHeight;

  $.getJSON(`/api/queryAllScanResultVisualise/?scan_id=${scan_id}&format=json`, function(data) {
    $('#visualisation-loader').empty();
    $('#visualisation-filter').show();
    var treeData = data[0];

    var subdomain_count = data[0]['children'][0]['children'].length;

    var height_multiplier = (subdomain_count/80) > 0 ? (subdomain_count/80)*9 : 2.5;

    var margin = {top: 0, right: 20, bottom: 20, left: 120},
    width = screen_width - margin.left - margin.right,
    height = screen_height * height_multiplier - margin.top - margin.bottom;

    var zoom = d3.zoom().on("zoom", function(){
      svg.attr("transform", d3.event.transform);
    });

    // append the svg object to the body of the page
    // appends a 'group' element to 'svg'
    // moves the 'group' element to the top left margin
    var svg = d3.select("#visualisation").append("svg")
    .attr("width", width + margin.right + margin.left)
    .attr("height", height + margin.top + margin.bottom)
    .call(d3.zoom().on("zoom", function () {svg.attr("transform", d3.event.transform)}).scaleExtent([0.2, 3]))
    .append("g")
    .attr("transform", "translate("+ margin.left + "," + -1 * (height/2-250) + ")");

    var i = 0,
    duration = 500,
    root;

    // declares a tree layout and assigns the size
    var treemap = d3.tree().size([height, width]);

    // Assigns parent, children, height, depth
    root = d3.hierarchy(treeData, function(d) { return d.children; });
    root.x0 = height / 2;
    root.y0 = 0;

    // Collapse after the second level
    root.children.forEach(collapse);

    update(root);

    // Collapse the node and all it's children
    function collapse(d) {
      if(d.children) {
        d._children = d.children
        d._children.forEach(collapse)
        d.children = null
      }
    }

    // expand nodes
    function expand(d){
      if (d._children) {
        d.children = d._children;
        d._children = null;
      }
      var children = (d.children)?d.children:d._children;
      if(children)
      children.forEach(expand);
    }

    function expandAll(){
      expand(root);
      update(root);
    }

    function update(source) {

      // Assigns the x and y position for the nodes
      var treeData = treemap(root);

      // Compute the new tree layout.
      var nodes = treeData.descendants(),
      links = treeData.descendants().slice(1);

      // Normalize for fixed-depth.
      nodes.forEach(function(d){ d.y = d.depth * 180});

      // ****************** Nodes section ***************************

      // Update the nodes...
      var node = svg.selectAll('g.node')
      .data(nodes, function(d) {return d.id || (d.id = ++i); });

      // Enter any new modes at the parent's previous position.
      var nodeEnter = node.enter().append('g')
      .attr('class', 'node')
      .attr("transform", function(d) {
        return "translate(" + source.y0 + "," + source.x0 + ")";
      })
      .on('click', click);

      // Add Circle for the nodes
      nodeEnter.append('circle')
      .attr('class', 'node')
      .attr('r', 1e-6)
      .style("fill", function(d) {
        return d._children ? "lightsteelblue" : "#fff";
      });

      // Labels
      nodeEnter.append('text')
      .attr("x", function(d) {
        return d.children || d._children ? -10 : 10;
      })
      .attr("dy", ".35em")
      .attr("text-anchor", function(d) {
        return d.children || d._children ? "end" : "start";
      })
      .attr('class', 'nodeText')
      .text(function(d) { return d.data.description; });

      // UPDATE
      var nodeUpdate = nodeEnter.merge(node);

      // Transition to the proper position for the node
      nodeUpdate.transition()
      .duration(duration)
      .attr("transform", function(d) {
        return "translate(" + d.y + "," + d.x + ")";
      });

      // Update the node attributes and style
      nodeUpdate.select('circle.node')
      .attr('r', 7)
      .style("fill", function(d) {
        return d._children ? "lightsteelblue" : "#fff";
      })
      .attr('cursor', 'pointer');


      // Remove any exiting nodes
      var nodeExit = node.exit().transition()
      .duration(duration)
      .attr("transform", function(d) {
        return "translate(" + source.y + "," + source.x + ")";
      })
      .remove();

      // On exit reduce the node circles size to 0
      nodeExit.select('circle')
      .attr('r', 1e-6);

      // On exit reduce the opacity of text labels
      nodeExit.select('text')
      .style('fill-opacity', 1e-6);

      // ****************** links section ***************************

      // Update the links...
      var link = svg.selectAll('path.link')
      .data(links, function(d) { return d.id; });

      // Enter any new links at the parent's previous position.
      var linkEnter = link.enter().insert('path', "g")
      .attr("class", "link")
      .attr('d', function(d){
        var o = {x: source.x0, y: source.y0}
        return diagonal(o, o)
      });

      // UPDATE
      var linkUpdate = linkEnter.merge(link);

      // Transition back to the parent element position
      linkUpdate.transition()
      .duration(duration)
      .attr('d', function(d){ return diagonal(d, d.parent) });

      // Remove any exiting links
      var linkExit = link.exit().transition()
      .duration(duration)
      .attr('d', function(d) {
        var o = {x: source.x, y: source.y}
        return diagonal(o, o)
      })
      .remove();

      // Store the old positions for transition.
      nodes.forEach(function(d){
        d.x0 = d.x;
        d.y0 = d.y;
      });

      // Creates a curved (diagonal) path from parent to the child nodes
      function diagonal(s, d) {

        path = `M ${s.y} ${s.x}
        C ${(s.y + d.y) / 2} ${s.x},
        ${(s.y + d.y) / 2} ${d.x},
        ${d.y} ${d.x}`

        return path
      }

      // Toggle children on click.
      function click(d) {
        if (d.children) {
          d._children = d.children;
          d.children = null;
        } else {
          d.children = d._children;
          d._children = null;
        }
        update(d);
      }

    }

    var checkbox = document.querySelector("input[name=expand-nodes-checkbox]");

    checkbox.addEventListener('change', function() {
      if (this.checked) {
        expandAll();
      } else {
        root.children.forEach(collapse);
      }
      update(root);
    });

  }).fail(function(){
    $('#visualisation-loader').empty();
    $("#visualisation-loader").append(`<h5 class="text-danger">Sorry, could not visualize.</h5>`);
  });;
}
