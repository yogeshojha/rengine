
function visualise_scan_results(scan_id)
{
  $.getJSON(`../api/queryDorkTypes/?scan_id=${scan_id}&format=json`, function(data) {
    var treePlugin = new d3.mitchTree.boxedTree()
    .setData(data)
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
      return data.name;
    })
    .initialize();
  });
}
