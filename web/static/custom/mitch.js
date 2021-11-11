/*Copyright (c) 2013-2016, Rob Schmuecker
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* The name Rob Schmuecker may not be used to endorse or promote products
  derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL MICHAEL BOSTOCK BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.*/

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

    // Calculate total nodes, max label length
    var totalNodes = 0;
    var maxLabelLength = 0;
    // variables for drag/drop
    var selectedNode = null;
    var draggingNode = null;
    // panning variables
    var panSpeed = 200;
    var panBoundary = 20; // Within 20px from edges will pan when dragging.
    // Misc. variables
    var i = 0;
    var duration = 750;
    var root;

    var subdomain_count = data[0]['children'][0]['children'].length;
    // size of the diagram
    var viewerWidth = screen_width  - 100;
    var viewerHeight = screen_height + 500;

    var tree = d3.layout.tree()
    .size([viewerHeight, viewerWidth]);

    // define a d3 diagonal projection for use by the node paths later on.
    var diagonal = d3.svg.diagonal()
    .projection(function(d) {
      return [d.y, d.x];
    });

    // A recursive helper function for performing some setup by walking through all nodes

    function visit(parent, visitFn, childrenFn) {
      if (!parent) return;

      visitFn(parent);

      var children = childrenFn(parent);
      if (children) {
        var count = children.length;
        for (var i = 0; i < count; i++) {
          visit(children[i], visitFn, childrenFn);
        }
      }
    }

    // Call visit function to establish maxLabelLength
    visit(treeData, function(d) {
      totalNodes++;
      maxLabelLength = Math.max(d.description.length, maxLabelLength);

    }, function(d) {
      return d.children && d.children.length > 0 ? d.children : null;
    });

    // TODO: Pan function, can be better implemented.

    function pan(domNode, direction) {
      var speed = panSpeed;
      if (panTimer) {
        clearTimeout(panTimer);
        translateCoords = d3.transform(svgGroup.attr("transform"));
        if (direction == 'left' || direction == 'right') {
          translateX = direction == 'left' ? translateCoords.translate[0] + speed : translateCoords.translate[0] - speed;
          translateY = translateCoords.translate[1];
        } else if (direction == 'up' || direction == 'down') {
          translateX = translateCoords.translate[0];
          translateY = direction == 'up' ? translateCoords.translate[1] + speed : translateCoords.translate[1] - speed;
        }
        scaleX = translateCoords.scale[0];
        scaleY = translateCoords.scale[1];
        scale = zoomListener.scale();
        svgGroup.transition().attr("transform", "translate(" + translateX + "," + translateY + ")scale(" + scale + ")");
        d3.select(domNode).select('g.node').attr("transform", "translate(" + translateX + "," + translateY + ")");
        zoomListener.scale(zoomListener.scale());
        zoomListener.translate([translateX, translateY]);
        panTimer = setTimeout(function() {
          pan(domNode, speed, direction);
        }, 50);
      }
    }

    // Define the zoom function for the zoomable tree

    function zoom() {
      svgGroup.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
    }


    // define the zoomListener which calls the zoom function on the "zoom" event constrained within the scaleExtents
    var zoomListener = d3.behavior.zoom().scaleExtent([0.1, 3]).on("zoom", zoom);

    // define the baseSvg, attaching a class for styling and the zoomListener
    var baseSvg = d3.select("#visualisation").append("svg")
    .attr("id", "visualisation-svg")
    .attr("width", viewerWidth)
    .attr("height", viewerHeight)
    .call(zoomListener);

    // Helper functions for collapsing and expanding nodes.

    function collapse(d) {
      if (d.children) {
        d._children = d.children;
        d._children.forEach(collapse);
        d.children = null;
      }
    }

    function expand(d) {
      if (d._children) {
        d.children = d._children;
        d.children.forEach(expand);
        d._children = null;
      }
    }

    var overCircle = function(d) {
      selectedNode = d;
      updateTempConnector();
    };
    var outCircle = function(d) {
      selectedNode = null;
      updateTempConnector();
    };

    // Function to update the temporary connector indicating dragging affiliation
    var updateTempConnector = function() {
      var data = [];
      if (draggingNode !== null && selectedNode !== null) {
        // have to flip the source coordinates since we did this for the existing connectors on the original tree
        data = [{
          source: {
            x: selectedNode.y0,
            y: selectedNode.x0
          },
          target: {
            x: draggingNode.y0,
            y: draggingNode.x0
          }
        }];
      }
      var link = svgGroup.selectAll(".templink").data(data);

      link.enter().append("path")
      .attr("class", "templink")
      .attr("d", d3.svg.diagonal())
      .attr('pointer-events', 'none');

      link.attr("d", d3.svg.diagonal());

      link.exit().remove();
    };

    // Function to center node when clicked/dropped so node doesn't get lost when collapsing/moving with large amount of children.

    function centerNode(source) {
      scale = zoomListener.scale();
      x = -source.y0;
      y = -source.x0;
      x = x * scale + viewerWidth / 2;
      y = y * scale + viewerHeight / 2;
      d3.select('g').transition()
      .duration(duration)
      .attr("transform", "translate(" + x + "," + y + ")scale(" + scale + ")");
      zoomListener.scale(scale);
      zoomListener.translate([x, y]);
    }

    // Toggle children function

    function toggleChildren(d) {
      if (d.children) {
        d._children = d.children;
        d.children = null;
      } else if (d._children) {
        d.children = d._children;
        d._children = null;
      }
      return d;
    }

    // Toggle children on click.

    function click(d) {
      if (d3.event.defaultPrevented) return; // click suppressed
      d = toggleChildren(d);
      update(d);
      centerNode(d);
    }

    function update(source) {
      // Compute the new height, function counts total children of root node and sets tree height accordingly.
      // This prevents the layout looking squashed when new nodes are made visible or looking sparse when nodes are removed
      // This makes the layout more consistent.
      var levelWidth = [1];
      var childCount = function(level, n) {

        if (n.children && n.children.length > 0) {
          if (levelWidth.length <= level + 1) levelWidth.push(0);

          levelWidth[level + 1] += n.children.length;
          n.children.forEach(function(d) {
            childCount(level + 1, d);
          });
        }
      };
      childCount(0, root);
      var newHeight = d3.max(levelWidth) * 25; // 25 pixels per line
      tree = tree.size([newHeight, viewerWidth]);

      // Compute the new tree layout.
      var nodes = tree.nodes(root).reverse(),
      links = tree.links(nodes);

      // Set widths between levels based on maxLabelLength.
      nodes.forEach(function(d) {
        d.y = (d.depth * (maxLabelLength * 10)); //maxLabelLength * 10px
        // alternatively to keep a fixed scale one can set a fixed depth per level
        // Normalize for fixed-depth by commenting out below line
        // d.y = (d.depth * 500); //500px per level.
      });

      // Update the nodes…
      node = svgGroup.selectAll("g.node")
      .data(nodes, function(d) {
        return d.id || (d.id = ++i);
      });

      // Enter any new nodes at the parent's previous position.
      var nodeEnter = node.enter().append("g")
      .attr("class", "node")
      .attr("transform", function(d) {
        return "translate(" + source.y0 + "," + source.x0 + ")";
      })
      .on('click', click);

      nodeEnter.append("circle")
      .attr('class', 'nodeCircle')
      .attr("r", 1e-6)
      .style("fill", function(d) {
        return d._children ? "lightsteelblue" : "#fff";
      });

      nodeEnter.append('text')
      .attr("x", function(d) {
        return d.children || d._children ? -10 : 10;
      })
      .attr("dy", ".35em")
      .attr("text-anchor", function(d) {
        return d.children || d._children ? "end" : "start";
      })
      .attr('class', function(data){
        text_class = "";
        if (data.http_status >= 400 || data.is_uncommon || data.description == 'High' || data.title == 'Exposed Creds') {
          text_class = " svg-text-danger "
        }
        else if (data.http_status > 200 && data.http_status < 400 || data.description == 'Medium') {
          text_class = " svg-text-warning "
        }
        else if (data.http_status == 200) {
          text_class = " svg-text-success "
        }
        else if (data.description == 'Critical'){
          text_class = " svg-text-critical "
        }
        else if (data.description == 'Low'){
          text_class = " svg-text-low "
        }
        else if (data.description == 'Informational'){
          text_class = " svg-text-primary "
        }
        return 'textNode' + text_class;
      })
      .text(function(d) {
        if (d.title == 'Interesting') {
          return '(Interesting) ' + d.description;
        }
        return d.description;
      });

      // Change the circle fill depending on whether it has children and is collapsed
      node.select("circle.nodeCircle")
      .attr("r", 7)
      .style("fill", function(d) {
        return d._children ? "lightsteelblue" : "#fff";
      }).attr('cursor', 'pointer');;

      // Transition nodes to their new position.
      var nodeUpdate = node.transition()
      .duration(duration)
      .attr("transform", function(d) {
        return "translate(" + d.y + "," + d.x + ")";
      });

      // Fade the text in
      nodeUpdate.select("text")
      .style("fill-opacity", 1);

      // Transition exiting nodes to the parent's new position.
      var nodeExit = node.exit().transition()
      .duration(duration)
      .attr("transform", function(d) {
        return "translate(" + source.y + "," + source.x + ")";
      })
      .remove();

      nodeExit.select("circle")
      .attr("r", 0);

      nodeExit.select("text")
      .style("fill-opacity", 0);

      // Update the links…
      var link = svgGroup.selectAll("path.link")
      .data(links, function(d) {
        return d.target.id;
      });

      // Enter any new links at the parent's previous position.
      link.enter().insert("path", "g")
      .attr("class", "link")
      .attr("d", function(d) {
        var o = {
          x: source.x0,
          y: source.y0
        };
        return diagonal({
          source: o,
          target: o
        });
      });

      // Transition links to their new position.
      link.transition()
      .duration(duration)
      .attr("d", diagonal);

      // Transition exiting nodes to the parent's new position.
      link.exit().transition()
      .duration(duration)
      .attr("d", function(d) {
        var o = {
          x: source.x,
          y: source.y
        };
        return diagonal({
          source: o,
          target: o
        });
      })
      .remove();

      // Stash the old positions for transition.
      nodes.forEach(function(d) {
        d.x0 = d.x;
        d.y0 = d.y;
      });
    }

    // Append a group which holds all nodes and which the zoom Listener can act upon.
    var svgGroup = baseSvg.append("g");

    // Define the root
    root = treeData;
    root.x0 = viewerHeight / 2;
    root.y0 = 0;

    // Layout the tree initially and center on the root node.
    update(root);
    centerNode(root);

    function expandAll(){
      update(root);
      centerNode(root);
    }

    var checkbox = document.querySelector("input[name=expand-nodes-checkbox]");

    checkbox.addEventListener('change', function() {
      if (this.checked) {
        root.children.forEach(expand);
      } else {
        root.children.forEach(collapse);
      }
      update(root);
    });

    // source: view-source:https://www.demo2s.com/javascript/javascript-d3.js-save-svg-to-png-image-demo-b1a10.htm

    d3.select('#saveButton').on('click', function(){
      // get domain name
      var domain = $("[aria-current]").text();
      var svgString = getSVGString(d3.select('#visualisation-svg').node());
      svgString2Image( svgString, 2*viewerWidth, 2*viewerHeight, 'png', save ); // passes Blob and filesize String to the callback
      function save( dataBlob, filesize ){
        saveAs( dataBlob, domain + '_visualisation.png' ); // FileSaver.js function
      }
    });

    // Below are the functions that handle actual exporting:
    // getSVGString ( svgNode ) and svgString2Image( svgString, width, height, format, callback )
    function getSVGString( svgNode ) {
      svgNode.setAttribute('xlink', 'http://www.w3.org/1999/xlink');
      var cssStyleText = getCSSStyles( svgNode );
      appendCSS( cssStyleText, svgNode );
      var serializer = new XMLSerializer();
      var svgString = serializer.serializeToString(svgNode);
      svgString = svgString.replace(/(\w+)?:?xlink=/g, 'xmlns:xlink='); // Fix root xlink without namespace
      svgString = svgString.replace(/NS\d+:href/g, 'xlink:href'); // Safari NS namespace fix
      return svgString;
      function getCSSStyles( parentElement ) {
        var selectorTextArr = [];
        // Add Parent element Id and Classes to the list
        selectorTextArr.push( '#'+parentElement.id );
        for (var c = 0; c < parentElement.classList.length; c++)
        if ( !contains('.'+parentElement.classList[c], selectorTextArr) )
        selectorTextArr.push( '.'+parentElement.classList[c] );
        // Add Children element Ids and Classes to the list
        var nodes = parentElement.getElementsByTagName("*");
        for (var i = 0; i < nodes.length; i++) {
          var id = nodes[i].id;
          if ( !contains('#'+id, selectorTextArr) )
          selectorTextArr.push( '#'+id );
          var classes = nodes[i].classList;
          for (var c = 0; c < classes.length; c++)
          if ( !contains('.'+classes[c], selectorTextArr) )
          selectorTextArr.push( '.'+classes[c] );
        }
        // Extract CSS Rules
        var extractedCSSText = "";
        for (var i = 0; i < document.styleSheets.length; i++) {
          var s = document.styleSheets[i];
          try {
            if(!s.cssRules) continue;
          } catch( e ) {
            if(e.name !== 'SecurityError') throw e; // for Firefox
            continue;
          }
          var cssRules = s.cssRules;
          for (var r = 0; r < cssRules.length; r++) {
            if ( contains( cssRules[r].selectorText, selectorTextArr ) )
            extractedCSSText += cssRules[r].cssText;
          }
        }
        return extractedCSSText;
        function contains(str,arr) {
          return arr.indexOf( str ) === -1 ? false : true;
        }
      }
      function appendCSS( cssText, element ) {
        var styleElement = document.createElement("style");
        styleElement.setAttribute("type","text/css");
        styleElement.innerHTML = cssText;
        var refNode = element.hasChildNodes() ? element.children[0] : null;
        element.insertBefore( styleElement, refNode );
      }
    }
    function svgString2Image( svgString, width, height, format, callback ) {
      var format = format ? format : 'png';
      var imgsrc = 'data:image/svg+xml;base64,'+ btoa( unescape( encodeURIComponent( svgString ) ) ); // Convert SVG string to data URL
      var canvas = document.createElement("canvas");
      var context = canvas.getContext("2d");
      canvas.width = width;
      canvas.height = height;
      var image = new Image();
      image.onload = function() {
        context.clearRect ( 0, 0, width, height );
        context.drawImage(image, 0, 0, width, height);
        canvas.toBlob( function(blob) {
          var filesize = Math.round( blob.length/1024 ) + ' KB';
          if ( callback ) callback( blob, filesize );
        });
      };
      image.src = imgsrc;
    }

  }).fail(function(){
    $('#visualisation-loader').empty();
    $("#visualisation-loader").append(`<h5 class="text-danger">Sorry, could not visualize.</h5>`);
  });;
}
