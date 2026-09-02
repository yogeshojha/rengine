export type Intensity = 'passive' | 'normal' | 'aggressive';

export const INTENSITIES: readonly Intensity[] = ['passive', 'normal', 'aggressive'] as const;

export const INTENSITY_LABELS: Record<Intensity, string> = {
	passive: 'Passive',
	normal: 'Normal',
	aggressive: 'Aggressive'
};

export const INTENSITY_HELP: Record<Intensity, string> = {
	passive: 'No active probing — lowest footprint, stealthiest, fewest findings.',
	normal: 'Balanced active scanning — standard rate limits and tool coverage.',
	aggressive: 'Maximum coverage — higher rate, noisier, most thorough but detectable.'
};

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
	global_threads: number;
	global_http_crawl: boolean;
	global_headers: string[];
	stages: Record<string, StageConfig>;
	yaml_source: string | null;
	tool_options: Record<string, string>;
	usage: EngineUsage;
	created_at: string;
	updated_at: string;
	last_used_at: string | null;
}

export interface ScanEngineCreate {
	name: string;
	description?: string | null;
	intensity?: Intensity;
	global_threads?: number;
	global_http_crawl?: boolean;
	global_headers?: string[];
	stages?: Record<string, StageConfig>;
	yaml_source?: string | null;
	tool_options?: Record<string, string>;
}

export type ScanEngineUpdate = Partial<Omit<ScanEngineCreate, 'name'>> & { name?: string };

export type FieldType = 'boolean' | 'integer' | 'number' | 'string' | 'array';
export type FieldScale = 'threads' | 'timeout' | 'rate';

export interface StageField {
	name: string;
	title: string;
	description: string | null;
	type: FieldType;
	default: unknown;
	options: string[] | null;
	minimum: number | null;
	maximum: number | null;
	scale: FieldScale | null;
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
	defaults: StageConfig;
	fields: StageField[];
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
	stages: Record<string, StageConfig>;
}

export interface EngineCatalog {
	phases: string[];
	stages: StageCatalogEntry[];
	rate_tools: string[];
	tool_options: ToolOption[];
	presets: EnginePreset[];
	target_types: string[];
}

export interface EnginePreviewResult {
	phases: import('./scan').PreviewPhase[];
	resolved_stages: Record<string, StageConfig>;
	warnings: string[];
}

export interface EnginePreviewRequest {
	target_type: string;
	context_id?: string | null;
	intensity?: Intensity;
	global_threads?: number;
	stages?: Record<string, StageConfig>;
}

export const SCALE_HELP: Record<FieldScale, string> = {
	threads: 'A scan context can scale this.',
	timeout: 'A scan context can scale this.',
	rate: 'A scan context can cap this.'
};

export const PHASE_LABELS: Record<string, string> = {
	discovery: 'Discovery',
	expansion: 'Expansion',
	depth: 'Depth',
	finalize: 'Finalize'
};

export const TARGET_TYPE_LABELS: Record<string, string> = {
	domain: 'Domain',
	ip: 'IP',
	ip_range: 'CIDR',
	asn: 'ASN',
	url: 'URL'
};

export function phaseLabel(phase: string): string {
	return PHASE_LABELS[phase] ?? phase.replace(/_/g, ' ');
}

export function targetTypeLabel(type: string): string {
	return TARGET_TYPE_LABELS[type] ?? type;
}
