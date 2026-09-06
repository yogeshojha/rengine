export interface InterestKindEntry {
	key: string;
	label: string;
	help: string;
	weight: number;
	tone: string;
}

export interface InterestSourceEntry {
	key: string;
	label: string;
	help: string;
	judgement: boolean;
}

export interface InterestBandEntry {
	key: string;
	label: string;
	tone: string;
	floor: number;
}

export interface InterestCatalog {
	kinds: InterestKindEntry[];
	sources: InterestSourceEntry[];
	bands: InterestBandEntry[];
	modes: Record<string, string>;
	keyword_fields: Record<string, string>;
	max_score: number;
	providers: string[];
}

export interface InterestSignal {
	source: string;
	kind: string;
	kind_label: string;
	label: string;
	reason: string;
	evidence: string | null;
	weight: number;
	rule_id: string | null;
	model: string | null;
	judgement: boolean;
}

export interface InterestRow {
	subdomain_id: string;
	host: string;
	score: number;
	band: string;
	kinds: string[];
	signals: InterestSignal[];
	sources: string[];
	http_status: number | null;
	page_title: string | null;
	tech: string[];
	webserver: string | null;
	resolved_ips: string[];
	asn: number | null;
	asn_org: string | null;
	is_cdn: boolean;
	screenshot_path: string | null;
	is_new: boolean;
	dismissed: boolean;
}

export interface InterestSummary {
	total: number;
	bands: Record<string, number>;
	sources: Record<string, number>;
	kinds: Record<string, number>;
	dismissed: number;
	judged_hosts: number;
	judged_at: string | null;
	model: string | null;
	ai_available: boolean;
	ai_enabled: boolean;
	stale: boolean;
}

export interface InterestPage {
	rows: InterestRow[];
	total: number;
	summary: InterestSummary;
}

export interface InterestFilter {
	q?: string | null;
	bands?: string[];
	sources?: string[];
	kinds?: string[];
	sort?: string;
	order?: string;
	limit?: number;
	offset?: number;
}

export interface InterestRule {
	id: string;
	project_id: string | null;
	name: string;
	description: string | null;
	mode: string;
	query: string;
	keywords: string[];
	keyword_fields: string[];
	live_only: boolean;
	kind: string;
	kind_label: string;
	weight: number;
	enabled: boolean;
	builtin: boolean;
	notify: boolean;
	updated_at: string;
	matches: number | null;
	error: string | null;
}

export interface InterestRuleCreate {
	name: string;
	description?: string | null;
	mode: string;
	query?: string;
	keywords?: string[];
	keyword_fields?: string[];
	live_only?: boolean;
	kind: string;
	weight?: number | null;
	enabled?: boolean;
	notify?: boolean;
}

export type InterestRuleUpdate = Partial<InterestRuleCreate>;

export interface RulePreview {
	matches: number;
	capped: boolean;
	error: string | null;
	sample: string[];
}

export interface InterestDismissal {
	id: string;
	host: string;
	kind: string;
	target_id: string;
	note: string | null;
	created_at: string;
}

export const RULE_MODE = { KEYWORD: 'keyword', QUERY: 'query' } as const;
export const INTEREST_SOURCE = {
	KEYWORD: 'keyword',
	RULE: 'rule',
	CORRELATION: 'correlation',
	AI: 'ai'
} as const;
export const INTEREST_BAND = {
	CRITICAL: 'critical',
	HIGH: 'high',
	NOTABLE: 'notable'
} as const;

export interface RuleSuggestion {
	name: string;
	kind: string;
	kind_label: string;
	query: string;
	reason: string;
	matches: number;
}
