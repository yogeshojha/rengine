<script lang="ts">
	import PauseIcon from '@lucide/svelte/icons/pause';
	import PlayIcon from '@lucide/svelte/icons/play';
	import SettingsIcon from '@lucide/svelte/icons/settings-2';
	import CircleStopIcon from '@lucide/svelte/icons/circle-stop';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Switch } from '$lib/components/ui/switch';
	import { Toggle } from '$lib/components/ui/toggle';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import WatchDialog from './watch-dialog.svelte';
	import WatchHostRow from './watch-host-row.svelte';
	import { watchesApi } from '$lib/api/watches';
	import {
		EVENT_ICONS,
		EVENT_TONE_CLASS,
		HOST_FILTERS,
		WATCH_EVENT_PAGE_SIZE,
		WATCH_HOST_PAGE_SIZE
	} from '$lib/config/watch';
	import { CADENCE_LABELS } from '$lib/config/watch';
	import { PLATFORM_LABELS, SUBMISSION_STATE_LABELS } from '$lib/config/bounty-programs';
	import { SubmissionState } from '$lib/types/bounty-program';
	import { watchesStore } from '$lib/stores/watches.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		WatchStatus,
		type Watch,
		type WatchEvent,
		type WatchHost,
		type WatchHostCounts,
		type WatchHostFilter
	} from '$lib/types/watch';

	interface Props {
		watch: Watch | null;
		projectId: string;
		open: boolean;
		initialFilter?: WatchHostFilter;
		initialTab?: 'hosts' | 'activity';
		onOpenChange: (open: boolean) => void;
		onChanged: (watch: Watch | null) => void;
	}

	let {
		watch,
		projectId,
		open,
		initialFilter = 'all',
		initialTab = 'hosts',
		onOpenChange,
		onChanged
	}: Props = $props();

	let tab = $state<'hosts' | 'activity'>('hosts');
	let filter = $state<WatchHostFilter>('all');
	let sinceSeen = $state(false);
	let search = $state('');
	let hosts = $state<WatchHost[]>([]);
	let hostTotal = $state(0);
	let hostPage = $state(0);
	let counts = $state<WatchHostCounts | null>(null);
	let events = $state<WatchEvent[]>([]);
	let eventTotal = $state(0);
	let eventPage = $state(0);
	let eventFilter = $state<'all' | 'scope'>('all');
	let loading = $state(false);
	let busy = $state(false);
	let settingsOpen = $state(false);
	let stopOpen = $state(false);
	let seenAt = $state<string | null>(null);

	const platformLabel = $derived(watch ? (PLATFORM_LABELS[watch.platform] ?? watch.platform) : '');
	const paused = $derived(watch?.status === WatchStatus.Paused);
	const since = $derived(sinceSeen ? seenAt : null);

	async function loadHosts() {
		if (!watch) return;
		loading = true;
		try {
			const [page, c] = await Promise.all([
				watchesApi.hosts(watch.id, projectId, {
					state: filter,
					since,
					q: search.trim() || null,
					page: hostPage + 1,
					size: WATCH_HOST_PAGE_SIZE
				}),
				watchesApi.hostCounts(watch.id, projectId, since)
			]);
			hosts = page.items;
			hostTotal = page.total;
			counts = c;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Hosts not loaded');
		} finally {
			loading = false;
		}
	}

	async function loadEvents() {
		if (!watch) return;
		try {
			const page = await watchesApi.events(watch.id, projectId, {
				page: eventPage + 1,
				size: WATCH_EVENT_PAGE_SIZE,
				kind: eventFilter === 'scope' ? 'scope' : null,
				since: eventFilter === 'scope' && sinceSeen ? seenAt : null
			});
			events = page.items;
			eventTotal = page.total;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Activity not loaded');
		}
	}

	$effect(() => {
		const id = watch?.id;
		if (!open || !id) return;
		untrack(() => {
			const w = watch as Watch;
			tab = initialTab;
			filter = initialFilter;
			search = '';
			hostPage = 0;
			eventPage = 0;
			seenAt = w.seen_at;
			eventFilter = initialTab === 'activity' ? 'scope' : 'all';
			sinceSeen =
				w.seen_at !== null &&
				((initialFilter === 'arrived' && w.new_hosts > 0) ||
					(initialFilter === 'alerted' && w.new_alerts > 0) ||
					(initialTab === 'activity' && w.scope_changes > 0));
			void loadHosts();
			void loadEvents();
			void watchesApi
				.markSeen(id, projectId)
				.then(() => watchesStore.refresh())
				.catch(() => undefined);
		});
	});

	$effect(() => {
		void filter;
		void sinceSeen;
		void hostPage;
		if (!open) return;
		untrack(() => void loadHosts());
	});

	let searchTimer: ReturnType<typeof setTimeout> | null = null;
	function onSearch(value: string) {
		search = value;
		if (searchTimer) clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			hostPage = 0;
			void loadHosts();
		}, 250);
	}

	async function setStatus(status: WatchStatus) {
		if (!watch) return;
		busy = true;
		try {
			const updated = await watchesApi.update(watch.id, projectId, { status });
			watchesStore.upsert(updated);
			onChanged(updated);
			toast.success(status === WatchStatus.Paused ? 'Watch paused' : 'Watch resumed');
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Watch not updated');
		} finally {
			busy = false;
		}
	}

	async function stop() {
		if (!watch) return;
		busy = true;
		try {
			await watchesApi.remove(watch.id, projectId);
			watchesStore.remove(watch.id);
			toast.success('Watch stopped');
			stopOpen = false;
			onChanged(null);
			onOpenChange(false);
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Watch not stopped');
		} finally {
			busy = false;
		}
	}

	async function mute(host: WatchHost) {
		if (!watch) return;
		try {
			const updated = await watchesApi.muteHost(watch.id, host.id, projectId);
			hosts = hosts.map((h) => (h.id === updated.id ? updated : h));
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Host not updated');
		}
	}

	function onSaved(updated: Watch) {
		watchesStore.upsert(updated);
		onChanged(updated);
	}

	const filterCounts = $derived<Record<string, number>>({
		all: counts?.all ?? 0,
		arrived: counts?.arrived ?? 0,
		alerted: counts?.alerted ?? 0,
		unresolved: counts?.unresolved ?? 0,
		out_of_scope: counts?.out_of_scope ?? 0
	});
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
		{#if watch}
			<Sheet.Header class="gap-2 border-b p-4">
				<Sheet.Title class="flex flex-wrap items-center gap-2">
					<span class="min-w-0 truncate">{watch.program_name}</span>
					{#if paused}
						<Badge variant="secondary">Paused</Badge>
					{:else}
						<Badge variant="success">Watching</Badge>
					{/if}
					{#if watch.submission_state !== SubmissionState.Open && watch.submission_state !== SubmissionState.Unknown}
						<Badge variant="warning">
							Submissions {SUBMISSION_STATE_LABELS[
								watch.submission_state as SubmissionState
							]?.toLowerCase() ?? watch.submission_state}
						</Badge>
					{/if}
					{#if watch.baseline.status}
						<Badge variant="outline" class="text-muted-foreground">
							{watch.baseline.engine_name} · {CADENCE_LABELS[watch.cadence]}
						</Badge>
					{/if}
				</Sheet.Title>
				<Sheet.Description class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
					<span class="font-mono">@{watch.handle}</span>
					<span>{platformLabel}</span>
					<span class="tabular-nums"
						>{watch.targets} {watch.targets === 1 ? 'target' : 'targets'}</span
					>
					<span class="font-mono">
						{watch.watch_items
							.slice(0, 6)
							.map((i) => (i.startsWith('.') ? `*${i}` : i))
							.join(' · ')}{watch.items_total > 6 ? ` · ${watch.items_total - 6} more` : ''}
					</span>
					{#if watch.last_certificate_at}
						<span>Last certificate {relativeTime(watch.last_certificate_at)}</span>
					{/if}
					{#if watch.rate_limit}
						<span class="tabular-nums">{watch.rate_limit} req/s</span>
					{/if}
				</Sheet.Description>
				{#if watch.last_error}
					<p class="text-xs text-destructive">{watch.last_error}</p>
				{/if}
				<div class="flex flex-wrap items-center gap-2 pt-1">
					{#if paused}
						<LoadingButton
							loading={busy}
							size="sm"
							variant="outline"
							onclick={() => setStatus(WatchStatus.Active)}
						>
							<PlayIcon class="mr-1.5 size-3.5" />
							Resume
						</LoadingButton>
					{:else}
						<LoadingButton
							loading={busy}
							size="sm"
							variant="outline"
							onclick={() => setStatus(WatchStatus.Paused)}
						>
							<PauseIcon class="mr-1.5 size-3.5" />
							Pause
						</LoadingButton>
					{/if}
					<Button size="sm" variant="outline" onclick={() => (settingsOpen = true)}>
						<SettingsIcon class="mr-1.5 size-3.5" />
						Settings
					</Button>
					<Button
						size="sm"
						variant="ghost"
						class="text-muted-foreground"
						onclick={() => (stopOpen = true)}
					>
						<CircleStopIcon class="mr-1.5 size-3.5" />
						Stop watching
					</Button>
				</div>
			</Sheet.Header>

			<div class="border-b px-4">
				<CountTabs
					tabs={[
						{ key: 'hosts', label: 'Hosts' },
						{ key: 'activity', label: 'Activity' }
					]}
					counts={{ hosts: counts?.all ?? watch.hosts_seen, activity: eventTotal }}
					value={tab}
					onChange={(k) => (tab = k as 'hosts' | 'activity')}
				/>
			</div>

			{#if tab === 'hosts'}
				<div class="flex flex-wrap items-center gap-2 border-b px-4 py-2">
					{#each HOST_FILTERS as f (f.key)}
						<Toggle
							size="sm"
							variant="outline"
							pressed={filter === f.key}
							onPressedChange={() => {
								filter = f.key;
								hostPage = 0;
							}}
							class="h-7 gap-1.5 px-2.5 text-xs"
						>
							{f.label}
							<span class="text-2xs tabular-nums text-muted-foreground">{filterCounts[f.key]}</span>
						</Toggle>
					{/each}
					<div class="ml-auto flex items-center gap-3">
						{#if seenAt}
							<label class="flex items-center gap-2 text-xs text-muted-foreground">
								<Switch checked={sinceSeen} onCheckedChange={(v) => (sinceSeen = v)} />
								Since last visit
							</label>
						{/if}
						<Input
							value={search}
							oninput={(e) => onSearch((e.currentTarget as HTMLInputElement).value)}
							placeholder="Filter hosts"
							class="h-7 w-40 text-xs"
						/>
					</div>
				</div>
				<ScrollArea.Root class="min-h-0 flex-1">
					{#if loading && hosts.length === 0}
						<div class="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
							<Spinner class="size-4" />
							Loading hosts
						</div>
					{:else if hosts.length === 0}
						<EmptyState
							title={counts?.all === 0 ? 'No certificates yet' : 'No hosts match'}
							description={counts?.all === 0
								? 'New certificates for the watched apexes are listed here.'
								: undefined}
							class="p-10"
						/>
					{:else}
						{#each hosts as host (host.id)}
							<WatchHostRow {host} onMute={mute} />
						{/each}
					{/if}
				</ScrollArea.Root>
				{#if hostTotal > WATCH_HOST_PAGE_SIZE}
					<div class="border-t px-4 py-2">
						<ResultsPagination
							page={hostPage}
							pageSize={WATCH_HOST_PAGE_SIZE}
							total={hostTotal}
							noun="host"
							onPage={(p) => (hostPage = p)}
						/>
					</div>
				{/if}
			{:else}
				<div class="flex flex-wrap items-center gap-2 border-b px-4 py-2">
					{#each [{ key: 'all', label: 'All' }, { key: 'scope', label: 'Scope changes' }] as f (f.key)}
						<Toggle
							size="sm"
							variant="outline"
							pressed={eventFilter === f.key}
							onPressedChange={() => {
								eventFilter = f.key as 'all' | 'scope';
								eventPage = 0;
								void loadEvents();
							}}
							class="h-7 px-2.5 text-xs"
						>
							{f.label}
						</Toggle>
					{/each}
					{#if seenAt && eventFilter === 'scope'}
						<label class="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
							<Switch
								checked={sinceSeen}
								onCheckedChange={(v) => {
									sinceSeen = v;
									void loadEvents();
								}}
							/>
							Since last visit
						</label>
					{/if}
				</div>
				<ScrollArea.Root class="min-h-0 flex-1">
					{#if events.length === 0}
						<EmptyState
							title={eventFilter === 'scope' ? 'No scope changes' : 'No activity'}
							class="p-10"
						/>
					{:else}
						{#each events as event (event.id)}
							{@const Icon = EVENT_ICONS[event.kind]}
							<div
								class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-3 border-b px-4 py-3 last:border-b-0"
							>
								<span class="flex h-5 items-center">
									<Icon class="size-4 {EVENT_TONE_CLASS[event.kind] ?? 'text-muted-foreground'}" />
								</span>
								<div class="flex min-w-0 flex-col gap-0.5">
									<span class="text-sm">
										{event.label}
										{#if event.name}
											<span class="font-mono text-xs">· {event.name}</span>
										{/if}
									</span>
									{#if event.detail}
										<span class="text-xs whitespace-pre-line text-muted-foreground"
											>{event.detail}</span
										>
									{/if}
								</div>
								<span class="text-2xs text-muted-foreground">{relativeTime(event.created_at)}</span>
							</div>
						{/each}
					{/if}
				</ScrollArea.Root>
				{#if eventTotal > WATCH_EVENT_PAGE_SIZE}
					<div class="border-t px-4 py-2">
						<ResultsPagination
							page={eventPage}
							pageSize={WATCH_EVENT_PAGE_SIZE}
							total={eventTotal}
							noun="event"
							onPage={(p) => {
								eventPage = p;
								void loadEvents();
							}}
						/>
					</div>
				{/if}
			{/if}
		{/if}
	</Sheet.Content>
</Sheet.Root>

{#if watch}
	<WatchDialog
		program={{
			name: watch.program_name,
			handle: watch.handle,
			platform: watch.platform,
			platform_label: platformLabel
		}}
		{projectId}
		open={settingsOpen}
		existing={watch}
		onOpenChange={(v) => (settingsOpen = v)}
		{onSaved}
	/>
	<ConfirmDialog
		bind:open={stopOpen}
		title="Stop watching {watch.program_name}"
		description="The watch, its certificate ledger, its baseline schedule and its scan context are removed."
		confirmLabel="Stop watching"
		destructive
		loading={busy}
		onOpenChange={(v) => (stopOpen = v)}
		onConfirm={stop}
	/>
{/if}
