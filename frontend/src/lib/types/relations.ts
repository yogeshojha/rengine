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
