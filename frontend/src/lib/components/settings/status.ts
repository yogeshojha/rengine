export type CheckState = 'ok' | 'failed' | 'untested' | 'off';

export const CHECK_DOT: Record<CheckState, string> = {
	ok: 'bg-success',
	failed: 'bg-destructive',
	untested: 'bg-muted-foreground/60',
	off: 'bg-muted-foreground/30'
};

export function checkState(enabled: boolean, ok: boolean | null): CheckState {
	if (!enabled) return 'off';
	if (ok === true) return 'ok';
	if (ok === false) return 'failed';
	return 'untested';
}
