<script lang="ts">
	import { TaskStatus } from '$lib/types/task-status';
	import { relativeTime } from '$lib/utilities/dates';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { XCircle } from 'lucide-svelte';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import type { Snippet, Component } from 'svelte';

	interface Props {
		title: string;
		sectionIcon: Component<{ class?: string }>;
		status: TaskStatus;
		error?: string | null;
		queriedAt?: string | null;
		onRefresh?: () => void;
		isRefreshing?: boolean;
		children: Snippet;
	}

	let {
		title,
		sectionIcon,
		status,
		error = null,
		queriedAt = null,
		onRefresh,
		isRefreshing = false,
		children
	}: Props = $props();

	let isOpen = $state(true);

	const statusConfig: Record<string, { label: string; class: string }> = {
		success: {
			label: 'Collected',
			class: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
		},
		failed: { label: 'Failed', class: 'bg-red-500/10 text-red-500 border-red-500/20' },
		pending: { label: 'Pending', class: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
		querying: { label: 'Querying', class: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
		skipped: { label: 'Skipped', class: 'bg-muted text-muted-foreground border-border' },
		not_applicable: { label: 'N/A', class: 'bg-muted text-muted-foreground border-border' }
	};

	let cfg = $derived(statusConfig[status] ?? statusConfig.pending);
	let isLoaded = $derived(status === TaskStatus.SUCCESS);
	let isFailed = $derived(status === TaskStatus.FAILED);
	let isPending = $derived(status === TaskStatus.PENDING || status === TaskStatus.QUERYING);
</script>

<Collapsible.Root bind:open={isOpen}>
	<div class="rounded-lg border border-border bg-card overflow-hidden">
		<Collapsible.Trigger
			class="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-accent/30"
		>
			<div class="flex items-center gap-3">
				<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted/50">
					<svelte:component this={sectionIcon} class="h-4 w-4 text-muted-foreground" />
				</div>
				<div class="flex items-center gap-2.5">
					<span class="text-sm font-semibold tracking-tight">{title}</span>
					<Badge variant="outline" class="text-[10px] h-5 {cfg.class}">
						{cfg.label}
					</Badge>
				</div>
			</div>

			<div class="flex items-center gap-2">
				{#if queriedAt && isLoaded}
					<span class="text-[10px] font-mono tabular-nums text-muted-foreground">
						{relativeTime(queriedAt)}
					</span>
				{/if}

				{#if onRefresh}
					<Button
						variant="ghost"
						size="icon"
						class="h-7 w-7"
						disabled={isRefreshing || isPending}
						onclick={(e) => {
							e.stopPropagation();
							onRefresh?.();
						}}
					>
						{#if isRefreshing || isPending}
							<Spinner class="h-3.5 w-3.5" />
						{:else}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path
									d="M3 3v5h5"
								/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" /><path
									d="M16 16h5v5"
								/></svg
							>
						{/if}
					</Button>
				{/if}
			</div>
		</Collapsible.Trigger>

		<Collapsible.Content>
			{#if isFailed && error}
				<div class="mx-4 mb-4 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2.5">
					<div class="flex items-start gap-2">
						<XCircle class="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
						<p class="text-xs text-red-400 leading-relaxed">{error}</p>
					</div>
				</div>
			{:else if isPending}
				<div class="flex flex-col items-center justify-center py-10 gap-2">
					<Spinner class="h-5 w-5 text-muted-foreground" />
					<p class="text-xs text-muted-foreground">Collecting data…</p>
				</div>
			{:else if isLoaded}
				<div class="px-4 pb-4">
					{@render children()}
				</div>
			{/if}
		</Collapsible.Content>
	</div>
</Collapsible.Root>
