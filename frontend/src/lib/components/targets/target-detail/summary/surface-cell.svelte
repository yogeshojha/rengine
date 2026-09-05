<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { surfaceSpec } from '$lib/config/surface';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { SurfaceMetric } from '$lib/types/target-summary';

	interface Props {
		metric: SurfaceMetric;
		note?: string;
	}

	let { metric, note }: Props = $props();

	let spec = $derived(surfaceSpec(metric.key));
	let href = $derived(
		metric.scan_id && spec ? ROUTES.scanTab(metric.scan_id, spec.tab) : undefined
	);
	let observed = $derived(metric.observed_at ? formatShortDate(metric.observed_at) : '');
	let hint = $derived.by(() => {
		const label = spec?.label ?? 'this';
		if (!metric.covered) return `No scan of this target has run ${label} yet`;
		if (metric.scan_status === 'running')
			return 'A scan is still running. This figure will change.';
		if (!metric.current)
			return `The most recent scan did not cover ${label}. Observed on ${observed}.`;
		if (metric.previous != null)
			return `Observed on ${observed}. The previous scan to cover ${label} found ${metric.previous.toLocaleString()}.`;
		return `Observed on ${observed}`;
	});
</script>

{#snippet body()}
	<span class="flex min-w-0 flex-col gap-1.5">
		<span class="truncate text-xs text-muted-foreground group-hover:text-foreground">
			{metric.label}
		</span>
		<span class="text-2xl leading-none font-semibold tracking-tight tabular-nums">
			{metric.value == null ? '—' : metric.value.toLocaleString()}
		</span>
		<span class="flex h-4 items-center gap-2 text-xs">
			{#if !metric.covered}
				<span class="truncate text-muted-foreground">Not scanned</span>
			{:else if note}
				<span class="truncate text-muted-foreground">{note}</span>
			{:else if !metric.current && observed}
				<span class="truncate text-muted-foreground">as of {observed}</span>
			{:else if metric.added != null}
				{#if metric.added > 0}
					<span class="inline-flex items-center text-success tabular-nums">
						<ArrowUpRight class="size-3" />{metric.added.toLocaleString()} new
					</span>
				{/if}
				{#if metric.gone}
					<span class="inline-flex items-center text-muted-foreground tabular-nums">
						<ArrowDownRight class="size-3" />{metric.gone.toLocaleString()} gone
					</span>
				{/if}
				{#if !metric.added && !metric.gone}
					<span class="truncate text-muted-foreground">No change</span>
				{/if}
			{:else if metric.delta}
				<span class="inline-flex items-center text-muted-foreground tabular-nums">
					{#if metric.delta > 0}
						<ArrowUpRight class="size-3" />
					{:else}
						<ArrowDownRight class="size-3" />
					{/if}
					{Math.abs(metric.delta).toLocaleString()}
				</span>
			{/if}
		</span>
	</span>
{/snippet}

<Hint text={hint}>
	{#snippet child(props)}
		{#if href}
			<a
				{...props}
				{href}
				class="group flex min-w-0 items-end justify-between gap-3 border-t border-l px-5 py-4 transition-colors hover:bg-muted/40"
			>
				{@render body()}
			</a>
		{:else}
			<span
				{...props}
				class="group flex min-w-0 items-end justify-between gap-3 border-t border-l px-5 py-4"
			>
				{@render body()}
			</span>
		{/if}
	{/snippet}
</Hint>
