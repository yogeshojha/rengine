import type { SurfaceSpec } from '$lib/config/surface';
import { MAX_NAME, SCOPE_LABELS, ScopeKind } from '$lib/config/tripwires';
import type { TripwireScope } from '$lib/types/tripwire';

export const SHOWN_LABELS = 2;

export function scopeText(scope: TripwireScope, labels: string[]): string {
	if (scope.kind === ScopeKind.All) return SCOPE_LABELS[ScopeKind.All];
	if (labels.length === 0) return 'No target chosen';
	if (scope.kind === ScopeKind.Targets) {
		return labels.length <= SHOWN_LABELS
			? labels.join(', ')
			: `${labels.slice(0, SHOWN_LABELS).join(', ')} and ${labels.length - SHOWN_LABELS} more`;
	}
	const kind = SCOPE_LABELS[scope.kind as ScopeKind];
	return kind ? `${kind} ${labels[0]}` : labels[0];
}

export function defaultTripwireName(spec: SurfaceSpec, query: string): string {
	const text = query.trim();
	const base = text ? `${spec.label} · ${text}` : `New ${spec.nounPlural}`;
	return base.length > MAX_NAME ? `${base.slice(0, MAX_NAME - 1)}…` : base;
}
