import { getContext, setContext } from 'svelte';
import { formatDateTime } from '$lib/utilities/dates';
import type { EstateScopeRead } from '$lib/types/ask';

const KEY = Symbol('ask-link-scan');
const VALUES = Symbol('ask-link-values');

/** The scan a thread reads alone, for every link its blocks open. */
export function setLinkScan(get: () => string | null): void {
	setContext(KEY, get);
}

export function linkScan(): () => string | null {
	return getContext<(() => string | null) | undefined>(KEY) ?? (() => null);
}

/** The target values a scoped thread's links name, null when unscoped. */
export function setLinkValues(get: () => string[] | null): void {
	setContext(VALUES, get);
}

export function linkValues(): () => string[] | null {
	return getContext<(() => string[] | null) | undefined>(VALUES) ?? (() => null);
}

/** The target count beside a scope label that does not state it. */
export function scopeCount(scope: EstateScopeRead): string | null {
	if (scope.scan_id) return null;
	if (scope.filtered && !scope.tag_id && !scope.organization_id) return null;
	return `${scope.targets} ${scope.targets === 1 ? 'target' : 'targets'}`;
}

/** A thread's scope as the viewer reads it, a scan's time in local time. */
export function scopeLabel(scope: EstateScopeRead): string {
	if (scope.scan_at && scope.scan_target)
		return `${scope.scan_target} · scan of ${formatDateTime(scope.scan_at)}`;
	return scope.label;
}
