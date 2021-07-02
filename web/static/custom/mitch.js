
function visualise_scan_results(scan_id)
{
	$.getJSON(`../api/queryAllScanResultVisualise/?scan_id=${scan_id}&format=json`, function(data) {
		data = data[0];
		var treePlugin = new d3.mitchTree.boxedTree();
		treePlugin
		.setData(data)
		.setMinScale(0.4)
		.setMaxScale(1)
		.setAllowFocus(false)
		.setAllowNodeCentering(true)
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
					.setVerticalSpacing(40)
					.setHorizontalSpacing(10)
					.setBodyBoxHeight(70)
					.back()
		treePlugin.initialize();
		treePlugin.getZoomListener().scaleTo(treePlugin.getSvg(), 0.7);
	});
}
