<script lang="ts">
	import BadgeCheck from '@lucide/svelte/icons/badge-check';
	import BadgeX from '@lucide/svelte/icons/badge-x';
	import BadgeMinus from '@lucide/svelte/icons/badge-minus';
	import * as Tabs from '$lib/components/ui/tabs';
	import type { TargetImportResult } from '$lib/types/target';

	interface Props {
		total: number;
		imported: number;
		failed: number;
		skipped_duplicates: number;
		results: TargetImportResult[];
	}

	let { total, imported, failed, skipped_duplicates, results }: Props = $props();

	let successResults = $derived(results.filter((r) => r.success));
	let failedResults = $derived(results.filter((r) => !r.success && !r.duplicate));
	let duplicateResults = $derived(results.filter((r) => !r.success && r.duplicate));

	let availableTabs = $derived.by(() => {
		const tabs: { value: string; label: string; count: number }[] = [];
		if (successResults.length > 0)
			tabs.push({
				value: 'imported',
				label: 'Imported',
				count: successResults.length
			});
		if (failedResults.length > 0)
			tabs.push({
				value: 'failed',
				label: 'Failed',
				count: failedResults.length
			});
		if (duplicateResults.length > 0)
			tabs.push({
				value: 'duplicates',
				label: 'Skipped',
				count: duplicateResults.length
			});
		return tabs;
	});

	let defaultTab = $derived(
		failedResults.length > 0 ? 'failed' : successResults.length > 0 ? 'imported' : 'duplicates'
	);

	let userSelectedTab = $state<string | null>(null);
	let activeTab = $derived(userSelectedTab ?? defaultTab);

	let activeItems = $derived.by(() => {
		if (activeTab === 'failed') return failedResults;
		if (activeTab === 'duplicates') return duplicateResults;
		return successResults;
	});

	function friendlyError(error: string | null): string {
		if (!error) return 'Unknown error';
		switch (error) {
			case 'Target exists in this project':
				return 'Already exists';
			case 'Duplicate within import batch':
				return 'Duplicate in batch';
			case 'Empty target value':
				return 'Empty value';
			default:
				return error;
		}
	}
</script>

<div class="space-y-4">
	<div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
		<div class="rounded-lg border bg-card p-3 space-y-1">
			<div class="text-2xl font-semibold tabular-nums">{total}</div>
			<div class="text-xs text-muted-foreground">Total</div>
		</div>
		<div class="rounded-lg border bg-card p-3 space-y-1">
			<div class="text-2xl font-semibold tabular-nums text-foreground">
				{imported}
			</div>
			<div class="text-xs text-muted-foreground">Imported</div>
		</div>
		<div class="rounded-lg border bg-card p-3 space-y-1">
			<div class="text-2xl font-semibold tabular-nums text-muted-foreground">
				{skipped_duplicates}
			</div>
			<div class="text-xs text-muted-foreground">Skipped</div>
		</div>
		<div class="rounded-lg border bg-card p-3 space-y-1">
			<div class="text-2xl font-semibold tabular-nums text-destructive">
				{failed}
			</div>
			<div class="text-xs text-muted-foreground">Failed</div>
		</div>
	</div>

	{#if availableTabs.length > 0}
		<div class="flex flex-col gap-3">
			<Tabs.Root
				value={activeTab}
				onValueChange={(v) => {
					userSelectedTab = v;
				}}
			>
				<Tabs.List variant="line">
					{#each availableTabs as tab (tab.value)}
						<Tabs.Trigger value={tab.value} class="flex-none px-3">
							{tab.label}
							<span class="text-xs text-muted-foreground tabular-nums">
								{tab.count.toLocaleString()}
							</span>
						</Tabs.Trigger>
					{/each}
				</Tabs.List>
			</Tabs.Root>

			<ul class="divide-y rounded-md border">
				{#each activeItems as result, i (`${result.target_value}:${i}`)}
					<li class="flex items-center justify-between gap-3 px-4 py-2.5">
						<div class="flex min-w-0 flex-1 items-center gap-2">
							{#if activeTab === 'imported'}
								<BadgeCheck class="size-3.5 shrink-0 text-foreground" />
							{:else if activeTab === 'failed'}
								<BadgeX class="size-3.5 shrink-0 text-destructive" />
							{:else}
								<BadgeMinus class="size-3.5 shrink-0 text-muted-foreground" />
							{/if}
							<code class="truncate font-mono text-xs" title={result.target_value}
								>{result.target_value}</code
							>
						</div>

						{#if result.error && activeTab !== 'imported'}
							<span
								class="max-w-[200px] shrink-0 truncate text-xs {activeTab === 'failed'
									? 'text-destructive'
									: 'text-muted-foreground'}"
							>
								{friendlyError(result.error)}
							</span>
						{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>
