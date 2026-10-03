<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Switch } from '$lib/components/ui/switch';
	import Hint from '$lib/components/hint.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { FEED_STATUS_DOT, FEED_STATUS_TONE } from '$lib/config/threat-intel';
	import { threatIntelApi } from '$lib/api/threat-intel';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { formatBytes } from '$lib/utilities/format';
	import { externalHref } from '$lib/utilities/links';
	import type { ThreatFeedRead, ThreatIntelStatus } from '$lib/types/threat-intel';

	const POLL_MS = 4000;
	const COLUMNS = 'md:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)_7.5rem_minmax(0,0.8fr)_6rem_8.5rem]';

	let status = $state<ThreatIntelStatus | null>(null);
	let loading = $state(true);
	let syncing = $state(false);
	let fetchedProjectId = $state<string | null>(null);
	let togglingAuto = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	let projectId = $derived(projectsStore.activeProject?.id ?? null);
	let feeds = $derived(status?.feeds ?? []);
	let providers = $derived(status?.providers ?? []);
	let lastSynced = $derived(
		feeds
			.map((f) => f.last_synced_at)
			.filter((at): at is string => !!at)
			.sort()
			.at(-1) ?? null
	);
	let autoSync = $derived(status?.auto_sync ?? true);

	function version(feed: ThreatFeedRead): string {
		const v = feed.version?.replace('model_version:', '').split(',')[0] ?? '';
		return /^\d{4}-\d{2}-\d{2}T/.test(v) ? v.slice(0, 10) : v;
	}

	function transfer(feed: ThreatFeedRead): string {
		if (!feed.bytes) return '';
		const size = formatBytes(feed.bytes);
		return feed.duration_ms ? `${size} in ${(feed.duration_ms / 1000).toFixed(1)}s` : size;
	}

	async function load(id: string | null) {
		try {
			status = await threatIntelApi.status(id ?? undefined);
			fetchedProjectId = id;
		} catch {
			status = null;
		} finally {
			loading = false;
		}
	}

	async function toggleAuto(enabled: boolean) {
		togglingAuto = true;
		try {
			status = await threatIntelApi.setAutoSync(enabled, fetchedProjectId ?? undefined);
			toast.success(enabled ? 'Nightly sync enabled' : 'Nightly sync disabled');
		} catch {
			toast.error('Sync setting not saved');
		} finally {
			togglingAuto = false;
		}
	}

	async function sync() {
		syncing = true;
		try {
			const res = await threatIntelApi.sync();
			if (res.queued) {
				toast.success('Feed sync started');
				setTimeout(() => load(fetchedProjectId), 2500);
			} else {
				toast.error(res.detail ?? 'Feed sync not started');
			}
		} catch {
			toast.error('Feed sync not started');
		} finally {
			syncing = false;
		}
	}

	$effect(() => {
		const id = projectId;
		if (id === fetchedProjectId && status) return;
		untrack(() => void load(id));
	});

	$effect(() => {
		if (!status?.syncing) return;
		const handle = setInterval(() => untrack(() => load(fetchedProjectId)), POLL_MS);
		return () => clearInterval(handle);
	});
</script>

