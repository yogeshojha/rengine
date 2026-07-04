const vuln_datatable_columns = [
	{'data': 'id', 'defaultContent': ''},
	{'data': 'source', 'defaultContent': ''},
	{'data': 'type', 'defaultContent': ''},

	{'data': 'name', 'defaultContent': ''},
	{'data': 'cvss_metrics', 'defaultContent': ''},
	{'data': 'tags', 'defaultContent': ''},
	{'data': 'hackerone_report_id', 'defaultContent': ''},

	{'data': 'severity', 'defaultContent': ''},
	{'data': 'cvss_score', 'defaultContent': ''},
	{'data': 'cve_ids', 'defaultContent': ''},
	{'data': 'cwe_ids', 'defaultContent': ''},
	{'data': 'http_url', 'defaultContent': ''},

	{'data': 'description', 'defaultContent': ''},
	{'data': 'references', 'defaultContent': ''},

	{'data': 'discovered_date', 'defaultContent': ''},
	{'data': 'exploit_url', 'defaultContent': ''},
	{'data': 'validation_status', 'defaultContent': ''},

	{'data': 'open_status', 'defaultContent': ''},

	{'data': null, 'defaultContent': ''}, // 18

	{'data': 'extracted_results', 'defaultContent': ''},
	{'data': 'curl_command', 'defaultContent': ''},
	{'data': 'matcher_name', 'defaultContent': ''},
	{'data': 'request', 'defaultContent': ''},
	{'data': 'response', 'defaultContent': ''},
	{'data': 'template_id', 'defaultContent': ''},
	{'data': 'template_url', 'defaultContent': ''},
];

const vuln_datatable_page_length = 50;
const vuln_datatable_length_menu = [[50, 100, 500, 1000, -1], [50, 100, 500, 1000, 'All']];


function vulnerability_datatable_col_visibility(table){
	const hidden_cols = [
		'type', 'cvss_metrics', 'tags', 'hackerone_report_id', 
		'cve_ids', 'cwe_ids', 'description', 'references', 
		'discovered_date', 'exploit_url', 'validation_status',
		'extracted_results', 'curl_command', 'matcher_name',
		'request', 'response', 'template_id', 'template_url'
	];
	
	hidden_cols.forEach(col => {
		let idx = get_datatable_col_index(col, vuln_datatable_columns);
		if (idx !== -1) table.column(idx).visible(false);
	});
	
	// Ensure essential columns are visible
	const visible_cols = ['source', 'severity', 'cvss_score', 'http_url', 'open_status'];
	visible_cols.forEach(col => {
		let idx = get_datatable_col_index(col, vuln_datatable_columns);
		if (idx !== -1) {
			const checkboxId = `#vuln_${col === 'open_status' ? 'status' : col === 'http_url' ? 'vulnerable_url' : col}_checkbox`;
			if($(checkboxId).length === 0 || $(checkboxId).is(":checked")){
				table.column(idx).visible(true);
			} else {
				table.column(idx).visible(false);
			}
		}
	});
}

