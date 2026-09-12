<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { cn } from '$lib/utils';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import { Button } from '$lib/components/ui/button';
	import { ROUTES } from '$lib/config/routes';
	import { COMPARABILITY_LABEL, COMPARABILITY_TONE, facetRank } from '$lib/config/compare';
	import { COMPARABILITY } from '$lib/types/compare';
	import type { ScanComparison } from '$lib/types/compare';

	interface Props {
		comparison: ScanComparison;
	}

	let { comparison }: Props = $props();

	const NOTE_LIMIT = 3;
	const FACET_LIMIT = 3;

	let open = $state(false);

	const fmt = (iso: string | null) =>
		iso
			? new Date(iso).toLocaleString('en-US', {
					month: 'short',
					day: 'numeric',
					hour: 'numeric',
					minute: '2-digit'
				})
			: '';

	const MARK = {
		success: 'bg-success',
		warning: 'bg-warning',
		muted: 'bg-muted-foreground/50'
	};

	let tone = $derived(COMPARABILITY_TONE[comparison.comparability]);
	let label = $derived(COMPARABILITY_LABEL[comparison.comparability]);

	let notes = $derived(
		comparison.dimensions
			.filter(
				(d) =>
					d.verdict.compared &&
					d.verdict.comparability !== COMPARABILITY.LIKE_FOR_LIKE &&
					d.verdict.note &&
					d.verdict.comparability !== COMPARABILITY.SETTINGS_DIFFER
			)
			.map((d) => ({ dimension: d.dimension, label: d.label, note: d.verdict.note }))
			.slice(0, NOTE_LIMIT)
	);

	let hiddenNotes = $derived(
		comparison.dimensions.filter(
			(d) =>
				d.verdict.compared &&
				d.verdict.comparability !== COMPARABILITY.LIKE_FOR_LIKE &&
				d.verdict.note &&
				d.verdict.comparability !== COMPARABILITY.SETTINGS_DIFFER
		).length - notes.length
	);

	let coverage = $derived(
		comparison.dimensions.flatMap((d) =>
			d.verdict.coverage.map((c) => ({ ...c, dimension: d.label }))
		)
	);

	let runDiff = $derived(
		[...comparison.run_diff].sort(
			(a, b) => Number(b.material) - Number(a.material) || facetRank(a.key) - facetRank(b.key)
		)
	);
	let materialRunDiff = $derived(runDiff.filter((r) => r.material));

	let evidence = $derived(comparison.setting_diff.length + coverage.length + runDiff.length);

	let intelMoved = $derived(comparison.dimensions.reduce((n, d) => n + d.intel_moved, 0));
</script>

