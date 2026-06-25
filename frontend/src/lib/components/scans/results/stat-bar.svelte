<script lang="ts">
	interface Props {
		label: string;
		count: number;
		total: number;
		colorClass?: string;
		sub?: string;
	}

	let { label, count, total, colorClass = 'bg-foreground/70', sub }: Props = $props();

	let pct = $derived(total > 0 ? Math.round((count / total) * 100) : 0);
</script>

<div class="space-y-1">
	<div class="flex items-baseline justify-between gap-2 text-xs">
		<span class="truncate font-mono" title={label}>{label}</span>
		<span class="shrink-0 tabular-nums text-muted-foreground">
			{count}{#if sub}&nbsp;·&nbsp;{sub}{/if}
		</span>
	</div>
	<div class="h-1.5 w-full overflow-hidden rounded-full bg-muted">
		<div class="h-full rounded-full {colorClass}" style="width: {pct}%"></div>
	</div>
</div>
