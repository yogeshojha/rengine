import { formatTargetType } from './target';

export type Intensity = 'passive' | 'normal' | 'aggressive';

export const INTENSITIES: readonly Intensity[] = ['passive', 'normal', 'aggressive'] as const;
export const DEFAULT_INTENSITY: Intensity = 'normal';
export const CUSTOM_INTENSITY = 'custom';

export const INTENSITY_LABELS: Record<string, string> = {
	passive: 'Passive',
	normal: 'Normal',
	aggressive: 'Aggressive',
	[CUSTOM_INTENSITY]: 'Custom'
};

export const INTENSITY_TAGLINE: Record<string, string> = {
	passive: 'No traffic to the target.',
	normal: 'Default rates for every tool.',
	aggressive: 'Higher rates and concurrency.',
	[CUSTOM_INTENSITY]: 'Rates and concurrency set per tool.'
};

export const INTENSITY_HELP: Record<string, string> = {
	passive: 'Findings come from public sources only. No request reaches the target.',
	normal: '150 requests a second per tool. 1,000 packets a second for the port scan.',
	aggressive:
		'400 requests a second per tool. 3,000 packets a second for the port scan, and higher concurrency.',
	[CUSTOM_INTENSITY]: 'Rates and concurrency set per tool. An empty value uses the preset.'
};

export type ToolTransport = { rate?: number | null; threads?: number | null };
export type TransportOverrides = Record<string, ToolTransport>;

export type StageConfig = Record<string, unknown>;

export interface EngineUsage {
	schedules: number;
	scans: number;
}

export interface ScanEngine {
	id: string;
	project_id: string;
	created_by: string;
	name: string;
	description: string | null;
	intensity: Intensity;
	global_headers: string[];
	stages: Record<string, StageConfig>;
	transport_overrides: TransportOverrides;
	yaml_source: string | null;
	tool_options: Record<string, string>;
	usage: EngineUsage;
	builtin: boolean;
	carries_credentials: boolean;
	created_at: string;
	updated_at: string;
	last_used_at: string | null;
}

export interface ScanEngineCreate {
	name: string;
	description?: string | null;
	intensity?: Intensity;
	global_headers?: string[];
	stages?: Record<string, StageConfig>;
	transport_overrides?: TransportOverrides;
	yaml_source?: string | null;
	tool_options?: Record<string, string>;
}

export type ScanEngineUpdate = Partial<Omit<ScanEngineCreate, 'name'>> & { name?: string };

export type FieldType = 'boolean' | 'integer' | 'number' | 'string' | 'array';
export type FieldTier = 'basic' | 'advanced';
export const ADVANCED_TIER: FieldTier = 'advanced';

export interface StageField {
	name: string;
	title: string;
	description: string | null;
	type: FieldType;
	default: unknown;
	options: string[] | null;
	option_labels: Record<string, string> | null;
	minimum: number | null;
	maximum: number | null;
	tier: FieldTier;
	widget: string | null;
	kind: string | null;
	launch: boolean;
	needs: string | null;
	unavailable_reason: string | null;
}

export interface StageTransport {
	tool: string;
	rates: Record<string, number | null>;
	threads: Record<string, number>;
	timeout: number;
}

export interface StageCatalogEntry {
	name: string;
	title: string;
	description: string;
	phase: string;
	level: number;
	applies_to: string[];
	tools: string[];
	api_keys: string[];
	requires_api_keys: boolean;
	touches_target: boolean;
	always_on?: boolean;
	passive_capable?: boolean;
	launch_fields: string[];
	group: string;
	role: string;
	consumes: string[];
	produces: string[];
	transport?: StageTransport | null;
	check_of?: string | null;
	finding_severities?: string[];
	defaults: StageConfig;
	fields: StageField[];
}

export interface StageGroupEntry {
	key: string;
	label: string;
}

export interface ToolOption {
	name: string;
	label: string;
	phase: string;
	example: string;
}

export interface EnginePreset {
	name: string;
	title: string;
	description: string;
	intensity: Intensity;
	stages: Record<string, StageConfig>;
}

export interface EngineCatalog {
	stages: StageCatalogEntry[];
	rate_tools: string[];
	tool_options: ToolOption[];
	presets: EnginePreset[];
	target_types: string[];
	groups: StageGroupEntry[];
	seed_produces: Record<string, string[]>;
}

export interface PreviewResolved {
	header_names: string[];
	global_rate_limit_ceiling: number | null;
	per_tool_rate_limits: Record<string, number>;
	preset_rates: Record<string, number>;
	preset_threads: Record<string, number>;
	excluded_subdomains: string[];
	excluded_paths: string[];
	excluded_ips: string[];
	included_subdomains: string[];
	follow_redirects: boolean | null;
	http_protocol: string;
}

export interface EnginePreviewResult {
	phases: import('./scan').PreviewPhase[];
	resolved_stages: Record<string, StageConfig>;
	resolved: PreviewResolved;
	warnings: string[];
}

export interface EnginePreviewRequest {
	target_type: string;
	context_id?: string | null;
	context?: import('./scan-context').ScanContextCreate | null;
	intensity?: Intensity;
	stages?: Record<string, StageConfig>;
	transport_overrides?: TransportOverrides;
}

export function hasCustomTransport(overrides: TransportOverrides | undefined | null): boolean {
	if (!overrides) return false;
	return Object.values(overrides).some(
		(t) => (t?.rate ?? null) !== null || (t?.threads ?? null) !== null
	);
}

export function basicFields(stage: StageCatalogEntry): StageField[] {
	return stage.fields.filter((f) => f.name !== 'enabled' && f.tier !== ADVANCED_TIER);
}

export function advancedFields(stage: StageCatalogEntry): StageField[] {
	return stage.fields.filter((f) => f.name !== 'enabled' && f.tier === ADVANCED_TIER);
}

export function stageRate(stage: StageCatalogEntry, intensity: string): number {
	return stage.transport?.rates?.[intensity] ?? 0;
}

export const PHASE_LABELS: Record<string, string> = {
	discovery: 'Discovery',
	expansion: 'Expansion',
	depth: 'Depth',
	finalize: 'Finalize'
};

export function phaseLabel(phase: string): string {
	return PHASE_LABELS[phase] ?? phase.replace(/_/g, ' ');
}

export const targetTypeLabel = formatTargetType;

const TARGET_TYPE_ARTICLES: Record<string, string> = {
	domain: 'a',
	ip: 'an',
	ip_range: 'an',
	asn: 'an',
	url: 'a'
};

export function targetTypePhrase(type: string): string {
	const label = type === 'domain' ? 'domain' : targetTypeLabel(type);
	return `${TARGET_TYPE_ARTICLES[type] ?? 'a'} ${label}`;
}