function vulnerability_format_details(row) {
    let html = '<div class="card p-3 m-2 shadow-sm border-left-primary bg-light">';
    html += '<div class="row">';
    
    // Header section: ID, Discovered Date, URL
    html += '<div class="col-12 mb-3">';
    html += `<p class="text-muted mb-1 font-13"><strong>ID :</strong> <span class="ms-2">${row.id}</span></p>`;
    html += `<p class="text-muted mb-1 font-13"><strong>Vulnerability URL :</strong> <span class="ms-2"><a href="${row.http_url}" target="_blank" class="text-info text-break">${row.http_url}</a></span></p>`;
    html += `<p class="text-muted mb-1 font-13"><strong>Severity :</strong> <span class="ms-2 badge badge-soft-${row.severity === 'Critical' ? 'danger' : row.severity === 'High' ? 'danger' : row.severity === 'Medium' ? 'warning' : 'info'}">${row.severity}</span></p>`;
    html += `<p class="text-muted mb-1 font-13"><strong>Vulnerability Type :</strong> <span class="ms-2">${row.type || 'N/A'}</span></p>`;
    html += `<p class="text-muted mb-1 font-13"><strong>Template ID :</strong> <span class="ms-2">${row.template_id || 'N/A'}</span></p>`;
    if (row.template_url) {
        html += `<p class="text-muted mb-1 font-13"><strong>Template URL :</strong> <span class="ms-2"><a href="${row.template_url}" target="_blank" class="text-info text-break">${row.template_url}</a></span></p>`;
    }
    html += `<p class="text-muted mb-1 font-13"><strong>Vulnerability Source :</strong> <span class="ms-2">${row.source || 'N/A'}</span></p>`;
    html += `<p class="text-muted mb-0 font-13"><strong>Discovered on :</strong> <span class="ms-2">${row.discovered_date || 'Unknown'}</span></p>`;
    html += '</div>';

    html += '<div class="col-12">';
    
    // Description Accordion
    if (row.description) {
        html += `<div class="accordion custom-accordion mt-2" id="vuln_desc_acc_${row.id}">
            <div class="card mb-1 shadow-none border">
                <div class="card-header p-2" id="headingDesc_${row.id}">
                    <h5 class="m-0 font-14">
                        <a class="custom-accordion-title text-reset d-block" data-bs-toggle="collapse" href="#collapseDesc_${row.id}" aria-expanded="true">
                            Vulnerability Description <i class="fe-chevron-down float-end"></i>
                        </a>
                    </h5>
                </div>
                <div id="collapseDesc_${row.id}" class="collapse show">
                    <div class="card-body p-2 font-13 text-muted" style="white-space: pre-wrap;">${htmlEncode(row.description)}</div>
                </div>
            </div>
        </div>`;
    }

    // Impact & Remediation
    if (row.impact || row.remediation) {
        if (row.impact) {
            html += `<div class="accordion custom-accordion mt-2" id="vuln_impact_acc_${row.id}">
                <div class="card mb-1 shadow-none border">
                    <div class="card-header p-2">
                        <h5 class="m-0 font-14">
                            <a class="custom-accordion-title text-reset d-block" data-bs-toggle="collapse" href="#collapseImpact_${row.id}">
                                Vulnerability Impact <i class="fe-chevron-down float-end"></i>
                            </a>
                        </h5>
                    </div>
                    <div id="collapseImpact_${row.id}" class="collapse show">
                        <div class="card-body p-2 font-13 text-muted" style="white-space: pre-wrap;">${htmlEncode(row.impact)}</div>
                    </div>
                </div>
            </div>`;
        }
        if (row.remediation) {
            html += `<div class="accordion custom-accordion mt-2" id="vuln_rem_acc_${row.id}">
                <div class="card mb-1 shadow-none border">
                    <div class="card-header p-2">
                        <h5 class="m-0 font-14">
                            <a class="custom-accordion-title text-reset d-block" data-bs-toggle="collapse" href="#collapseRem_${row.id}">
                                Remediation <i class="fe-chevron-down float-end"></i>
                            </a>
                        </h5>
                    </div>
                    <div id="collapseRem_${row.id}" class="collapse show">
                        <div class="card-body p-2 font-13 text-muted" style="white-space: pre-wrap;">${htmlEncode(row.remediation)}</div>
                    </div>
                </div>
            </div>`;
        }
    }

    // Classification Table Accordion
    html += `<div class="accordion custom-accordion mt-2" id="vuln_class_acc_${row.id}">
        <div class="card mb-1 shadow-none border">
            <div class="card-header p-2">
                <h5 class="m-0 font-14">
                    <a class="custom-accordion-title text-reset d-block" data-bs-toggle="collapse" href="#collapseClass_${row.id}">
                        Vulnerability Classification <i class="fe-chevron-down float-end"></i>
                    </a>
                </h5>
            </div>
            <div id="collapseClass_${row.id}" class="collapse show">
                <div class="card-body p-2">
                    <table class="table table-sm table-borderless mb-0 font-13 text-muted">`;
                    if (row.cve_ids && row.cve_ids.length) {
                        html += `<tr><td style="width:150px">CVE IDs</td><td>`;
                        row.cve_ids.forEach(cve => {
                            html += `<a href="#" onclick="get_and_render_cve_details('${cve.name.toUpperCase()}')" class="badge badge-outline-primary me-1 mt-1">${cve.name.toUpperCase()}</a>`;
                        });
                        html += `</td></tr>`;
                    }
                    if (row.cwe_ids && row.cwe_ids.length) {
                        html += `<tr><td>CWE IDs</td><td>`;
                        row.cwe_ids.forEach(cwe => {
                            html += `<a href="#" onclick="get_and_render_cwe_details('${cwe.name.toUpperCase()}')" class="badge badge-outline-warning me-1 mt-1">${cwe.name.toUpperCase()}</a>`;
                        });
                        html += `</td></tr>`;
                    }
                    if (row.cvss_score) {
                        html += `<tr><td>CVSS Score</td><td><span class="badge badge-outline-${row.cvss_score > 7 ? 'danger' : row.cvss_score > 4 ? 'warning' : 'info'}">${row.cvss_score}</span></td></tr>`;
                    }
                    if (row.cvss_metrics) {
                        html += `<tr><td>CVSS Metrics</td><td><code>${row.cvss_metrics}</code></td></tr>`;
                    }
                    html += `</table>
                </div>
            </div>
        </div>
    </div>`;

    // HTTP Request Accordion
    if (row.request) {
        html += `<div class="accordion custom-accordion mt-2" id="vuln_req_acc_${row.id}">
            <div class="card mb-1 shadow-none border">
                <div class="card-header p-2">
                    <h5 class="m-0 font-14">
                        <a class="custom-accordion-title text-reset d-block" data-bs-toggle="collapse" href="#collapseReq_${row.id}">
                            HTTP Request <i class="fe-chevron-down float-end"></i>
                        </a>
                    </h5>
                </div>
                <div id="collapseReq_${row.id}" class="collapse show">
                    <div class="card-body p-0"><pre class="bg-dark text-light p-2 mb-0" style="max-height:250px; overflow-y:auto; font-size: 11px;"><code>${htmlEncode(row.request)}</code></pre></div>
                </div>
            </div>
        </div>`;
    }

    // HTTP Response Accordion
    if (row.response) {
        html += `<div class="accordion custom-accordion mt-2" id="vuln_res_acc_${row.id}">
            <div class="card mb-1 shadow-none border">
                <div class="card-header p-2">
                    <h5 class="m-0 font-14">
                        <a class="custom-accordion-title text-reset d-block" data-bs-toggle="collapse" href="#collapseRes_${row.id}">
                            HTTP Response <i class="fe-chevron-down float-end"></i>
                        </a>
                    </h5>
                </div>
                <div id="collapseRes_${row.id}" class="collapse">
                    <div class="card-body p-0"><pre class="bg-dark text-light p-2 mb-0" style="max-height:250px; overflow-y:auto; font-size: 11px;"><code>${htmlEncode(row.response)}</code></pre></div>
                </div>
            </div>
        </div>`;
    }

    // References Accordion
    if (row.references && typeof row.references === 'string') {
        html += `<div class="accordion custom-accordion mt-2" id="vuln_ref_acc_${row.id}">
            <div class="card mb-1 shadow-none border">
                <div class="card-header p-2">
                    <h5 class="m-0 font-14">
                        <a class="custom-accordion-title text-reset d-block" data-bs-toggle="collapse" href="#collapseRef_${row.id}">
                            References <i class="fe-chevron-down float-end"></i>
                        </a>
                    </h5>
                </div>
                <div id="collapseRef_${row.id}" class="collapse show">
                    <div class="card-body p-2 font-13 text-muted"><ul class="mb-0 ps-3">`;
                    row.references.split('\n').forEach(ref => {
                        if (ref.trim()) html += `<li class="mb-1"><a href="${ref.trim()}" target="_blank" class="text-info text-break">${ref.trim()}</a></li>`;
                    });
                    html += `</ul></div>
                </div>
            </div>
        </div>`;
    }

    // Exploit Preview
    if (row.exploit_url) {
        html += `<div class="alert alert-soft-danger mt-3 border-danger shadow-sm">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span><i class="fe-zap text-danger me-1"></i> <strong>Potential Exploit Found</strong></span>
                <a href="${row.exploit_url}" target="_blank" class="btn btn-xs btn-danger"><i class="fe-external-link"></i> Source</a>
            </div>
            <p class="mb-2 text-muted small">Validation: <span class="badge badge-soft-dark">${row.validation_status || 'Unverified'}</span></p>
            <button class="btn btn-sm btn-outline-danger w-100" onclick="preview_exploit('${row.exploit_url}', ${row.id})"><i class="fe-eye me-1"></i> Preview Exploit Content</button>
            <div id="exploit-preview-${row.id}" class="mt-2" style="display:none;"><pre class="bg-dark text-white p-2 rounded" style="max-height:250px; overflow-y:auto; font-size: 11px;"></pre></div>
        </div>`;
    }

    // Others: CURL, Extracted
    if (row.curl_command || row.extracted_results) {
        html += `<div class="mt-3">`;
        if (row.curl_command) {
            html += `<h5 class="text-primary mt-2 font-14"><i class="fe-terminal me-1"></i> CURL Command</h5><pre class="bg-dark text-light p-2 rounded" style="font-size: 11px;"><code>${htmlEncode(row.curl_command)}</code></pre>`;
        }
        if (row.extracted_results) {
            html += `<h5 class="text-primary mt-2 font-14"><i class="fe-search me-1"></i> Extracted Results</h5><pre class="bg-white p-2 border rounded" style="max-height:150px; font-size: 11px;"><code>${htmlEncode(row.extracted_results)}</code></pre>`;
        }
        html += `</div>`;
    }

    html += '</div>';
    html += '</div></div>';
    return html;
}

