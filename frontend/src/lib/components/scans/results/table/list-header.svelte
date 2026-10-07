<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { ACTIONS_BODY, ACTIONS_PIN, columnCell, type TableColumn } from './columns';

	interface Props {
		lead: TableColumn[];
		columns: TableColumn[];
		selectAllChecked?: boolean | 'indeterminate';
		selectAllLabel?: string;
		onSelectAll?: () => void;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		sticky?: boolean;
		top?: number;
		follow?: HTMLElement | null;
	}

	let {
		lead,
		columns,
		selectAllChecked,
		selectAllLabel = '',
		onSelectAll,
		sortKey,
		sortDir,
		onSort,
		sticky = false,
		top = 0,
		follow = null
	}: Props = $props();

	let wrap = $state<HTMLElement | null>(null);

	$effect(() => {
		const viewport = follow?.querySelector<HTMLElement>('[data-slot=scroll-area-viewport]');
		const el = wrap;
		const inner = el?.firstElementChild as HTMLElement | null;
		if (!viewport || !el || !inner) return;
		const sync = () => {
			el.scrollLeft = viewport.scrollLeft;
		};
		const fit = () => {
			inner.style.width = `${Math.max(viewport.scrollWidth, viewport.clientWidth)}px`;
			sync();
		};
		fit();
		const ro = new ResizeObserver(fit);
		ro.observe(viewport);
		if (viewport.firstElementChild) ro.observe(viewport.firstElementChild);
		viewport.addEventListener('scroll', sync, { passive: true });
		return () => {
			ro.disconnect();
			viewport.removeEventListener('scroll', sync);
			inner.style.width = '';
		};
	});
</script>

{#snippet cell(col: TableColumn)}
	{#if col.sort}
		<button
			type="button"
			class="flex items-center gap-1 rounded-sm uppercase outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 {sortKey ===
			col.sort
				? 'text-foreground'
				: ''}"
			onclick={() => onSort(col.sort ?? col.key)}
		>
			{col.label}
			{#if sortKey === col.sort}
				{#if sortDir === 1}<ArrowUp class="size-3" />{:else}<ArrowDown class="size-3" />{/if}
				<span class="sr-only">, sorted {sortDir === 1 ? 'ascending' : 'descending'}</span>
			{/if}
		</button>
	{:else}
		{col.label}
	{/if}
{/snippet}

<div
	bind:this={wrap}
	class={sticky ? 'z-10 overflow-x-hidden bg-card md:sticky' : ''}
	style={sticky ? `top: calc(var(--scan-tabs-h, 0px) + ${top}px)` : undefined}
>
	<div
		class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
	>
		{#if onSelectAll}
			<div class="hidden shrink-0 sm:flex">
				<Checkbox
					checked={selectAllChecked === true}
					indeterminate={selectAllChecked === 'indeterminate'}
					onCheckedChange={onSelectAll}
					aria-label={selectAllLabel}
				/>
			</div>
		{/if}
		{#each lead as col (col.key)}
			<div
				class="{col.grow === undefined
					? ''
					: col.grow
						? 'min-w-0 flex-1'
						: 'shrink-0'} {col.width} {col.align === 'right' ? 'flex justify-end' : ''}"
			>
				{@render cell(col)}
			</div>
		{/each}
		{#each columns as col (col.key)}
			<div class={columnCell(col)}>
				{@render cell(col)}
			</div>
		{/each}
		<div class={ACTIONS_PIN}>
			<div class="{ACTIONS_BODY} bg-muted/20"><span class="sr-only">Actions</span></div>
		</div>
	</div>
</div>