<section class="flex gap-3 border-b bg-muted/30 px-4 py-3 sm:px-5">
	<span class={cn('w-[3px] shrink-0 self-stretch rounded-full', MARK[tone])}></span>

	<div class="flex min-w-0 flex-col gap-1">
		<p class="text-sm leading-5">
			<span class="font-semibold">{label}.</span>
			<span class="text-muted-foreground">{comparison.summary}</span>
		</p>

		{#if comparison.live}
			<p class="text-xs text-muted-foreground">
				The later run is in progress. Missing rows are listed as unconfirmed.
			</p>
		{/if}

		{#if intelMoved > 0}
			<p class="text-xs text-muted-foreground">
				{intelMoved.toLocaleString()}
				{intelMoved === 1 ? 'finding' : 'findings'} re-ranked by exploitation intelligence.
			</p>
		{/if}

		{#if materialRunDiff.length}
			<p class="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-muted-foreground">
				<span class="text-foreground">The runs were set up differently:</span>
				{#each materialRunDiff.slice(0, FACET_LIMIT) as r, i (r.key)}
					{#if i > 0}<span class="opacity-40">·</span>{/if}
					<span>
						{r.label}
						<span class="font-mono">{r.baseline ?? 'none'}</span>
						<span class="opacity-50">→</span>
						<span class="font-mono text-foreground">{r.current ?? 'none'}</span>
					</span>
				{/each}
				{#if materialRunDiff.length > FACET_LIMIT}
					<span>and {materialRunDiff.length - FACET_LIMIT} more</span>
				{/if}
			</p>
		{/if}

		{#if comparison.runs_between > 0}
			<p class="text-xs text-muted-foreground">
				{comparison.runs_between}
				{comparison.runs_between === 1 ? 'run' : 'runs'} of this target ran between these two.
			</p>
		{/if}

		{#each notes as n (n.dimension)}
			<p class="text-xs text-muted-foreground">
				<span class="text-foreground">{n.label}:</span>
				{n.note}
			</p>
		{/each}
		{#if hiddenNotes > 0}
			<p class="text-xs text-muted-foreground">
				{hiddenNotes} more {hiddenNotes === 1 ? 'dimension' : 'dimensions'} carry a note.
			</p>
		{/if}

		{#if comparison.suggestion}
			<div class="mt-1 flex flex-wrap items-center gap-2">
				<span class="text-xs text-muted-foreground">
					A like-for-like run exists: {comparison.suggestion.engine_name} on {fmt(
						comparison.suggestion.started_at
					)}.
				</span>
				<Button
					variant="outline"
					size="sm"
					class="h-6 gap-1 px-2 text-xs"
					href={ROUTES.compare(comparison.current.scan_id, comparison.suggestion.scan_id)}
				>
					Compare with it <ArrowRight class="size-3" />
				</Button>
			</div>
		{/if}

		{#if evidence}
			<Collapsible.Root bind:open class="mt-1">
				<Collapsible.Trigger
					class="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
				>
					<ChevronRight class={cn('size-3.5 transition-transform', open && 'rotate-90')} />
					{open ? 'Hide' : 'Show'} what differs
					<span class="text-muted-foreground tabular-nums">{evidence}</span>
				</Collapsible.Trigger>
				<Collapsible.Content>
					<dl
						class="mt-2 grid grid-cols-[minmax(0,auto)_minmax(0,1fr)] gap-x-4 gap-y-1 border-l pl-3 text-xs"
					>
						{#each runDiff as r (r.key)}
							<dt class="text-muted-foreground">
								Run
								<span class="opacity-50">·</span>
								{r.label}
							</dt>
							<dd class="m-0 font-mono break-all">
								<span class="text-muted-foreground line-through">{r.baseline ?? 'none'}</span>
								<span class="px-1 text-muted-foreground">→</span>
								<span class="font-medium">{r.current ?? 'none'}</span>
							</dd>
						{/each}
						{#each comparison.setting_diff as s (s.stage + s.field)}
							<dt class="text-muted-foreground">
								{s.title}
								<span class="opacity-50">·</span>
								{s.label}
							</dt>
							<dd class="m-0 font-mono break-all">
								<span class="text-muted-foreground line-through">{s.before ?? 'unset'}</span>
								<span class="px-1 text-muted-foreground">→</span>
								<span class="font-medium">{s.after ?? 'unset'}</span>
							</dd>
						{/each}
						{#each coverage as c (c.dimension + c.label)}
							<dt class="text-muted-foreground">
								{c.dimension}
								<span class="opacity-50">·</span>
								{c.label}
							</dt>
							<dd class="m-0 font-mono tabular-nums">
								<span class="text-muted-foreground">{c.baseline}</span>
								<span class="px-1 text-muted-foreground">→</span>
								<span class="font-medium">{c.current}</span>
							</dd>
						{/each}
					</dl>
				</Collapsible.Content>
			</Collapsible.Root>
		{:else if comparison.settings_identical}
			<p class="text-xs text-muted-foreground">
				{comparison.settings_identical.toLocaleString()} stage settings are identical.
			</p>
		{/if}
	</div>
</section>
