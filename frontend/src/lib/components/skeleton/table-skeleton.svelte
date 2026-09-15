<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import {
		ACTIONS_BODY,
		ACTIONS_PIN,
		columnCell,
		rowPadding,
		type TableColumn
	} from '$lib/components/scans/results/table/columns';

	interface Props {
		lead?: TableColumn[];
		columns?: TableColumn[];
		rows?: number;
		density?: string;
		selectable?: boolean;
		actions?: boolean;
		header?: boolean;
		subline?: boolean;
		class?: string;
	}

	let {
		lead = [],
		columns = [],
		rows = 8,
		density = 'cozy',
		selectable = false,
		actions = true,
		header = true,
		subline = true,
		class: className = ''
	}: Props = $props();

	const BAR = ['w-full', 'w-4/5', 'w-2/3', 'w-11/12', 'w-3/5'];

	let pad = $derived(rowPadding(density));

	function bar(row: number, col: number): string {
		return BAR[(row * 3 + col * 2) % BAR.length];
	}

	function leadCell(col: TableColumn): string {
		const grow = col.grow === undefined ? '' : col.grow ? 'min-w-0 flex-1' : 'shrink-0';
		return `${grow} ${col.width}`;
	}

	let subIndex = $derived.by(() => {
		const marked = lead.findIndex((col) => col.grow === true);
		if (marked >= 0) return marked;
		const flexed = lead.findIndex((col) => /\bflex-(?:1|\[)/.test(col.width));
		return flexed >= 0 ? flexed : 0;
	});
</script>

<div class={className} aria-busy="true">
	{#if header}
		<div
			class="flex items-center gap-3 border-b bg-muted/30 px-4 py-2 text-xs font-medium tracking-wider text-muted-foreground uppercase"
		>
			{#if selectable}
				<div class="hidden size-4 shrink-0 sm:block"></div>
			{/if}
			{#each lead as col (col.key)}
				<div class={leadCell(col)}>{col.label}</div>
			{/each}
			{#each columns as col (col.key)}
				<div class={columnCell(col)}>{col.label}</div>
			{/each}
			{#if actions}
				<div class={ACTIONS_PIN}><div class="{ACTIONS_BODY} bg-muted/30"></div></div>
			{/if}
		</div>
	{/if}
	<div class="divide-y divide-border/50">
		{#each Array(rows) as _, i (i)}
			<div class="flex items-center gap-3 px-4 {pad}">
				{#if selectable}
					<Skeleton class="hidden size-4 shrink-0 rounded-[4px] sm:block" />
				{/if}
				{#each lead as col, j (col.key)}
					<div class={leadCell(col)}>
						<div class="flex w-full flex-col gap-1.5 {col.align === 'right' ? 'items-end' : ''}">
							<Skeleton class="h-4 {bar(i, j)}" />
							{#if subline && j === subIndex}
								<Skeleton class="h-3 w-1/3" />
							{/if}
						</div>
					</div>
				{/each}
				{#each columns as col, j (col.key)}
					<div class={columnCell(col)}>
						<Skeleton class="h-4 {bar(i, j + lead.length)}" />
					</div>
				{/each}
				{#if actions}
					<div class={ACTIONS_PIN}>
						<div class={ACTIONS_BODY}><Skeleton class="size-6 rounded-md" /></div>
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>
