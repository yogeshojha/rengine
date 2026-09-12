export interface RelationEvidence {
	kind: string;
	label: string;
	value: string;
	detail: string;
}

export interface RelatedTarget {
	target_id: string;
	target_value: string;
	reasons: RelationEvidence[];
}

export interface TargetRelations {
	items: RelatedTarget[];
	total: number;
	considered: number;
}

export interface ProgramMatch {
	program_id: string;
	handle: string;
	name: string;
	platform: string;
	url: string | null;
	scope_identifier: string;
	asset_type: string;
	wildcard: boolean;
	in_scope: boolean;
	offers_bounties: boolean;
	eligible_for_bounty: boolean | null;
	max_severity: string | null;
}

export interface TargetPrograms {
	items: ProgramMatch[];
	total: number;
}