{#snippet cell(label: string)}
	<span class="text-2xs text-muted-foreground md:hidden">{label}</span>
{/snippet}

{#snippet source(name: string, url: string, hint: string)}
	<Hint text={hint}>
		{#snippet child(props)}
			<a
				{...props}
				class="inline-flex min-w-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
				href={externalHref(url)}
				target="_blank"
				rel="noopener noreferrer"
			>
				<span class="truncate">{name}</span>
				<ExternalLink class="size-3 shrink-0" />
			</a>
		{/snippet}
	</Hint>
{/snippet}

{#snippet group(label: string)}
	<div
		class="border-b bg-muted/10 px-4 py-2 text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase"
	>
		{label}
	</div>
{/snippet}

{#if loading}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<RowSkeleton rows={6} avatar="size-2 rounded-full" trailing="h-4 w-20 rounded-md" />
	</Card.Root>
{:else if !status}
	<EmptyState
		icon={TriangleAlert}
		title="Threat intel not loaded"
		description="The API did not respond. Check that the api service is running."
	>
		<Button
			variant="outline"
			size="sm"
			onclick={() => {
				loading = true;
				void load(projectId);
			}}
		>
			Retry
		</Button>
	</EmptyState>
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<Card.Header class="border-b px-4 py-5">
			<Card.Title>Sources</Card.Title>
			{#if lastSynced}
				<Card.Description>Synced {relativeTime(lastSynced)}</Card.Description>
			{/if}
			<Card.Action class="flex flex-wrap items-center justify-end gap-4">
				<label class="flex cursor-pointer items-center gap-2 text-sm">
					<Switch
						checked={autoSync}
						disabled={togglingAuto || !isAdmin}
						onCheckedChange={toggleAuto}
						aria-label="Nightly sync"
					/>
					<span class="whitespace-nowrap">Nightly sync</span>
				</label>
				<Hint text={isAdmin ? null : 'Editable by administrators'}>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<LoadingButton
								loading={syncing || !!status?.syncing}
								loadingLabel="Syncing"
								variant="outline"
								size="sm"
								disabled={!isAdmin}
								onclick={sync}
							>
								<RefreshCw class="size-4" />
								Sync feeds
							</LoadingButton>
						</span>
					{/snippet}
				</Hint>
			</Card.Action>
		</Card.Header>

		<div
			class="hidden gap-4 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase md:grid {COLUMNS}"
		>
			<span>Source</span>
			<span>Publisher</span>
			<span class="text-right">Records</span>
			<span>Version</span>
			<span>Updated</span>
			<span>Status</span>
		</div>

		{@render group('Feeds')}
		{#each feeds as feed (feed.kind)}
			<div class="border-b px-4 py-3 hover:bg-muted/40">
				<div class="grid grid-cols-2 items-center gap-x-4 gap-y-3 {COLUMNS}">
					<div class="col-span-2 flex min-w-0 items-start gap-3 md:col-span-1">
						<span class="flex h-5 shrink-0 items-center">
							<span class="size-2 rounded-full {FEED_STATUS_DOT[feed.status]}" aria-hidden="true"
							></span>
						</span>
						<div class="flex min-w-0 flex-col">
							<span class="text-sm leading-5 font-medium">{feed.label}</span>
							<span class="text-xs text-muted-foreground">{feed.tagline}</span>
						</div>
					</div>
					<div class="flex min-w-0 flex-col">
						{@render cell('Publisher')}
						{@render source(feed.source, feed.source_url, feed.license)}
					</div>
					<div class="flex flex-col md:items-end">
						{@render cell('Records')}
						<span class="font-mono text-sm tabular-nums">{feed.rows.toLocaleString()}</span>
						<span class="text-2xs text-muted-foreground">{feed.rows_noun}</span>
					</div>
					<div class="flex min-w-0 flex-col">
						{@render cell('Version')}
						<Hint text={transfer(feed)}>
							{#snippet child(props)}
								<span {...props} class="truncate font-mono text-xs text-muted-foreground">
									{version(feed) || '—'}
								</span>
							{/snippet}
						</Hint>
					</div>
					<div class="flex flex-col">
						{@render cell('Updated')}
						<span class="text-xs text-muted-foreground tabular-nums">
							{feed.last_synced_at ? relativeTime(feed.last_synced_at) : 'Never'}
						</span>
					</div>
					<div class="flex flex-col">
						{@render cell('Status')}
						<span class="text-xs {FEED_STATUS_TONE[feed.status]}">{feed.status_label}</span>
					</div>
				</div>
				{#if feed.error}
					<p class="mt-2 pl-5 font-mono text-xs break-all text-destructive">{feed.error}</p>
				{/if}
			</div>
		{/each}

		{#if providers.length}
			{@render group('Lookup APIs')}
			{#each providers as provider (provider.kind)}
				<div class="border-b px-4 py-3 last:border-b-0 hover:bg-muted/40">
					<div class="grid grid-cols-2 items-center gap-x-4 gap-y-3 {COLUMNS}">
						<div class="col-span-2 flex min-w-0 items-start gap-3 md:col-span-1">
							<span class="flex h-5 shrink-0 items-center">
								<span
									class="size-2 rounded-full {provider.keyed
										? 'bg-success'
										: 'bg-muted-foreground'}"
									aria-hidden="true"
								></span>
							</span>
							<div class="flex min-w-0 flex-col">
								<span class="text-sm leading-5 font-medium">{provider.label}</span>
								<span class="text-xs text-muted-foreground">{provider.tagline}</span>
							</div>
						</div>
						<div class="flex min-w-0 flex-col">
							{@render cell('Publisher')}
							{@render source(provider.source, provider.source_url, '')}
						</div>
						<div class="flex flex-col md:items-end">
							{@render cell('Records')}
							<span class="font-mono text-sm tabular-nums">{provider.rows.toLocaleString()}</span>
							<span class="text-2xs text-muted-foreground">{provider.rows_noun}</span>
						</div>
						<div class="flex flex-col">
							{@render cell('Version')}
							<span class="font-mono text-xs text-muted-foreground">—</span>
						</div>
						<div class="flex flex-col">
							{@render cell('Updated')}
							<span class="text-xs text-muted-foreground tabular-nums">
								{provider.last_fetched_at ? relativeTime(provider.last_fetched_at) : 'Never'}
							</span>
						</div>
						<div class="flex flex-col">
							{@render cell('Status')}
							{#if provider.keyed}
								<span class="text-xs text-success">API key set</span>
							{:else}
								<Hint text={`Limit without a key: ${provider.unkeyed_rate}`}>
									{#snippet child(props)}
										<a
											{...props}
											class="w-fit text-xs text-muted-foreground hover:text-foreground"
											href={ROUTES.settings('api-keys')}
										>
											No API key
										</a>
									{/snippet}
								</Hint>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		{/if}
	</Card.Root>
{/if}
