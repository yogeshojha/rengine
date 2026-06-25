<script lang="ts">
	import type { Snippet } from 'svelte';
	import { TaskStatus } from '$lib/types/task-status';
	import { relativeTime } from '$lib/utilities/dates';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import XCircle from '@lucide/svelte/icons/circle-x';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import FileText from '@lucide/svelte/icons/file-text';
	import Globe from '@lucide/svelte/icons/globe';
	import Router from '@lucide/svelte/icons/router';

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

	let isFailed = $derived(status === TaskStatus.FAILED);
	let isPending = $derived(status === TaskStatus.PENDING || status === TaskStatus.QUERYING);
	let isLoaded = $derived(status === TaskStatus.SUCCESS);

	const TITLE_ICON: Record<string, typeof FileText> = {
		WHOIS: FileText,
		DNS: Globe,
		BGP: Router
	};
	const TitleIcon = $derived(TITLE_ICON[title] ?? FileText);
</script>

<div class="rounded-lg border border-border bg-card flex flex-col overflow-hidden {className}">
	<div class="flex items-center justify-between px-4 py-2.5 border-b border-border/50 shrink-0">
		<div class="flex items-center gap-2">
			<TitleIcon class="h-3.5 w-3.5 text-muted-foreground/40" />
			<h3 class="text-xs font-semibold tracking-tight text-foreground">{title}</h3>
		</div>
		<div class="flex items-center gap-2">
			{#if queriedAt && isLoaded}
				<span class="text-[9px] font-mono tabular-nums text-muted-foreground/50">
					{relativeTime(queriedAt)}
				</span>
			{/if}
			{#if onRefresh}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="h-6 w-6 text-muted-foreground/40 hover:text-foreground"
								disabled={isRefreshing || isPending}
								aria-label={isRefreshing ? `Refreshing ${title}` : `Refresh ${title}`}
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
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Refresh {title}</Tooltip.Content>
				</Tooltip.Root>
			{/if}
		</div>
	</div>

	<div class="min-h-0">
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
		{:else if isFailed}
			<div class="p-4">
				<div
					class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5"
				>
					<XCircle class="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
					<p class="text-[11px] text-destructive/90 leading-relaxed">
						{error || `${title} enrichment failed — try refreshing.`}
					</p>
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
