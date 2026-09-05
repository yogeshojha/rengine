<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		label: string;
		sub?: string;
		mono?: boolean;
		children: Snippet;
	}

	let { label, sub, mono = true, children }: Props = $props();
</script>

<div
	class="grid grid-cols-[6rem_minmax(0,1fr)] border-t last:border-b sm:grid-cols-[8rem_minmax(0,1fr)]"
>
	<div class="flex flex-col gap-0.5 py-2.5 pr-3">
		<span class="text-xs font-medium {mono ? 'font-mono' : ''}">{label}</span>
		{#if sub}
			<span class="text-[11px] text-muted-foreground">{sub}</span>
		{/if}
	</div>
	<div class="flex min-w-0 flex-col divide-y divide-border/60">
		{@render children()}
	</div>
</div>
