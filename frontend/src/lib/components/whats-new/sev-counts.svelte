<script lang="ts">
	import { SEVERITY_CHIP, SEVERITY_LABELS, SEVERITY_ORDER } from '$lib/config/vulnerabilities';

	interface Props {
		severities: Record<string, number>;
		labelled?: boolean;
	}

	let { severities, labelled = false }: Props = $props();

	let shown = $derived(
		SEVERITY_ORDER.filter((s) => (severities[s] ?? 0) > 0 && SEVERITY_CHIP[s]).map((s) => ({
			sev: s,
			n: severities[s]
		}))
	);
</script>

{#if shown.length === 0}
	<span class="text-xs text-muted-foreground">None</span>
{:else}
	<span class="flex flex-wrap items-center gap-1">
		{#each shown as c (c.sev)}
			<span
				class="inline-flex h-6 min-w-8 items-center justify-center gap-1 rounded-md px-1.5 font-mono text-xs font-semibold tabular-nums {SEVERITY_CHIP[
					c.sev
				].chip}"
				aria-label="{c.n} {SEVERITY_LABELS[c.sev].toLowerCase()}"
			>
				{#if labelled}<span class="font-sans text-2xs font-medium opacity-70"
						>{SEVERITY_LABELS[c.sev]}</span
					>{/if}
				{c.n.toLocaleString()}
			</span>
		{/each}
	</span>
{/if}
