<script lang="ts">
	import SevCountChip from '$lib/components/sev-count-chip.svelte';
	import { SEVERITY_CHIP, SEVERITY_ORDER } from '$lib/config/vulnerabilities';

	interface Props {
		severities: Record<string, number>;
	}

	let { severities }: Props = $props();

	let shown = $derived(
		SEVERITY_ORDER.filter((s) => (severities[s] ?? 0) > 0 && SEVERITY_CHIP[s]).map((s) => ({
			sev: s,
			n: severities[s]
		}))
	);
</script>

<span class="flex flex-wrap items-center gap-1">
	{#each shown as c (c.sev)}
		<SevCountChip severity={c.sev} count={c.n} size="sm" />
	{/each}
</span>
