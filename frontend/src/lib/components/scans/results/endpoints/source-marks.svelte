<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import {
		PASSIVE_SOURCES,
		SOURCE_ICONS,
		SOURCE_LABELS,
		EndpointSource
	} from '$lib/config/endpoints';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { SourceEvidence } from '$lib/utilities/endpoints';

	interface Props {
		sources: string[];
		evidence?: SourceEvidence[];
		limit?: number;
	}

	let { sources, evidence = [], limit = 4 }: Props = $props();

	let byName = $derived(new Map(evidence.map((e) => [e.source, e])));
	let shown = $derived(sources.slice(0, limit));
	let extra = $derived(Math.max(0, sources.length - limit));

	function icon(source: string) {
		return SOURCE_ICONS[source] ?? SOURCE_ICONS[EndpointSource.OTHER];
	}
</script>

<div class="flex items-center gap-1">
	{#each shown as source (source)}
		{@const Icon = icon(source)}
		{@const detail = byName.get(source)}
		<Tooltip.Root>
			<Tooltip.Trigger class="flex h-5 shrink-0 items-center">
				<span
					class="flex size-5 items-center justify-center rounded border {PASSIVE_SOURCES.has(source)
						? 'border-border/60 text-muted-foreground'
						: 'border-primary/25 bg-primary/5 text-primary'}"
				>
					<Icon class="size-3" />
				</span>
			</Tooltip.Trigger>
			<Tooltip.Content class="max-w-xs">
				<p class="font-medium">{SOURCE_LABELS[source] ?? source}</p>
				{#if detail?.detail}
					<p class="mt-0.5 text-xs text-muted-foreground">{detail.detail}</p>
				{/if}
				{#if detail?.found_on}
					<p class="mt-0.5 truncate font-mono text-xs text-muted-foreground">
						from {detail.found_on}
					</p>
				{/if}
				{#if detail?.observed_at}
					<p class="mt-0.5 text-xs text-muted-foreground">
						{formatShortDate(detail.observed_at)}
					</p>
				{/if}
			</Tooltip.Content>
		</Tooltip.Root>
	{/each}
	{#if extra > 0}
		<span class="text-xs tabular-nums text-muted-foreground">+{extra}</span>
	{/if}
</div>
