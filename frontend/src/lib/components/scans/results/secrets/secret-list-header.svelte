<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import { SECRET_WIDTHS, type SecretSortKey } from './columns';

	interface Props {
		projectWide?: boolean;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: SecretSortKey) => void;
	}

	let { projectWide = false, sortKey, sortDir, onSort }: Props = $props();
</script>

{#snippet arrow(key: SecretSortKey)}
	{#if sortKey === key}
		{#if sortDir === 1}<ArrowUp class="h-3 w-3" />{:else}<ArrowDown class="h-3 w-3" />{/if}
	{/if}
{/snippet}

<div
	class="flex items-center gap-3 border-b border-border bg-muted/30 px-4 py-2 text-xs font-medium tracking-wider text-muted-foreground uppercase"
>
	<div class="min-w-0 flex-1">Secret</div>

	{#if projectWide}
		<div class={SECRET_WIDTHS.target}>Target</div>
	{/if}

	<button
		type="button"
		class="{SECRET_WIDTHS.kind} items-center gap-1 text-left tracking-wider uppercase hover:text-foreground"
		onclick={() => onSort('kind')}
	>
		Kind
		{@render arrow('kind')}
	</button>

	<button
		type="button"
		class="{SECRET_WIDTHS.state} items-center gap-1 tracking-wider uppercase hover:text-foreground"
		onclick={() => onSort('state')}
	>
		State
		{@render arrow('state')}
	</button>

	<button
		type="button"
		class="{SECRET_WIDTHS.asset} items-center gap-1 text-left tracking-wider uppercase hover:text-foreground"
		onclick={() => onSort('hosts')}
	>
		Web asset
		{@render arrow('hosts')}
	</button>

	<button
		type="button"
		class="{SECRET_WIDTHS.seen} items-center gap-1 tracking-wider uppercase hover:text-foreground"
		onclick={() => onSort('seen')}
	>
		Seen
		{@render arrow('seen')}
	</button>

	<div class={SECRET_WIDTHS.actions}></div>
</div>
