export enum BountyPlatform {
	HackerOne = 'hackerone',
	Bugcrowd = 'bugcrowd',
	Intigriti = 'intigriti',
	YesWeHack = 'yeswehack'
}

export enum ProgramSource {
	Api = 'api',
	Feed = 'feed'
}

export enum ProgramState {
	Public = 'public',
	Private = 'private'
}

export enum SubmissionState {
	Open = 'open',
	Paused = 'paused',
	Closed = 'closed',
	Unknown = 'unknown'
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
	events: BountyEventSpec[];
	sync_intervals: SyncInterval[];
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
	platform_label: string;
	source: ProgramSource;
	source_label: string;
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
	min_payout: number | null;
	max_payout: number | null;
	payout_currency: string | null;
	safe_harbor: string | null;
	requires_2fa: boolean | null;
	scopes_synced_at: string | null;
	synced_at: string;
	in_scope_count: number;
	out_of_scope_count: number;
	importable_count: number;
	imported_count: number;
	watched: boolean;
	watch_id: string | null;
}

export interface BountyProgramDetail extends BountyProgram {
	scopes: BountyScope[];
	unreachable: Record<string, number>;
}

export enum SyncInterval {
	Off = 'off',
	SixHours = 'six_hours',
	Daily = 'daily',
	Weekly = 'weekly'
}

export interface PlatformCount {
	platform: string;
	label: string;
	source: ProgramSource;
	programs: number;
}

export interface BountyEventSpec {
	kind: string;
	label: string;
	description: string;
	icon: string;
	tone: string;
	actionable: boolean;
}

export interface BountyEvent {
	id: string;
	platform: string;
	handle: string;
	program_name: string;
	kind: string;
	label: string;
	description: string;
	icon: string;
	tone: string;
	actionable: boolean;
	asset_type: string | null;
	asset_identifier: string | null;
	detail: string | null;
	created_at: string;
}

export interface BountySettings {
	sync_interval: SyncInterval;
	feed_interval: SyncInterval;
	feed_synced_at: string | null;
	feed_next_sync_at: string | null;
	feed_programs: number;
	feed_source: string;
	feed_url: string;
	feed_license: string;
	notify: boolean;
	notify_events: string[];
	notifiable_events: string[];
	last_synced_at: string | null;
	next_sync_at: string | null;
	programs: number;
	events_recorded: number;
}

export interface BountySettingsUpdate {
	sync_interval?: string;
	feed_interval?: string;
	notify?: boolean;
	notify_events?: string[];
}

export interface BountyStatus {
	configured: boolean;
	platform: string;
	username: string | null;
	programs: number;
	private_programs: number;
	last_synced_at: string | null;
	sync_interval: SyncInterval;
	next_sync_at: string | null;
	unseen_events: number;
	platforms: PlatformCount[];
	feed_interval: SyncInterval;
	feed_synced_at: string | null;
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
	platforms?: string[];
	sources?: string[];
	scope?: 'importable' | 'none' | null;
	sort?: string;
}
