export enum ReportStage {
	Open = 'open',
	Resolved = 'resolved',
	Closed = 'closed'
}

export interface Money {
	currency: string;
	amount: number;
	awards: number;
}

export interface ReportStateCount {
	state: string;
	label: string;
	stage: ReportStage;
	count: number;
}

export interface MonthPoint {
	month: string;
	open: number;
	resolved: number;
	closed: number;
	earned: number;
	awards: number;
}

export interface AwardRead {
	amount: number;
	bonus: number;
	currency: string;
	awarded_at: string | null;
}

export interface ProgramReports {
	handle: string;
	name: string;
	in_hub: boolean;
	reports: number;
	open: number;
	resolved: number;
	closed: number;
	critical: number;
	high: number;
	paid_reports: number;
	earned: Money[];
	last_submitted_at: string | null;
}

export interface BountyAccountSummary {
	platform: string;
	label: string;
	url: string;
	username: string | null;
	reputation: number | null;
	signal: number | null;
	impact: number | null;
	synced_at: string | null;
	error: string | null;
	reports: number;
	programs: number;
	stages: Record<ReportStage, number>;
	states: ReportStateCount[];
	severities: { severity: string; count: number }[];
	earned: Money[];
	paid_reports: number;
	last_submitted_at: string | null;
	monthly: MonthPoint[];
	chart_currency: string | null;
}

export interface BountyReport {
	id: string;
	platform: string;
	external_id: string;
	url: string;
	program_handle: string | null;
	program_name: string | null;
	program_in_hub: boolean;
	title: string;
	state: string;
	state_label: string;
	stage: ReportStage;
	severity: string | null;
	severity_score: number | null;
	weakness: string | null;
	asset_type: string | null;
	asset_identifier: string | null;
	submitted_at: string | null;
	triaged_at: string | null;
	closed_at: string | null;
	disclosed_at: string | null;
	last_program_activity_at: string | null;
	awarded: Money[];
	awards: AwardRead[];
}

export enum ReportView {
	Reports = 'reports',
	Programs = 'programs'
}

export enum ReportSort {
	Submitted = 'submitted',
	Bounty = 'bounty',
	Severity = 'severity',
	Program = 'program'
}

export const PAID_TAB = 'paid';
export const ALL_TAB = 'all';

export interface BountyReportFilters {
	tab: string;
	states: string[];
	programs: string[];
	severities: string[];
	q: string;
	from: string | null;
	to: string | null;
	sort: ReportSort;
	order: 'asc' | 'desc';
}

export type ReportCounts = Record<string, number>;
