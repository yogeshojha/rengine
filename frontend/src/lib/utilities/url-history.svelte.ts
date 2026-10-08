import { pushState, replaceState } from '$app/navigation';
import { page } from '$app/state';

export function writeSearch(sp: URLSearchParams, push: boolean): void {
	const qs = sp.toString();
	if (qs === location.search.replace(/^\?/, '')) return;
	(push ? pushState : replaceState)(qs ? `?${qs}` : location.pathname, page.state);
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
