<script lang="ts">
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';

	interface Props {
		count: number;
		noun: string;
		nounPlural: string;
		total?: number;
		totalCapped?: boolean;
		maxAssets?: number;
		queryActive?: boolean;
		busy?: boolean;
		disabled?: boolean;
		reason?: string;
		onRescan?: () => void;
		onOptions?: () => void;
		onRescanAll?: () => void;
		onRescanAllOptions?: () => void;
		onClear?: () => void;
	}

	let {
		count,
		noun,
		nounPlural,
		total = 0,
		totalCapped = false,
		maxAssets = 0,
		queryActive = false,
		busy = false,
		disabled = false,
		reason = '',
		onRescan,
		onOptions,
		onRescanAll,
		onRescanAllOptions,
		onClear
	}: Props = $props();

	let label = $derived(`${count.toLocaleString()} ${count === 1 ? noun : nounPlural}`);
	let willRun = $derived(maxAssets > 0 ? Math.min(total, maxAssets) : total);
	let overCap = $derived(maxAssets > 0 && (total > maxAssets || totalCapped));
	let allLabel = $derived(
		overCap
			? `Rescan first ${willRun.toLocaleString()} of ${total.toLocaleString()}${
					totalCapped ? '+' : ''
				}`
			: `Rescan all ${willRun.toLocaleString()} ${willRun === 1 ? noun : nounPlural}`
	);
	let offerAll = $derived(
		Boolean(onRescanAll) && total > count && (count > 0 || (queryActive && total > 0))
	);
</script>

{#if count > 0 || offerAll}
	<div class="border-b bg-primary/[0.06] text-[13px] dark:bg-primary/10">
		{#if count > 0}
			<div class="flex flex-wrap items-center gap-2 px-4 py-2">
				<span class="font-semibold tabular-nums">{count.toLocaleString()} selected</span>
				{#if reason}
					<span class="text-xs text-muted-foreground">{reason}</span>
				{/if}
				<span class="flex-1"></span>
				{#if onOptions}
					<Button variant="ghost" size="sm" class="h-7 gap-1.5 px-2" onclick={onOptions}>
						<Settings2 class="size-3.5" />
						Options
					</Button>
				{/if}
				{#if onRescan}
					<LoadingButton
						size="sm"
						class="h-7 gap-1.5 px-2.5"
						loading={busy}
						{disabled}
						loadingLabel="Starting…"
						onclick={onRescan}
					>
						<RefreshCw class="size-3.5" />
						Rescan {label}
					</LoadingButton>
				{/if}
				{#if onClear}
					<Button
						variant="ghost"
						size="sm"
						class="h-7 px-2 text-muted-foreground"
						onclick={onClear}
					>
						Clear
					</Button>
				{/if}
			</div>
		{/if}
		{#if offerAll}
			<div
				class="flex flex-wrap items-center gap-2 px-4 py-2 text-xs text-muted-foreground {count > 0
					? 'border-t border-primary/10'
					: ''}"
			>
				<button
					type="button"
					class="font-medium text-foreground underline underline-offset-2"
					onclick={onRescanAll}
					disabled={busy}
				>
					{allLabel}{queryActive ? ' matching' : ''}
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
		{/if}
	</div>
{/if}
