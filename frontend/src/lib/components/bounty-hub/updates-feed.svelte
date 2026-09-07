<script lang="ts">
	import ArrowUpRightIcon from '@lucide/svelte/icons/arrow-up-right';
	import BellOffIcon from '@lucide/svelte/icons/bell-off';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import * as Card from '$lib/components/ui/card';
	import { Spinner } from '$lib/components/ui/spinner';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import {
		EVENT_PAGE_SIZE,
		EVENT_TONE,
		EVENT_TONE_BG,
		assetIcon
	} from '$lib/config/bounty-programs';
	import { relativeTime } from '$lib/utilities/dates';
	import type { BountyEvent } from '$lib/types/bounty-program';

	interface Props {
		onOpenProgram: (handle: string, platform: string) => void;
	}

	let { onOpenProgram }: Props = $props();

	let events = $state<BountyEvent[]>([]);
	let total = $state(0);
	let pageIndex = $state(0);
	let loading = $state(true);
	let filter = $state('all');

	const TABS = [
		{ key: 'all', label: 'Everything' },
		{ key: 'scope_added', label: 'Scope added' },
		{ key: 'program_added', label: 'New programs' },
		{ key: 'went_out_of_scope', label: 'Now out of scope' }
	];

	async function load(kind: string, index: number) {
		loading = true;
		try {
			const result = await bountyProgramsApi.events(
				index + 1,
				EVENT_PAGE_SIZE,
				kind === 'all' ? null : kind,
				null,
				null
			);
			events = result.items;
			total = result.total;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Could not load updates');
			events = [];
			total = 0;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void load(filter, pageIndex);
	});

	// reading the feed is what clears the badge
	$effect(() => {
		if (loading || events.length === 0) return;
		void bountyProgramsApi.markEventsSeen().catch(() => {});
	});

	function onFilter(key: string) {
		filter = key;
		pageIndex = 0;
	}
</script>

<div class="flex flex-col gap-4">
	<CountTabs tabs={TABS} value={filter} onChange={onFilter} />

	<Card.Root class="gap-0 overflow-hidden py-0">
		{#if loading}
			<div class="flex items-center justify-center gap-2 p-12 text-sm text-muted-foreground">
				<Spinner class="size-4" />
				Loading updates
			</div>
		{:else if events.length === 0}
			<EmptyState
				icon={BellOffIcon}
				title="Nothing has changed yet"
				description="reNgine records a change the next time it syncs. The first sync of a program is a baseline, not a change."
				class="p-12"
			/>
		{:else}
			{#each events as event (event.id)}
				{@const Icon = assetIcon(event.icon)}
				<div class="flex items-start gap-3 border-b px-4 py-3 last:border-b-0">
					<span
						class="flex size-7 shrink-0 items-center justify-center rounded-md {EVENT_TONE_BG[
							event.tone
						] ?? 'bg-muted'}"
					>
						<Icon class="size-3.5 {EVENT_TONE[event.tone] ?? 'text-muted-foreground'}" />
					</span>

					<div class="flex min-w-0 flex-1 flex-col gap-0.5">
						<div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
							<span class="text-sm font-medium">{event.label}</span>
							<button
								type="button"
								onclick={() => onOpenProgram(event.handle, event.platform)}
								class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground hover:underline"
							>
								{event.program_name}
								<ArrowUpRightIcon class="size-3" />
							</button>
							{#if event.actionable && event.tone !== 'muted'}
								<Badge variant={event.tone === 'warning' ? 'warning' : 'info'}>
									{event.tone === 'warning' ? 'Act now' : 'Worth a look'}
								</Badge>
							{/if}
						</div>

						{#if event.asset_identifier}
							<span class="font-mono text-xs break-all text-muted-foreground">
								{event.asset_identifier}
							</span>
						{/if}
						{#if event.detail}
							<span class="text-xs text-muted-foreground">{event.detail}</span>
						{/if}
					</div>

					<span class="shrink-0 text-xs whitespace-nowrap text-muted-foreground">
						{relativeTime(event.created_at)}
					</span>
				</div>
			{/each}
		{/if}
	</Card.Root>

	{#if total > EVENT_PAGE_SIZE}
		<ResultsPagination
			page={pageIndex}
			pageSize={EVENT_PAGE_SIZE}
			{total}
			noun="update"
			onPage={(p) => (pageIndex = p)}
		/>
	{/if}
</div>
