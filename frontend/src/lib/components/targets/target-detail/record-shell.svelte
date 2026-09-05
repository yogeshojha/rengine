<script lang="ts">
	import type { Snippet } from 'svelte';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';
	import { TaskStatus } from '$lib/types/task-status';
	import { relativeTime } from '$lib/utilities/dates';

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
		emptyText = 'No data was returned.',
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
				<Hint text="Last refreshed {new Date(queriedAt).toLocaleString()}">
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
				{#if refreshing || pending}
					<Spinner class="size-3.5" />
				{:else}
					<RefreshCw class="size-3.5" />
				{/if}
			</Button>
		</div>
	</div>

	{#if loading}
		<div class="flex flex-col gap-3 border-t py-4">
			{#each Array(6) as _, i (i)}
				<div class="grid grid-cols-[8rem_1fr] gap-4">
					<Skeleton class="h-3.5 w-16" />
					<Skeleton class="h-3.5 w-72" />
				</div>
			{/each}
		</div>
	{:else if failed}
		<div
			class="flex items-start justify-between gap-4 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3"
		>
			<div class="flex items-start gap-2.5">
				<span class="flex h-5 shrink-0 items-center">
					<CircleX class="size-4 text-destructive" />
				</span>
				<div class="flex flex-col gap-0.5">
					<p class="text-sm leading-5">{name} lookup failed</p>
					{#if error}
						<p class="text-xs leading-4 text-muted-foreground wrap-anywhere">{error}</p>
					{/if}
				</div>
			</div>
			<Button variant="outline" size="sm" class="shrink-0 gap-2" onclick={onRefresh}>
				<RefreshCw class="size-3.5" /> Retry
			</Button>
		</div>
	{:else if pending}
		<div class="flex flex-col items-center justify-center gap-2 border-t py-12">
			<Spinner class="size-4 text-muted-foreground" />
			<p class="text-sm text-muted-foreground">Collecting {name.toLowerCase()} data</p>
		</div>
	{:else if empty}
		<p class="border-t py-8 text-center text-sm text-muted-foreground">{emptyText}</p>
	{:else}
		{@render children()}
	{/if}
</div>
