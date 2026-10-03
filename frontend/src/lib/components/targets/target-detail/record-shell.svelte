<script lang="ts">
	import type { Snippet } from 'svelte';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { TaskStatus } from '$lib/types/task-status';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';

	interface Props {
		name: string;
		status: TaskStatus;
		error?: string | null;
		queriedAt?: string | null;
		refreshing?: boolean;
		loading?: boolean;
		empty?: boolean;
		emptyText?: string;
		onRefresh: () => void;
		bar?: Snippet;
		children: Snippet;
	}

	let {
		name,
		status,
		error = null,
		queriedAt = null,
		refreshing = false,
		loading = false,
		empty = false,
		emptyText = 'No data',
		onRefresh,
		bar,
		children
	}: Props = $props();

	let failed = $derived(status === TaskStatus.FAILED);
	let pending = $derived(status === TaskStatus.PENDING || status === TaskStatus.QUERYING);
</script>

<div class="flex flex-col gap-3">
	<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
		{#if bar}
			{@render bar()}
		{/if}
		<div class="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
			{#if queriedAt && !pending}
				<Hint text="Last refreshed {formatDateTime(queriedAt)}">
					{#snippet child(props)}
						<span {...props} class="tabular-nums">queried {relativeTime(queriedAt)}</span>
					{/snippet}
				</Hint>
			{/if}
			<Button
				variant="ghost"
				size="icon"
				class="size-7 text-muted-foreground hover:text-foreground"
				disabled={refreshing || pending}
				aria-label="Refresh {name}"
				onclick={onRefresh}
			>
				<RefreshCw class="size-3.5 {refreshing || pending ? 'animate-spin' : ''}" />
			</Button>
		</div>
	</div>

	{#if loading}
		<div class="flex flex-col gap-3 border-t py-4">
			{#each Array(6) as _, i (i)}
				<div class="grid grid-cols-[6rem_minmax(0,1fr)] gap-4 sm:grid-cols-[8rem_minmax(0,1fr)]">
					<Skeleton class="h-3.5 w-16" />
					<Skeleton class="h-3.5 w-72 max-w-full" />
				</div>
			{/each}
		</div>
	{:else if failed}
		<EmptyState
			compact
			icon={TriangleAlert}
			title="{name} lookup failed"
			description={error ?? undefined}
		>
			<Button variant="outline" size="sm" onclick={onRefresh}>Retry</Button>
		</EmptyState>
	{:else if pending}
		<EmptyState compact title="Collecting {name} data" />
	{:else if empty}
		<EmptyState compact title={emptyText} />
	{:else}
		{@render children()}
	{/if}
</div>
