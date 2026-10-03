<script lang="ts">
	import { Spinner } from '$lib/components/ui/spinner';
	import { Skeleton } from '$lib/components/ui/skeleton';
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
	const organization = $derived(
		typeof run.raw?.organization === 'string' ? run.raw.organization : null
	);
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
		<h3 class="text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">
			{run.title}
		</h3>
		<span class="flex-1"></span>
		<span role="status" class="flex items-center gap-1.5 text-2xs text-muted-foreground">
			{#if pending}
				<Spinner class="size-3" aria-hidden="true" />
				{run.status === 'queued' ? 'Queued' : 'Running'}
			{:else if run.status === 'completed'}
				<span class="sr-only">Completed</span>
			{/if}
		</span>
		{#if !pending}
			{#if took}<span class="font-mono text-2xs text-muted-foreground">{took}</span>{/if}
			{#if run.raw}
				<span class="flex h-5 shrink-0 items-center">
					<CopyButton value={JSON.stringify(run.raw, null, 2)} />
				</span>
			{/if}
		{/if}
	</div>

	{#if pending}
		<div class="space-y-2" aria-busy="true">
			<Skeleton class="h-20 rounded-lg" />
			<Skeleton class="h-3 w-2/3" />
			<Skeleton class="h-3 w-1/2" />
		</div>
	{:else if run.status === 'failed'}
		<div
			role="alert"
			class="flex items-start gap-2 rounded-md border border-destructive/25 bg-destructive/10 px-3 py-2.5 text-sm leading-5 text-destructive"
		>
			<span class="flex h-5 shrink-0 items-center"><CircleX class="size-4" /></span>
			<span class="min-w-0 break-words">{run.error}</span>
		</div>
	{:else}
		{#each run.blocks as block, i (i)}
			<ResultBlockView {block} {organization} {onLookup} {onNavigate} />
		{/each}
		{#if run.pivot}
			<button
				type="button"
				onclick={openPivot}
				class="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80"
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
