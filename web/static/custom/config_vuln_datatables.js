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

const vuln_datatable_page_length = 30;
const vuln_datatable_length_menu = [50, 100, 500, 1000];
