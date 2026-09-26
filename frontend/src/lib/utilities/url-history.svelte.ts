import { pushState, replaceState } from '$app/navigation';
import { page } from '$app/state';

const HISTORY_INDEX = 'sveltekit:history';

function readIndex(): number {
	const state = history.state as Record<string, unknown> | null;
	return typeof state?.[HISTORY_INDEX] === 'number' ? (state[HISTORY_INDEX] as number) : 0;
}

const position = $state({ index: 0 });

if (typeof window !== 'undefined') {
	position.index = readIndex();
	window.addEventListener('popstate', () => (position.index = readIndex()));
}

export function historyIndex(): number {
	return position.index;
}

export function markEntry(): number {
	position.index = readIndex();
	return position.index;
}

export function writeSearch(sp: URLSearchParams, push: boolean): void {
	const qs = sp.toString();
	if (qs === location.search.replace(/^\?/, '')) return;
	(push ? pushState : replaceState)(qs ? `?${qs}` : location.pathname, page.state);
	position.index = readIndex();
}

export class UrlSync {
	#settled = false;
	readonly #keys: readonly string[];

	constructor(keys: readonly string[], settled = false) {
		this.#keys = keys;
		this.#settled = settled;
	}

	write(sp: URLSearchParams): void {
		// eslint-disable-next-line svelte/prefer-svelte-reactivity
		const current = new URLSearchParams(location.search);
		const settled = this.#settled;
		this.#settled = true;
		const changed = this.#keys.some((k) => (current.get(k) ?? '') !== (sp.get(k) ?? ''));
		writeSearch(sp, settled && changed);
	}
}

export function onPopSearch(restore: (sp: URLSearchParams) => void): () => void {
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const handler = () => restore(new URLSearchParams(location.search));
	window.addEventListener('popstate', handler);
	return () => window.removeEventListener('popstate', handler);
}
