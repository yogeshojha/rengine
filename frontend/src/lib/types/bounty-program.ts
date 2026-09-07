export enum BountyPlatform {
	HackerOne = 'hackerone'
}

export enum ProgramState {
	Public = 'public',
	Private = 'private'
}

export enum SubmissionState {
	Open = 'open',
	Paused = 'paused',
	Closed = 'closed'
}

export enum ScopeState {
	InScope = 'in_scope',
	OutOfScope = 'out_of_scope'
}

export enum AssetGroup {
	Network = 'network',
	Mobile = 'mobile',
	Code = 'code',
	Other = 'other'
}

export interface PlatformSpec {
	key: string;
	label: string;
	url: string;
	supports_private: boolean;
	note: string;
}

export interface AssetTypeSpec {
	key: string;
	label: string;
	group: AssetGroup;
	icon: string;
	note: string;
	targetable: boolean;
	target_type: string | null;
}

export interface BountyVocabulary {
	platforms: PlatformSpec[];
	asset_types: AssetTypeSpec[];
	asset_groups: AssetGroup[];
	program_states: ProgramState[];
	submission_states: SubmissionState[];
	scope_states: ScopeState[];
	max_severities: string[];
}

export interface BountyScope {
	id: string;
	asset_type: string;
	asset_type_label: string;
	asset_group: AssetGroup;
	icon: string;
	asset_identifier: string;
	scope_state: ScopeState;
	eligible_for_bounty: boolean | null;
	max_severity: string | null;
	instruction: string | null;
	target_value: string | null;
	target_type: string | null;
	importable: boolean;
	already_target: boolean;
}

export interface BountyProgram {
	id: string;
	platform: string;
	handle: string;
	name: string;
	url: string | null;
	profile_picture: string | null;
	program_state: ProgramState;
	raw_state: string | null;
	raw_state_label: string;
	joined: boolean;
	joined_at: string | null;
	submission_state: SubmissionState;
	offers_bounties: boolean;
	open_scope: boolean | null;
	gold_standard_safe_harbor: boolean | null;
	currency: string | null;
	started_accepting_at: string | null;
	bookmarked: boolean;
	reports_for_user: number | null;
	earnings_for_user: number | null;
	scopes_synced_at: string | null;
	synced_at: string;
	in_scope_count: number;
	out_of_scope_count: number;
	importable_count: number;
	imported_count: number;
}

export interface BountyProgramDetail extends BountyProgram {
	scopes: BountyScope[];
	unreachable: Record<string, number>;
}

export interface BountyStatus {
	configured: boolean;
	platform: string;
	username: string | null;
	programs: number;
	private_programs: number;
	last_synced_at: string | null;
	error: string | null;
}

export interface OrganizationSummary {
	id: string;
	name: string;
	slug: string;
}

export interface BountyImportResult {
	created: string[];
	existing: string[];
	skipped: string[];
	organization: OrganizationSummary | null;
}

export interface BountyProgramFilters {
	q?: string;
	state?: ProgramState | null;
	submission?: SubmissionState | null;
	bounty?: boolean | null;
	bookmarked?: boolean | null;
	joined?: boolean | null;
	scope?: 'importable' | 'none' | null;
	sort?: string;
}
