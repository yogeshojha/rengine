<script lang="ts">
	import { toast } from 'svelte-sonner';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { vulnTemplatesApi } from '$lib/api/vulnerabilities';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import type { DashboardReadiness } from '$lib/types/dashboard';

	interface Props {
		readiness: DashboardReadiness | null;
	}

	let { readiness }: Props = $props();

	let syncing = $state(false);
	let downloading = $state(false);

	let stages = $derived(engineCatalogStore.stages);
	let checksReady = $derived(!!readiness?.checks_ready);
	let workerReady = $derived(!!readiness?.worker_online);
	let allReady = $derived(!!readiness && workerReady && checksReady);

	let concurrency = $derived(
		readiness?.worker_concurrency ? `${readiness.worker_concurrency} concurrent stages` : ''
	);

	async function sync() {
		syncing = true;
		try {
			const result = await vulnTemplatesApi.sync();
			downloading = result.started;
			if (result.started) toast.success('Library sync started', { description: result.message });
			else toast.error(result.message);
		} catch {
			toast.error('Library sync could not be started');
		} finally {
			syncing = false;
		}
	}
</script>

{#if !readiness}
	<div class="flex items-center gap-3 border-t px-5 py-3">
		<Skeleton class="size-2 rounded-full" />
		<Skeleton class="h-4 w-72" />
	</div>
{:else if allReady}
	<div class="flex flex-wrap items-center gap-x-2 gap-y-1 border-t px-5 py-3 text-sm">
		<span class="flex h-5 shrink-0 items-center">
			<span class="size-2 rounded-full bg-success"></span>
		</span>
		<span class="font-medium">Ready</span>
		<span class="text-muted-foreground">
			Worker online{concurrency ? `, ${concurrency}` : ''}
			{#if stages.length}
				· {stages.length} stages available
			{/if}
			· {readiness.checks_total.toLocaleString()} vulnerability checks indexed
		</span>
	</div>
{:else}
	<div class="grid border-t sm:grid-cols-2">
		{#if !checksReady}
			<div class="flex flex-col gap-1.5 border-t px-5 py-3.5 first:border-t-0 sm:border-t-0">
				<span class="flex items-center gap-2 text-xs text-muted-foreground">
					<span class="flex h-4 shrink-0 items-center">
						<span class="size-2 rounded-full bg-warning"></span>
					</span>
					Vulnerability checks
				</span>
				{#if downloading}
					<span class="text-sm font-medium">Sync in progress</span>
					<span class="text-xs text-muted-foreground">
						Scans started before it completes run without these checks.
					</span>
				{:else}
					<span class="text-sm font-medium text-warning">Not indexed</span>
					<div>
						<LoadingButton
							variant="outline"
							size="sm"
							loading={syncing}
							loadingLabel="Starting"
							onclick={sync}
						>
							<RefreshCw class="size-3.5" />
							Sync library
						</LoadingButton>
					</div>
				{/if}
			</div>
		{/if}
		{#if !workerReady}
			<div
				class="flex flex-col gap-1.5 border-t px-5 py-3.5 first:border-t-0 sm:border-t-0 sm:border-l"
			>
				<span class="flex items-center gap-2 text-xs text-muted-foreground">
					<span class="flex h-4 shrink-0 items-center">
						<span class="size-2 rounded-full bg-destructive"></span>
					</span>
					Worker
				</span>
				<span class="text-sm font-medium text-destructive">Unreachable</span>
				<span class="text-xs text-muted-foreground">
					Scans remain queued until a worker is available.
				</span>
			</div>
		{/if}
		{#if workerReady}
			<div
				class="flex flex-col gap-1.5 border-t px-5 py-3.5 first:border-t-0 sm:border-t-0 sm:border-l"
			>
				<span class="flex items-center gap-2 text-xs text-muted-foreground">
					<span class="flex h-4 shrink-0 items-center">
						<span class="size-2 rounded-full bg-success"></span>
					</span>
					Worker
				</span>
				<span class="text-sm font-medium">Online</span>
				{#if concurrency}
					<span class="text-xs text-muted-foreground">{concurrency}</span>
				{/if}
			</div>
		{/if}
	</div>
{/if}
