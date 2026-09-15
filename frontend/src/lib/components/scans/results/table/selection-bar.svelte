<script lang="ts">
	interface Props {
		noun: string;
		nounPlural: string;
		total?: number;
		totalCapped?: boolean;
		maxAssets?: number;
		queryActive?: boolean;
		busy?: boolean;
		onRescanAll?: () => void;
		onRescanAllOptions?: () => void;
	}

	let {
		noun,
		nounPlural,
		total = 0,
		totalCapped = false,
		maxAssets = 0,
		queryActive = false,
		busy = false,
		onRescanAll,
		onRescanAllOptions
	}: Props = $props();

	let willRun = $derived(maxAssets > 0 ? Math.min(total, maxAssets) : total);
	let overCap = $derived(maxAssets > 0 && (total > maxAssets || totalCapped));
	let allLabel = $derived(
		overCap
			? `Rescan first ${willRun.toLocaleString()} of ${total.toLocaleString()}${
					totalCapped ? '+' : ''
				}`
			: `Rescan all ${willRun.toLocaleString()} ${willRun === 1 ? noun : nounPlural}`
	);
	let offerAll = $derived(Boolean(onRescanAll) && queryActive && total > 0);
</script>

{#if offerAll}
	<div class="border-b bg-primary/[0.06] text-sm dark:bg-primary/10">
		<div class="flex flex-wrap items-center gap-2 px-4 py-2 text-xs text-muted-foreground">
			<button
				type="button"
				class="font-medium text-foreground underline underline-offset-2"
				onclick={onRescanAll}
				disabled={busy}
			>
				{allLabel} matching
			</button>
			{#if onRescanAllOptions}
				<button
					type="button"
					class="text-muted-foreground underline underline-offset-2"
					onclick={onRescanAllOptions}
					disabled={busy}
				>
					Options
				</button>
			{/if}
		</div>
	</div>
{/if}
