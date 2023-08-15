const vuln_datatable_columns = [
	{'data': 'id'},
	{'data': 'source'},
	{'data': 'type'},

	{'data': 'name'},
	{'data': 'cvss_metrics'},
	{'data': 'tags'},
	{'data': 'hackerone_report_id'},

	{'data': 'severity'},
	{'data': 'cvss_score'},
	{'data': 'cve_ids'},
	{'data': 'cwe_ids'},
	{'data': 'http_url'},

	{'data': 'description'},
	{'data': 'references'},

	{'data': 'discovered_date'},

	{'data': 'open_status'},

	{'data': 'hackerone_report_id'},

	{'data': 'extracted_results'},
	{'data': 'curl_command'},
	{'data': 'matcher_name'},
	{'data': 'request'},
	{'data': 'response'},
	{'data': 'template'},
	{'data': 'template_url'},
	{'data': 'template_id'},
	{'data': 'impact'},
	{'data': 'remediation'},
	{'data': 'is_gpt_used'},
];

const vuln_datatable_page_length = 50;
const vuln_datatable_length_menu = [[50, 100, 500, 1000, -1], [50, 100, 500, 1000, 'All']];


function vulnerability_datatable_col_visibility(table){
	if(!$('#vuln_source_checkbox').is(":checked")){
		table.column(get_datatable_col_index('vuln_source_checkbox')).visible(false);
	}
	if(!$('#vuln_severity_checkbox').is(":checked")){
		table.column(get_datatable_col_index('severity')).visible(false);
	}
	if(!$('#vuln_vulnerable_url_checkbox').is(":checked")){
		table.column(get_datatable_col_index('http_url')).visible(false);
	}
	if(!$('#vuln_status_checkbox').is(":checked")){
		table.column(get_datatable_col_index('status')).visible(false);
	}
}


function vulnerability_datatable_grouping(table, api, cols){
	var rows = api.rows({ page: 'current' }).nodes();
	var last = null;

	var radioGroup = document.getElementsByName('grouping_vuln_row');

	radioGroup.forEach(function(radioButton) {
		radioButton.addEventListener('change', function() {
			if (this.checked) {
				var groupRows = document.querySelectorAll('tr.group');
				// Remove each group row
				groupRows.forEach(function(row) {
					row.parentNode.removeChild(row);
				});
				var col_index = get_datatable_col_index(cols, this.value);
				// table.order([[col_index, 'asc']]).draw();
				api.column(col_index, { page: 'current' })
					.data()
					.each(function (group, i) {
						if (last !== group) {
							$(rows)
								.eq(i)
								.before(
									'<tr class="group"><td colspan="7">' +
										group +
										'</td></tr>'
								);
							last = group;
						}
				});
			}
		});
	});
}
