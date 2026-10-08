<script lang="ts">
	import type { Snippet } from 'svelte';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { TaskStatus } from '$lib/types/task-status';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';
	import { cn } from '$lib/utils';

	interface Props {
		name: string;
		status: TaskStatus;
		error?: string | null;
		queriedAt?: string | null;
		refreshing?: boolean;
		loading?: boolean;
		/** The record did not load (the page notice carries the Retry). */
		unloaded?: string | null;
		empty?: boolean;
		emptyText?: string;
		/** Content brings its own cards: no outer card, no row padding. */
		plain?: boolean;
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
		unloaded = null,
		empty = false,
		emptyText = 'No data',
		plain = false,
		onRefresh,
		bar,
		children
	}: Props = $props();

	let failed = $derived(status === TaskStatus.FAILED);
	let pending = $derived(status === TaskStatus.PENDING || status === TaskStatus.QUERYING);
	let emptyClass = $derived(plain ? '' : 'border-0 bg-transparent');
</script>

{#snippet toolbar()}
	<div class={cn('flex flex-wrap items-center gap-2', plain ? 'gap-x-4' : 'border-b px-4 py-3')}>
		{#if bar}
			{@render bar()}
		{/if}
		<div class="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
			{#if queriedAt}
				<Hint text="Last refreshed {formatDateTime(queriedAt)}">
					{#snippet child(props)}
						<span {...props} class="tabular-nums">queried {relativeTime(queriedAt)}</span>
					{/snippet}
				</Hint>
			{/if}
			<Hint text="Refresh {name}">
				{#snippet child(props)}
					<Button
						{...props}
						variant="outline"
						size="icon"
						disabled={refreshing}
						aria-label="Refresh {name}"
						onclick={onRefresh}
					>
						<RefreshCw class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
					</Button>
				{/snippet}
			</Hint>
		</div>
	</div>
{/snippet}

{#snippet body()}
	{#if loading}
		<div class={cn('flex flex-col gap-3 py-4', plain ? 'border-t' : 'px-4')} aria-busy="true">
			{#each Array(6) as _, i (i)}
				<div class="grid grid-cols-[6rem_minmax(0,1fr)] gap-4 sm:grid-cols-[8rem_minmax(0,1fr)]">
					<Skeleton class="h-3.5 w-16" />
					<Skeleton class="h-3.5 w-72 max-w-full" />
				</div>
			{/each}
		</div>
	{:else if unloaded}
		<EmptyState
			compact
			icon={TriangleAlert}
			title="{name} not loaded"
			description={unloaded}
			class={emptyClass}
		/>
	{:else if failed}
		<EmptyState
			compact
			icon={TriangleAlert}
			title="{name} lookup failed"
			description={error ?? undefined}
			class={emptyClass}
		>
			<Button variant="outline" size="sm" disabled={refreshing} onclick={onRefresh}>Retry</Button>
		</EmptyState>
	{:else if pending}
		<EmptyState compact icon={Spinner} title="Collecting {name} data" class={emptyClass} />
	{:else if empty}
		<EmptyState compact title={emptyText} class={emptyClass}>
			<Button variant="outline" size="sm" disabled={refreshing} onclick={onRefresh}>
				<RefreshCw class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
				Refresh
			</Button>
		</EmptyState>
	{:else}
		{@render toolbar()}
		{#if plain}
			{@render children()}
		{:else}
			<div class="px-4">{@render children()}</div>
		{/if}
	{/if}
{/snippet}

{#if plain}
	<div class="flex flex-col gap-3">{@render body()}</div>
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">{@render body()}</Card.Root>
{/if}
