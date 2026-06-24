import { MediaQuery } from 'svelte/reactivity';

export class PrefersReducedMotion extends MediaQuery {
	constructor() {
		super('prefers-reduced-motion: reduce');
	}
}
