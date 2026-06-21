<script lang="ts">
	import { BadgeCheck, BadgeX, BadgeMinus } from 'lucide-svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
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

	function isDuplicate(result: TargetImportResult): boolean {
		return !result.success && !!result.error && result.error.toLowerCase().includes('duplicate');
	}

	let successResults = $derived(results.filter((r) => r.success));
	let failedResults = $derived(results.filter((r) => !r.success && !isDuplicate(r)));
	let duplicateResults = $derived(results.filter((r) => isDuplicate(r)));

	let availableTabs = $derived.by(() => {
		const tabs: { value: string; label: string; count: number; color: string }[] = [];
		if (successResults.length > 0)
			tabs.push({
				value: 'imported',
				label: 'Imported',
				count: successResults.length,
				color: 'bg-foreground'
			});
		if (failedResults.length > 0)
			tabs.push({
				value: 'failed',
				label: 'Failed',
				count: failedResults.length,
				color: 'bg-destructive'
			});
		if (duplicateResults.length > 0)
			tabs.push({
				value: 'duplicates',
				label: 'Duplicates',
				count: duplicateResults.length,
				color: 'bg-amber-500'
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
			case 'Target already exists in project':
				return 'Already exists';
			case 'Duplicate within import batch':
				return 'Duplicate in batch';
			case 'Invalid target format':
				return 'Invalid format';
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
			<div class="text-2xl font-semibold tabular-nums text-amber-600 dark:text-amber-500">
				{skipped_duplicates}
			</div>
			<div class="text-xs text-muted-foreground">Duplicates</div>
		</div>
		<div class="rounded-lg border bg-card p-3 space-y-1">
			<div class="text-2xl font-semibold tabular-nums text-destructive">
				{failed}
			</div>
			<div class="text-xs text-muted-foreground">Failed</div>
		</div>
	</div>

	{#if availableTabs.length > 0}
		<div class="space-y-3">
			<Tabs.Root
				value={activeTab}
				onValueChange={(v) => {
					userSelectedTab = v;
				}}
				class="w-full"
			>
				<Tabs.List class="h-8 w-auto inline-flex">
					{#each availableTabs as tab (tab.value)}
						<Tabs.Trigger value={tab.value} class="text-xs h-7 px-3">
							<div class="flex items-center gap-1.5">
								<div class="h-1.5 w-1.5 rounded-full {tab.color}"></div>
								{tab.label} ({tab.count})
							</div>
						</Tabs.Trigger>
					{/each}
				</Tabs.List>
			</Tabs.Root>

			<ScrollArea class="h-[200px] rounded-md border">
				<div class="divide-y">
					{#each activeItems as result (result.target_value)}
						<div
							class="px-4 py-2.5 flex items-center justify-between gap-3 hover:bg-accent/50 transition-colors"
						>
							<div class="flex items-center gap-2 min-w-0 flex-1">
								{#if activeTab === 'imported'}
									<BadgeCheck class="h-3.5 w-3.5 text-foreground flex-shrink-0" />
								{:else if activeTab === 'failed'}
									<BadgeX class="h-3.5 w-3.5 text-destructive flex-shrink-0" />
								{:else}
									<BadgeMinus class="h-3.5 w-3.5 text-amber-600 dark:text-amber-500 flex-shrink-0" />
								{/if}
								<code class="text-xs font-mono truncate">{result.target_value}</code>
							</div>

							{#if result.error && activeTab !== 'imported'}
								<span
									class="text-xs flex-shrink-0 max-w-[200px] truncate {activeTab === 'failed'
										? 'text-destructive'
										: 'text-muted-foreground'}"
								>
									{friendlyError(result.error)}
								</span>
							{/if}
						</div>
					{/each}
				</div>
			</ScrollArea>
		</div>
	{/if}
</div>
