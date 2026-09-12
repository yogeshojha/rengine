<script lang="ts">
	import { Spinner } from '$lib/components/ui/spinner';
	import CopyButton from '$lib/components/copy-button.svelte';
	import ResultBlockView from './result-block.svelte';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { toolIcon } from '$lib/config/toolbox';
	import { toolbox } from '$lib/stores/toolbox.svelte';
	import type { ToolRun } from '$lib/types/toolbox';

	interface Props {
		run: ToolRun;
		onLookup: (value: string, tool: string | null) => void;
		onNavigate: () => void;
	}

	let { run, onLookup, onNavigate }: Props = $props();

	const spec = $derived(toolbox.tool(run.tool));
	const Icon = $derived(toolIcon(spec?.icon ?? ''));
	const pending = $derived(run.status === 'queued' || run.status === 'running');
	const took = $derived(
		run.duration_ms === null
			? ''
			: run.duration_ms < 1000
				? `${run.duration_ms} ms`
				: `${(run.duration_ms / 1000).toFixed(1)} s`
	);

	function pivotHref(): string {
		const p = run.pivot;
		if (!p) return '';
		if (p.dimension) {
			const s = SURFACE[p.dimension as SurfaceDimension];
			if (s) return ROUTES.surface(s.tab, p.query ? { [s.queryParam]: p.query } : {});
		}
		return p.href ?? '';
	}

	function openPivot() {
		const href = pivotHref();
		if (!href) return;
		onNavigate();
		void goto(href);
	}
</script>

<section class="space-y-4">
	<div class="flex items-center gap-2 border-b pb-1.5">
		<Icon class="size-3.5 shrink-0 text-muted-foreground" />
		<h3 class="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
			{run.title}
		</h3>
		<span class="flex-1"></span>
		{#if pending}
			<span class="flex items-center gap-1.5 text-2xs text-muted-foreground">
				<Spinner class="size-3" />
				{run.status === 'queued' ? 'Queued' : 'Running'}
			</span>
		{:else}
			{#if took}<span class="font-mono text-2xs text-muted-foreground">{took}</span>{/if}
			{#if run.raw}
				<CopyButton value={JSON.stringify(run.raw, null, 2)} class="size-5" />
			{/if}
		{/if}
	</div>

	{#if pending}
		<div class="space-y-2">
			<div class="h-20 animate-pulse rounded-lg border bg-muted/25"></div>
			<div class="h-3 w-2/3 animate-pulse rounded bg-muted/40"></div>
			<div class="h-3 w-1/2 animate-pulse rounded bg-muted/40"></div>
		</div>
	{:else if run.status === 'failed'}
		<div
			class="flex items-start gap-2 rounded-md border border-destructive/25 bg-destructive/10 px-3 py-2.5 text-sm leading-5 text-destructive"
		>
			<span class="flex h-5 shrink-0 items-center"><CircleX class="size-4" /></span>
			<span class="min-w-0 break-words">{run.error}</span>
		</div>
	{:else}
		{#each run.blocks as block, i (i)}
			<ResultBlockView {block} {onLookup} />
		{/each}
		{#if run.pivot}
			<button
				type="button"
				onclick={openPivot}
				class="inline-flex items-center gap-1 text-xs text-primary underline-offset-2 hover:underline"
			>
				{run.pivot.label}
				<ArrowUpRight class="size-3" />
			</button>
		{/if}
		{#each run.caveats as caveat (caveat)}
			<p class="text-xs leading-5 text-muted-foreground">{caveat}</p>
		{/each}
	{/if}
</section>
