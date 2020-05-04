$(function(){
	$('#africa-map').vectorMap({
		map: 'africa_mill',
		backgroundColor: '#f8538d',
		regionStyle: {
			initial: {
				fill: '#fff'
			}
		}

	});

	$('#asia-map').vectorMap({
	  map: 'asia_mill',
		  backgroundColor: '#2196f3',
		  regionStyle: {
			  initial: {
				  fill: '#fff'
			  }
		  }
	});

	$('#continents-map').vectorMap({
	  map: 'continents_mill',
		  backgroundColor: '#25d5e4',
		  regionStyle: {
			  initial: {
				  fill: '#fff'
			  }
		  }
	});

	$('#europe-map').vectorMap({
	  map: 'europe_mill',
		  backgroundColor: '#3b3f5c',
		  regionStyle: {
			  initial: {
				  fill: '#fff'
			  }
		  }
	});

	$('#north_america-map').vectorMap({
	  map: 'north_america_mill',
		  backgroundColor: '#ffbb44',
		  regionStyle: {
			  initial: {
				  fill: '#fff'
			  }
		  }
	});

	$('#oceanina-map').vectorMap({
	  map: 'oceania_mill',
		  backgroundColor: '#e95f2b',
		  regionStyle: {
			  initial: {
				  fill: '#fff'
			  }
		  }
	});

	$('#south-america-map').vectorMap({
	  map: 'south_america_mill',
		  backgroundColor: '#25d5e4',
		  regionStyle: {
			  initial: {
				  fill: '#fff'
			  }
		  }
	});

	$('#world-map').vectorMap({

	   	map: 'world_mill_en',
		backgroundColor: '#5c1ac3',
		borderColor: '#818181',
		borderOpacity: 0.25,
		borderWidth: 1,
		color: '#f4f3f0',
		regionStyle: {
			initial: {
				fill: '#fff'
			}
		},
		markerStyle: {
		 	initial: {
				r: 9,
				'fill': '#fff',
				'fill-opacity': 1,
				'stroke': '#000',
				'stroke-width': 5,
				'stroke-opacity': 0.4
			},
		},
		enableZoom: true,
		hoverColor: '#060818',
		hoverOpacity: null,
		normalizeFunction: 'linear',
		scaleColors: ['#b6d6ff', '#005ace'],
		selectedColor: '#c9dfaf',
		selectedRegions: [],
		showTooltip: true,

	});
});
   