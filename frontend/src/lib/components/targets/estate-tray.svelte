<script lang="ts">
	import Link2 from '@lucide/svelte/icons/link-2';
	import { SvelteSet } from 'svelte/reactivity';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import EstateSheet from '$lib/components/targets/estate-sheet.svelte';
	import type { EstateDomain, EstateNeighbourCert, EstateProvider } from '$lib/types/estate';

	interface Props {
		count: number;
		subject?: string;
		detail?: string;
		domains: EstateDomain[];
		providers?: EstateProvider[];
		neighbours?: EstateNeighbourCert[];
		onAdded?: () => void;
	}

	let {
		count,
		subject,
		detail,
		domains,
		providers = [],
		neighbours = [],
		onAdded
	}: Props = $props();

	const SHOWN = 3;
	let open = $state(false);
	let added = new SvelteSet<string>();
	let candidates = $derived(
		domains
			.filter((d) => !d.target_id && !added.has(d.domain))
			.toSorted((a, b) => b.strength - a.strength)
	);
	let total = $derived(Math.max(0, count - added.size));
	let strengths = $derived.by(() => {
		const direct = candidates.filter((d) => d.strength).length;
		const shared = candidates.length - direct;
		const parts: string[] = [];
		if (direct) parts.push(`Direct ${direct.toLocaleString()}`);
		if (shared) parts.push(`Shared ${shared.toLocaleString()}`);
		return parts.join(' · ');
	});
	let subline = $derived(detail || strengths);
	let sheetDescription = $derived.by(() => {
		const basis = `Tied to ${subject ?? 'the targets'} by scan evidence.`;
		const shown = domains.filter((d) => !d.target_id).length;
		if (shown >= count) return basis;
		return `${basis} ${shown.toLocaleString()} of ${count.toLocaleString()} shown.`;
	});

	function evidence(d: EstateDomain): string | null {
		const s = d.signals[0];
		if (!s) return null;
		return s.detail ? `${s.label} ${s.detail}` : s.label;
	}
</script>

{#if total > 0}
	<div class="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-card px-4 py-2.5">
		<span
			class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground"
		>
			<Link2 class="size-4" />
		</span>
		<span class="flex min-w-0 flex-col">
			<span class="text-sm">
				<span class="font-semibold tabular-nums">{total.toLocaleString()}</span>
				candidate {total === 1 ? 'target' : 'targets'}
			</span>
			{#if subline}
				<span class="text-xs text-muted-foreground">{subline}</span>
			{/if}
		</span>
		<span class="ml-auto flex flex-wrap items-center gap-1.5">
			{#each candidates.slice(0, SHOWN) as d (d.domain)}
				<Hint text={evidence(d)}>
					{#snippet child(props)}
						<span
							{...props}
							class="rounded-md border px-2 py-0.5 font-mono text-xs {d.strength
								? ''
								: 'border-dashed text-muted-foreground'}"
						>
							{d.domain}
						</span>
					{/snippet}
				</Hint>
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
		title="Candidate targets"
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