function preview_exploit(url, id) {
    const previewDiv = $(`#exploit-preview-${id}`);
    const pre = previewDiv.find('pre');
    if (previewDiv.is(':visible')) {
        previewDiv.slideUp();
        return;
    }
    previewDiv.slideDown();
    pre.text('Fetching exploit content...');
    
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('HTTP error ' + response.status);
            return response.text();
        })
        .then(text => {
            pre.text(text);
        })
        .catch(err => {
            pre.html(`<span class="text-warning">Unable to preview content directly (likely due to security restrictions / CORS).</span><br><br><span class="text-muted">Error: ${err.message}</span><br><br><a href="${url}" target="_blank" class="btn btn-xs btn-outline-light">Open in New Tab</a>`);
        });
}

// Global click listener for vulnerability details toggle
$(document).on('click', '#vulnerability_results tbody td', function (e) {
    // Don't trigger if clicking a button, link, or checkbox
    if ($(e.target).closest('button, a, input, .dropdown').length) return;
    
    const table = $('#vulnerability_results').DataTable();
    const tr = $(this).closest('tr');
    const row = table.row(tr);

    if (row.child.isShown()) {
        row.child.hide();
        tr.removeClass('shown details-expanded');
    } else {
        row.child(vulnerability_format_details(row.data())).show();
        tr.addClass('shown details-expanded');
    }
});
