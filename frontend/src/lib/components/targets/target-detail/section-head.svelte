<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title: string;
		count?: string | number | null;
		children?: Snippet;
	}

	let { title, count = null, children }: Props = $props();
</script>

<div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
	<h3
		class="flex items-baseline gap-2 text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase"
	>
		{title}
		{#if count != null && count !== ''}
			<span class="text-xs font-medium tracking-normal normal-case tabular-nums">{count}</span>
		{/if}
	</h3>
	{#if children}
		<div class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
			{@render children()}
		</div>
	{/if}
</div>
