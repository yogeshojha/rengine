<script lang="ts">
	import type { Snippet } from 'svelte';
	import { TaskStatus } from '$lib/types/task-status';
	import { relativeTime } from '$lib/utilities/dates';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { XCircle, RefreshCw, FileText, Globe, Router } from 'lucide-svelte';

	interface Props {
		title: string;
		status?: TaskStatus;
		error?: string | null;
		queriedAt?: string | null;
		onRefresh?: () => void;
		isRefreshing?: boolean;
		loading?: boolean;
		class?: string;
		children: Snippet;
	}

	let {
		title,
		status,
		error = null,
		queriedAt = null,
		onRefresh,
		isRefreshing = false,
		loading = false,
		class: className = '',
		children
	}: Props = $props();

	const STATUS_DOT: Record<string, string> = {
		success: 'bg-emerald-500',
		failed: 'bg-red-500',
		pending: 'bg-amber-500 animate-pulse',
		querying: 'bg-blue-500 animate-pulse',
		skipped: 'bg-muted-foreground/30',
		not_applicable: 'bg-muted-foreground/30'
	};

	let dotCls = $derived(status ? (STATUS_DOT[status] ?? STATUS_DOT.pending) : '');
	let isFailed = $derived(status === TaskStatus.FAILED);
	let isPending = $derived(status === TaskStatus.PENDING || status === TaskStatus.QUERYING);
	let isLoaded = $derived(status === TaskStatus.SUCCESS);

	const TITLE_ICON: Record<string, typeof FileText> = {
		WHOIS: FileText,
		DNS: Globe,
		BGP: Router
	};
	let titleIcon = $derived(TITLE_ICON[title] ?? FileText);
</script>

<div class="rounded-lg border border-border bg-card flex flex-col overflow-hidden {className}">
	<!-- widget header — matches overview widget chrome -->
	<div class="flex items-center justify-between px-4 py-2.5 border-b border-border/50 shrink-0">
		<div class="flex items-center gap-2">
			<svelte:component this={titleIcon} class="h-3.5 w-3.5 text-muted-foreground/40" />
			<h3 class="text-xs font-semibold tracking-tight text-foreground/90">{title}</h3>
		</div>
		<div class="flex items-center gap-2">
			{#if queriedAt && isLoaded}
				<span class="text-[9px] font-mono tabular-nums text-muted-foreground/50">
					{relativeTime(queriedAt)}
				</span>
			{/if}
			{#if onRefresh}
				<button
					class="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground/40
						transition-colors hover:text-foreground hover:bg-accent/50
						disabled:opacity-30 disabled:pointer-events-none"
					disabled={isRefreshing || isPending}
					onclick={(e) => {
						e.stopPropagation();
						onRefresh?.();
					}}
				>
					{#if isRefreshing || isPending}
						<Spinner class="h-3 w-3" />
					{:else}
						<RefreshCw class="h-3 w-3" />
					{/if}
				</button>
			{/if}
		</div>
	</div>

	<!-- widget body -->
	<div class="flex-1 min-h-0 overflow-y-auto">
		{#if loading}
			<div class="p-4 space-y-3">
				<div class="flex items-center justify-between">
					<Skeleton class="h-3 w-20" />
					<Skeleton class="h-3 w-28" />
				</div>
				<div class="flex items-center justify-between">
					<Skeleton class="h-3 w-16" />
					<Skeleton class="h-3 w-32" />
				</div>
				<div class="flex items-center justify-between">
					<Skeleton class="h-3 w-24" />
					<Skeleton class="h-3 w-20" />
				</div>
				<div class="flex items-center justify-between">
					<Skeleton class="h-3 w-14" />
					<Skeleton class="h-3 w-36" />
				</div>
				<Skeleton class="h-3 w-full mt-2" />
				<Skeleton class="h-3 w-3/4" />
			</div>
		{:else if isFailed && error}
			<div class="p-4">
				<div
					class="flex items-start gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2.5"
				>
					<XCircle class="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
					<p class="text-[11px] text-red-400 leading-relaxed">{error}</p>
				</div>
			</div>
		{:else if isPending}
			<div class="flex flex-col items-center justify-center py-10 gap-1.5">
				<Spinner class="h-4 w-4 text-muted-foreground" />
				<p class="text-[10px] text-muted-foreground/60">Collecting…</p>
			</div>
		{:else}
			{@render children()}
		{/if}
	</div>
</div>
