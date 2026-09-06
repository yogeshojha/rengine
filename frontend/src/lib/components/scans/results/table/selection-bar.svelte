<script lang="ts">
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';

	interface Props {
		count: number;
		noun: string;
		nounPlural: string;
		busy?: boolean;
		disabled?: boolean;
		reason?: string;
		onRescan: () => void;
		onOptions?: () => void;
		onClear: () => void;
	}

	let {
		count,
		noun,
		nounPlural,
		busy = false,
		disabled = false,
		reason = '',
		onRescan,
		onOptions,
		onClear
	}: Props = $props();

	let label = $derived(`${count} ${count === 1 ? noun : nounPlural}`);
</script>

{#if count > 0}
	<div
		class="flex flex-wrap items-center gap-2 border-b bg-primary/[0.06] px-4 py-2 text-[13px] dark:bg-primary/10"
	>
		<span class="font-semibold tabular-nums">{count} selected</span>
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
		<Button variant="ghost" size="sm" class="h-7 px-2 text-muted-foreground" onclick={onClear}>
			Clear
		</Button>
	</div>
{/if}
