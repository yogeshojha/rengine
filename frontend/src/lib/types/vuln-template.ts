export interface VulnTemplateRead {
	id: string;
	origin: string;
	template_id: string;
	path: string;
	name: string;
	severity: string;
	protocol: string;
	directory: string;
	description: string | null;
	remediation: string | null;
	tags: string[];
	authors: string[];
	references: string[];
	cve_ids: string[];
	cwe_ids: string[];
	cvss_score: number | null;
	requests: number;
	enabled: boolean;
	sets: string[];
	findings: number;
	raw: string | null;
	created_at: string;
	updated_at: string;
}

export interface TemplateFilter {
	q: string | null;
	origins: string[];
	severities: string[];
	protocols: string[];
	sets: string[];
	tags: string[];
	fired: boolean;
	limit: number;
	offset: number;
}

export function emptyTemplateFilter(): TemplateFilter {
	return {
		q: null,
		origins: [],
		severities: [],
		protocols: [],
		sets: [],
		tags: [],
		fired: false,
		limit: 50,
		offset: 0
	};
}

export interface TemplatePage {
	items: VulnTemplateRead[];
	total: number;
}

export interface TemplateSetSpec {
	key: string;
	label: string;
	description: string;
	headless: boolean;
	count: number;
}

export interface TemplateSelection {
	severities: string[];
	template_sets: string[];
	custom_templates: string[];
	include_tags: string[];
	exclude_tags: string[];
	exclude_templates: string[];
	headless: boolean;
}

export interface SelectionBreakdown {
	key: string;
	label: string;
	count: number;
}

export interface SelectionPreview {
	ready: boolean;
	total: number;
	official: number;
	custom: number;
	by_severity: SelectionBreakdown[];
	by_set: SelectionBreakdown[];
	by_protocol: SelectionBreakdown[];
	estimated_requests: number;
	warnings: string[];
}

export interface TemplateLibraryStats {
	ready: boolean;
	total: number;
	official: number;
	custom: number;
	by_severity: SelectionBreakdown[];
	by_protocol: SelectionBreakdown[];
	sets: TemplateSetSpec[];
	tags: SelectionBreakdown[];
	fired: number;
	last_synced_at: string | null;
	syncing: boolean;
}

export interface TemplateSyncResult {
	started: boolean;
	message: string;
}

export interface VulnTemplateRejection {
	filename: string;
	reason: string;
}

export interface VulnTemplateUploadResult {
	accepted: VulnTemplateRead[];
	replaced: number;
	rejected: VulnTemplateRejection[];
}

export interface TemplateSource {
	id: string;
	template_id: string;
	name: string;
	origin: string;
	path: string;
	editable: boolean;
	content: string;
}
