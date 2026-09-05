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

<div class="flex flex-col overflow-hidden rounded-xl border bg-card {className}">
	<div class="flex shrink-0 items-center justify-between gap-3 border-b px-5 py-4">
		<div class="flex items-center gap-2">
			<span class="flex h-6 shrink-0 items-center">
				<TitleIcon class="size-4 text-muted-foreground" />
			</span>
			<h2 class="text-base leading-6 font-semibold">{title}</h2>
		</div>
		<div class="flex items-center gap-2 text-xs text-muted-foreground">
			{#if queriedAt && isLoaded}
				<span class="tabular-nums">{relativeTime(queriedAt)}</span>
			{/if}
			{#if onRefresh}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="size-7 text-muted-foreground hover:text-foreground"
								disabled={isRefreshing || isPending}
								aria-label={isRefreshing ? `Refreshing ${title}` : `Refresh ${title}`}
								onclick={(e) => {
									e.stopPropagation();
									onRefresh?.();
								}}
							>
								{#if isRefreshing || isPending}
									<Spinner class="size-3.5" />
								{:else}
									<RefreshCw class="size-3.5" />
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
			<div class="space-y-3 p-5">
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
			<div class="p-5">
				<div
					class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5"
				>
					<span class="flex h-5 shrink-0 items-center">
						<XCircle class="size-3.5 text-destructive" />
					</span>
					<p class="text-sm leading-5 text-destructive">
						{error || `${title} lookup failed. Refresh to try again.`}
					</p>
				</div>
			</div>
		{:else if isPending}
			<div class="flex flex-col items-center justify-center gap-2 py-12">
				<Spinner class="size-4 text-muted-foreground" />
				<p class="text-sm text-muted-foreground">Collecting…</p>
			</div>
		{:else}
			{@render children()}
		{/if}
	</div>
</div>
