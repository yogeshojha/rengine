<script lang="ts">
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';

	interface Props {
		noun: string;
		nounPlural: string;
		total?: number;
		totalCapped?: boolean;
		maxAssets?: number;
		queryActive?: boolean;
		query?: string;
		busy?: boolean;
		onRescanAll?: () => void | Promise<void>;
		onRescanAllOptions?: () => void;
	}

	let {
		noun,
		nounPlural,
		total = 0,
		totalCapped = false,
		maxAssets = 0,
		queryActive = false,
		query = '',
		busy = false,
		onRescanAll,
		onRescanAllOptions
	}: Props = $props();

	let willRun = $derived(maxAssets > 0 ? Math.min(total, maxAssets) : total);
	let overCap = $derived(maxAssets > 0 && (total > maxAssets || totalCapped));
	let matched = $derived(`${total.toLocaleString()}${totalCapped ? '+' : ''}`);
	let allLabel = $derived(
		overCap
			? `Rescan first ${willRun.toLocaleString()} of ${matched}`
			: `Rescan all ${willRun.toLocaleString()} ${willRun === 1 ? noun : nounPlural}`
	);
	let offerAll = $derived(Boolean(onRescanAll) && queryActive && total > 0);

	let confirming = $state(false);
	let confirmTitle = $derived(
		overCap
			? `Rescan first ${willRun.toLocaleString()} of ${matched} ${nounPlural}`
			: `Rescan ${willRun.toLocaleString()} ${willRun === 1 ? noun : nounPlural}`
	);

	async function confirm() {
		await onRescanAll?.();
		confirming = false;
	}
</script>

{#if offerAll}
	<div class="border-b bg-primary/[0.06] text-sm dark:bg-primary/10">
		<div class="flex flex-wrap items-center gap-2 px-4 py-2 text-xs text-muted-foreground">
			<button
				type="button"
				class="font-medium text-foreground underline underline-offset-2 hover:text-primary disabled:opacity-50"
				onclick={() => (confirming = true)}
				disabled={busy}
			>
				{allLabel} matching
			</button>
			{#if onRescanAllOptions}
				<button
					type="button"
					class="text-muted-foreground underline underline-offset-2 hover:text-foreground disabled:opacity-50"
					onclick={onRescanAllOptions}
					disabled={busy}
				>
					Options
				</button>
			{/if}
		</div>
	</div>

	<ConfirmDialog
		bind:open={confirming}
		title={confirmTitle}
		description={query ? `Matching ${query}` : undefined}
		confirmLabel="Rescan"
		loadingLabel="Starting"
		loading={busy}
		onOpenChange={(value) => (confirming = value)}
		onConfirm={confirm}
	/>
{/if}
