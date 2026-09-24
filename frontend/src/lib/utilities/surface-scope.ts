export interface TargetScope {
	targetIds?: string[];
	organizationId?: string;
	tagId?: string;
}

export interface SurfaceScope extends TargetScope {
	scanId?: string;
	projectId?: string;
}

export type ScopeArg = string | SurfaceScope;

export function scopeOf(scope: ScopeArg): SurfaceScope {
	return typeof scope === 'string' ? { scanId: scope } : scope;
}

export function isScoped(scope: TargetScope | null | undefined): boolean {
	return !!(scope?.targetIds?.length || scope?.organizationId || scope?.tagId);
}

export function appendTargetScope(sp: URLSearchParams, scope: TargetScope = {}): URLSearchParams {
	for (const id of scope.targetIds ?? []) sp.append('target_id', id);
	if (scope.organizationId) sp.set('organization_id', scope.organizationId);
	if (scope.tagId) sp.set('tag_id', scope.tagId);
	return sp;
}

export function scopeQuery(scope: ScopeArg, extra: Record<string, string> = {}): string {
	const resolved = scopeOf(scope);
	const sp = new URLSearchParams();
	if (resolved.scanId) sp.set('scan_id', resolved.scanId);
	if (resolved.projectId) sp.set('project_id', resolved.projectId);
	appendTargetScope(sp, resolved);
	for (const [key, value] of Object.entries(extra)) sp.set(key, value);
	return sp.toString();
}

export function sameTargetScope(a: TargetScope, b: TargetScope): boolean {
	const ids = (s: TargetScope) => [...(s.targetIds ?? [])].sort().join(',');
	return (
		ids(a) === ids(b) &&
		(a.organizationId ?? '') === (b.organizationId ?? '') &&
		(a.tagId ?? '') === (b.tagId ?? '')
	);
}
