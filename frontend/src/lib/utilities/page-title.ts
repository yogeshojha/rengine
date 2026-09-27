import { capabilitiesStore } from '$lib/stores/capabilities.svelte';

export function pageTitle(label: string): string {
	return `${label} · ${capabilitiesStore.instanceName}`;
}
