<script lang="ts">
	import { Spinner } from '$lib/components/ui/spinner';
	import CopyButton from '$lib/components/copy-button.svelte';
	import ResultBlockView from './result-block.svelte';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { ToolRun } from '$lib/types/toolbox';

	let { run, onNavigate }: { run: ToolRun; onNavigate?: () => void } = $props();

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
			const spec = SURFACE[p.dimension as SurfaceDimension];
			if (spec) return ROUTES.surface(spec.tab, p.query ? { [spec.queryParam]: p.query } : {});
		}
		return p.href ?? '';
	}

	function openPivot() {
		const href = pivotHref();
		if (!href) return;
		onNavigate?.();
		void goto(href);
	}
</script>

{#if pending}
	<div class="flex items-center gap-2 py-6 text-sm text-muted-foreground">
		<Spinner class="size-4" />
		{run.status === 'queued' ? 'Waiting for a worker…' : 'Running…'}
	</div>
{:else if run.status === 'failed'}
	<div
		class="flex items-start gap-2 rounded-md border border-destructive/25 bg-destructive/10 px-3 py-2.5 text-[13px] leading-5 text-destructive"
	>
		<span class="flex h-5 shrink-0 items-center"><CircleX class="size-4" /></span>
		<span class="min-w-0 break-words">{run.error}</span>
	</div>
{:else}
	<div class="space-y-5">
		<div class="flex items-start justify-between gap-3 border-b pb-2">
			<div class="min-w-0">
				<p class="text-sm leading-5 break-words">{run.summary}</p>
				{#if run.pivot}
					<button
						type="button"
						onclick={openPivot}
						class="mt-1 inline-flex items-center gap-1 text-xs text-primary underline-offset-2 hover:underline"
					>
						{run.pivot.label}
						<ArrowUpRight class="size-3" />
					</button>
				{/if}
			</div>
			<div class="flex shrink-0 items-center gap-1">
				{#if took}<span class="font-mono text-[11px] text-muted-foreground">{took}</span>{/if}
				{#if run.raw}
					<CopyButton value={JSON.stringify(run.raw, null, 2)} class="size-6" />
				{/if}
			</div>
		</div>

		{#each run.blocks as block, i (i)}
			<div>
				<ResultBlockView {block} />
			</div>
		{/each}

		{#each run.caveats as caveat (caveat)}
			<p class="text-xs leading-5 text-muted-foreground">{caveat}</p>
		{/each}
	</div>
{/if}
