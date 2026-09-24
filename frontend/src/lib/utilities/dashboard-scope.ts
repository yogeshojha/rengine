import { DASHBOARD_SCOPE_PARAMS as P } from '$lib/config/dashboard';
import type { TargetScope } from '$lib/utilities/surface-scope';

export function scopeFromParams(sp: URLSearchParams): TargetScope {
	const targetIds = sp.getAll(P.target).filter(Boolean);
	return {
		targetIds: targetIds.length ? targetIds : undefined,
		organizationId: sp.get(P.organization) || undefined,
		tagId: sp.get(P.tag) || undefined
	};
}

export function scopeToParams(sp: URLSearchParams, scope: TargetScope): URLSearchParams {
	const out = new URLSearchParams(sp);
	out.delete(P.target);
	out.delete(P.organization);
	out.delete(P.tag);
	for (const id of scope.targetIds ?? []) out.append(P.target, id);
	if (scope.organizationId) out.set(P.organization, scope.organizationId);
	if (scope.tagId) out.set(P.tag, scope.tagId);
	return out;
}
