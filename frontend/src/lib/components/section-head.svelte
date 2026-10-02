<script lang="ts">
	interface Props {
		title: string;
		count?: string | number | null;
	}

	let { title, count = null }: Props = $props();
</script>

<h3
	class="flex items-baseline gap-2 text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase"
>
	{title}
	{#if count != null && count !== ''}
		<span class="text-xs font-medium tracking-normal normal-case tabular-nums">{count}</span>
	{/if}
</h3>
