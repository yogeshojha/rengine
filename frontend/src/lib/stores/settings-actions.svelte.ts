import type { Snippet } from 'svelte';

let current = $state<Snippet | null>(null);

export const settingsActions = {
	get snippet() {
		return current;
	},
	set(snippet: Snippet) {
		current = snippet;
	},
	clear(snippet: Snippet) {
		if (current === snippet) current = null;
	}
};
