<script lang="ts">
	import type { IconComponent } from '$lib/config/icons';

	interface Props {
		title: string;
		count?: string | number | null;
		icon?: IconComponent | null;
	}

	let { title, count = null, icon: Icon = null }: Props = $props();
</script>

<h3
	class="flex gap-2 text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase {Icon
		? 'items-center'
		: 'items-baseline'}"
>
	{#if Icon}
		<span class="flex min-w-0 items-center gap-1.5">
			<Icon class="size-3.5 shrink-0" aria-hidden="true" />
			{title}
		</span>
	{:else}
		{title}
	{/if}
	{#if count != null && count !== ''}
		<span class="text-xs font-medium tracking-normal normal-case tabular-nums">{count}</span>
	{/if}
</h3>
