export type ToolExecution = 'inline' | 'queued';
export type RunStatus = 'queued' | 'running' | 'completed' | 'failed';
export type BlockKind = 'facts' | 'table' | 'tags' | 'code' | 'note';
export type Tone = 'neutral' | 'success' | 'warning' | 'critical' | 'info' | 'muted';

export interface ToolField {
	name: string;
	title: string;
	description: string | null;
	type: 'string' | 'integer' | 'number' | 'boolean' | 'array';
	default: unknown;
	options: string[] | null;
	option_labels: Record<string, string> | null;
	minimum: number | null;
	maximum: number | null;
	required: boolean;
}

export interface ToolSpec {
	name: string;
	title: string;
	description: string;
	group: string;
	icon: string;
	execution: ToolExecution;
	touches_target: boolean;
	placeholder: string;
	examples: string[];
	fields: ToolField[];
}

export interface ToolGroupSpec {
	key: string;
	label: string;
}

export interface ToolboxCatalog {
	groups: ToolGroupSpec[];
	tools: ToolSpec[];
}

export interface Fact {
	label: string;
	value: string;
	tone: Tone;
	note: string | null;
	href: string | null;
	mono: boolean;
}

export interface Cell {
	value: string;
	tone: Tone;
	note: string | null;
	href: string | null;
	mono: boolean;
	icon: string | null;
}

export interface Tag {
	value: string;
	tone: Tone;
	icon: string | null;
	href: string | null;
	note: string | null;
}

export interface ResultBlock {
	kind: BlockKind;
	title: string | null;
	tone: Tone;
	facts: Fact[];
	columns: string[];
	rows: Cell[][];
	tags: Tag[];
	text: string | null;
	lang: string | null;
	empty: string | null;
	total: number | null;
}

export interface Pivot {
	label: string;
	href: string | null;
	dimension: string | null;
	query: string | null;
}

export interface ToolRun {
	id: string;
	tool: string;
	title: string;
	label: string;
	input: Record<string, unknown>;
	status: RunStatus;
	summary: string | null;
	blocks: ResultBlock[];
	caveats: string[];
	pivot: Pivot | null;
	raw: Record<string, unknown> | null;
	error: string | null;
	queued_at: string;
	started_at: string | null;
	finished_at: string | null;
	duration_ms: number | null;
}

export interface ToolRunRequest {
	tool: string;
	input: Record<string, unknown>;
	project_id?: string;
}
