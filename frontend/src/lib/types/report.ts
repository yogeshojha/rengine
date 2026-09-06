export interface SectionEntry {
	section: string;
	enabled: boolean;
	title: string;
	config: Record<string, unknown>;
}

export interface SectionFieldOption {
	value: string;
	label: string;
}

export interface SectionField {
	name: string;
	label: string;
	help: string;
	type: 'string' | 'number' | 'flag' | 'list';
	default: unknown;
	options: SectionFieldOption[];
	minimum: number | null;
	maximum: number | null;
	widget: string;
	depends_on: string;
}

export interface SectionCatalogEntry {
	name: string;
	title: string;
	description: string;
	group: string;
	requires: string[];
	repeatable: boolean;
	default_enabled: boolean;
	always_available: boolean;
	fields: SectionField[];
	defaults: Record<string, unknown>;
}

export interface ReportStyle {
	theme: string;
	page_size: string;
	orientation: string;
	margin_top: number;
	margin_right: number;
	margin_bottom: number;
	margin_left: number;
	density: string;
	base_font_size: number;
	line_height: number;
	heading_font: string;
	body_font: string;
	mono_font: string;
	accent: string;
	accent_soft: string;
	severity_colors: Record<string, string>;
	chart_palette: string[];
	mono_safe: boolean;
	table_zebra: boolean;
	section_numbering: boolean;
	figure_numbering: boolean;
	page_numbers: boolean;
	show_header: boolean;
	show_footer: boolean;
	header_left: string;
	header_center: string;
	header_right: string;
	footer_left: string;
	footer_center: string;
	footer_right: string;
	cover_layout: string;
	cover_image: string;
	watermark_text: string;
	watermark_opacity: number;
	link_urls: boolean;
	hyphenate: boolean;
}

export interface Revision {
	version: string;
	date: string;
	author: string;
	note: string;
}

export interface ReportBranding {
	company_name: string;
	company_logo: string;
	client_name: string;
	prepared_for: string;
	prepared_by: string;
	author: string;
	contact_email: string;
	contact_url: string;
	classification: string;
	document_id: string;
	version: string;
	distribution: string[];
	revisions: Revision[];
	confidentiality_statement: string;
	disclaimer: string;
}

export interface NarrativeOptions {
	ai_enabled: boolean;
	audience: string;
	depth: string;
	explain_findings: boolean;
	max_explained_issues: number;
	model: string;
	disclose_ai: boolean;
	house_style: string;
}

export interface ReportTemplate {
	id: string;
	project_id: string | null;
	slug: string;
	name: string;
	description: string;
	title: string;
	subtitle: string;
	preset: string;
	tags: string[];
	scope: string;
	sections: SectionEntry[];
	theme: string;
	style: ReportStyle;
	branding: ReportBranding;
	narrative: NarrativeOptions;
	formats: string[];
	is_builtin: boolean;
	is_default: boolean;
	used_count: number;
	last_used_at: string | null;
	created_at: string;
	updated_at: string;
}

export interface ReportFile {
	format: string;
	filename: string;
	bytes: number;
	pages: number | null;
}

export interface Report {
	id: string;
	project_id: string;
	template_id: string | null;
	template_name: string;
	scope: string;
	scan_id: string | null;
	target_id: string | null;
	subject: string;
	title: string;
	status: string;
	progress: number;
	step: string;
	error: string | null;
	files: ReportFile[];
	page_count: number | null;
	stats: Record<string, unknown>;
	theme: string;
	formats: string[];
	ai_used: boolean;
	ai_model: string | null;
	ai_calls: number;
	ai_input_tokens: number;
	ai_output_tokens: number;
	ai_cached_calls: number;
	duration_seconds: number | null;
	created_by: string | null;
	created_at: string;
	started_at: string | null;
	completed_at: string | null;
	expires_at: string | null;
}

export interface ThemeSummary {
	slug: string;
	name: string;
	description: string;
	author: string;
	origin: string;
	accent: string;
	page: string;
	ink: string;
	cover_layout: string;
	heading_font: string;
	body_font: string;
	severity: Record<string, string>;
	chart: string[];
}

export interface ReportTheme {
	id: string;
	slug: string;
	name: string;
	description: string;
	author: string;
	version: string;
	origin: string;
	tokens: Record<string, unknown>;
	created_at: string;
	updated_at: string;
}

export interface FrameworkControl {
	id: string;
	title: string;
	note: string;
}

export interface FrameworkSummary {
	key: string;
	name: string;
	version: string;
	description: string;
	url: string;
	scope_note: string;
	controls: FrameworkControl[];
}

export interface KeyLabel {
	key: string;
	label: string;
	help?: string;
}

export interface ReportPreset {
	slug: string;
	name: string;
	description: string;
	scope: string;
	theme: string;
	title: string;
	subtitle: string;
	audience: string;
	depth: string;
	density: string;
	formats: string[];
	tags: string[];
	sections: { section: string; config: Record<string, unknown> }[];
}

export interface ReportCatalog {
	sections: SectionCatalogEntry[];
	groups: KeyLabel[];
	themes: ThemeSummary[];
	presets: ReportPreset[];
	fonts: { key: string; label: string; role: string; note: string }[];
	page_sizes: KeyLabel[];
	formats: KeyLabel[];
	scopes: KeyLabel[];
	slot_tokens: { token: string; label: string }[];
	frameworks: FrameworkSummary[];
	cover_layouts: KeyLabel[];
	cover_art: KeyLabel[];
	table_styles: KeyLabel[];
	finding_styles: KeyLabel[];
	heading_styles: KeyLabel[];
	audiences: KeyLabel[];
	depths: KeyLabel[];
	densities: KeyLabel[];
	ai_available: boolean;
	ai_model: string;
}

export interface ReportEstimate {
	sections: number;
	findings: number;
	assets: number;
	pages_estimated: number;
	ai_calls: number;
	ai_input_tokens: number;
	ai_output_tokens: number;
	ai_cost_usd: number;
	ai_cached: number;
	warnings: string[];
}

export interface ReportCreate {
	template_id?: string | null;
	scope?: string;
	scan_id?: string | null;
	target_id?: string | null;
	title?: string;
	subtitle?: string;
	sections?: SectionEntry[];
	theme?: string;
	style?: ReportStyle;
	branding?: ReportBranding;
	narrative?: NarrativeOptions;
	formats?: string[];
}
