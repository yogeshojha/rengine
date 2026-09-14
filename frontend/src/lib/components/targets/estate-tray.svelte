<script lang="ts">
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { SvelteSet } from 'svelte/reactivity';
	import { Button } from '$lib/components/ui/button';
	import EstateSheet from '$lib/components/targets/estate-sheet.svelte';
	import type { EstateDomain, EstateNeighbourCert, EstateProvider } from '$lib/types/estate';

	interface Props {
		count: number;
		subject: string;
		detail?: string;
		domains: EstateDomain[];
		providers?: EstateProvider[];
		neighbours?: EstateNeighbourCert[];
		sheetDescription?: string;
		onAdded?: () => void;
	}

	let {
		count,
		subject,
		detail,
		domains,
		providers = [],
		neighbours = [],
		sheetDescription,
		onAdded
	}: Props = $props();

	const SHOWN = 3;
	let open = $state(false);
	let added = new SvelteSet<string>();
	let candidates = $derived(domains.filter((d) => !d.target_id && !added.has(d.domain)));
	let total = $derived(Math.max(0, count - added.size));
</script>

{#if total > 0}
	<div class="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-card px-4 py-2.5">
		<span
			class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
		>
			<Sparkles class="size-4" />
		</span>
		<span class="flex min-w-0 flex-col">
			<span class="text-sm">
				Found <span class="font-semibold tabular-nums">{total.toLocaleString()}</span>
				{total === 1 ? 'domain' : 'domains'} associated with {subject}
			</span>
			{#if detail}
				<span class="text-xs text-muted-foreground">{detail}</span>
			{/if}
		</span>
		<span class="ml-auto flex flex-wrap items-center gap-1.5">
			{#each candidates.slice(0, SHOWN) as d (d.domain)}
				<span class="rounded-md border px-2 py-0.5 font-mono text-xs">{d.domain}</span>
			{/each}
			{#if total > SHOWN}
				<span class="text-xs text-muted-foreground">+{total - SHOWN}</span>
			{/if}
			<Button size="sm" onclick={() => (open = true)}>Review</Button>
		</span>
	</div>
	<EstateSheet
		{open}
		onOpenChange={(o) => (open = o)}
		title="Domains associated with {subject}"
		description={sheetDescription}
		{domains}
		{providers}
		{neighbours}
		onAdded={(d) => {
			added.add(d);
			onAdded?.();
		}}
	/>
{/if}
