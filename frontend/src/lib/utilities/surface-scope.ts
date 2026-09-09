export interface SurfaceScope {
	scanId?: string;
	projectId?: string;
}

export type ScopeArg = string | SurfaceScope;

export function scopeOf(scope: ScopeArg): SurfaceScope {
	return typeof scope === 'string' ? { scanId: scope } : scope;
}

export function scopeQuery(scope: ScopeArg, extra: Record<string, string> = {}): string {
	const { scanId, projectId } = scopeOf(scope);
	const sp = new URLSearchParams();
	if (scanId) sp.set('scan_id', scanId);
	if (projectId) sp.set('project_id', projectId);
	for (const [key, value] of Object.entries(extra)) sp.set(key, value);
	return sp.toString();
}

export function isProjectScope(scope: ScopeArg): boolean {
	return !scopeOf(scope).scanId;
}

export function scopeReady(scope: ScopeArg): boolean {
	const { scanId, projectId } = scopeOf(scope);
	return Boolean(scanId || projectId);
}
