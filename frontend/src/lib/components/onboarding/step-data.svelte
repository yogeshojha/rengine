<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { datasetsApi } from '$lib/api/datasets';
	import { instanceSettingsApi } from '$lib/api/instanceSettings';
	import { threatIntelApi } from '$lib/api/threat-intel';
	import { FEED_STATUS_DOT, FEED_STATUS_TONE, FeedStatus } from '$lib/config/threat-intel';
	import { SCAN_RETENTION, SCREENSHOT_RETENTION, retentionLabel } from '$lib/config/retention';
	import type { DatasetRead, QueueHealth } from '$lib/types/dataset';
	import type { InstanceSettingsUpdate } from '$lib/types/instance-settings';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	const POLL_MS = 3000;
	const QUEUED_FOR_MS = 120_000;

	let datasets = $state<DatasetRead[] | null>(null);
	let loadError = $state<string | null>(null);
	let health = $state<QueueHealth | null>(null);
	let checking = $state(false);
	let autoSync = $state<boolean | null>(null);
	let togglingAuto = $state(false);
	let scanRetention = $state('');
	let shotRetention = $state('');
	let storedRetention = $state<{ scan: string; shot: string } | null>(null);
	let busy = $state(false);
	let destroyed = false;
	let timer: ReturnType<typeof setTimeout> | null = null;

	// kind -> the attempt the request was made against
	const queued = new SvelteMap<string, { at: number; attempt: string | null }>();

	const missing = $derived(health?.queues.filter((q) => q.workers === 0) ?? []);
	const services = $derived([...new Set(missing.map((q) => q.service))]);
	const workersOnline = $derived(!!health?.responded && missing.length === 0);
	const nightly = $derived((datasets ?? []).filter((d) => d.auto_sync).map((d) => d.label));

	function joined(items: string[]): string {
		if (items.length < 2) return items[0] ?? '';
		return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
	}

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy });
	});

	function schedule() {
		if (timer) clearTimeout(timer);
		timer = null;
		if (destroyed) return;
		const loading = (datasets ?? []).some((d) => d.status === FeedStatus.SYNCING);
		if (loading || queued.size > 0) timer = setTimeout(loadDatasets, POLL_MS);
	}

	async function loadDatasets() {
		try {
			datasets = await datasetsApi.list();
			loadError = null;
			const now = Date.now();
			for (const [kind, request] of queued) {
				const row = datasets.find((d) => d.kind === kind);
				const started =
					!row || row.status === FeedStatus.SYNCING || row.last_attempt_at !== request.attempt;
				if (started || now - request.at > QUEUED_FOR_MS) queued.delete(kind);
			}
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Datasets not loaded';
		}
		schedule();
	}

	async function checkWorkers() {
		checking = true;
		try {
			health = await datasetsApi.queues();
		} catch {
			health = { responded: false, queues: [] };
		} finally {
			checking = false;
		}
	}

	async function loadRetention() {
		try {
			const settings = await instanceSettingsApi.get();
			scanRetention = String(settings.scan_history_retention_days);
			shotRetention = String(settings.screenshot_retention_days);
			storedRetention = { scan: scanRetention, shot: shotRetention };
		} catch {
			storedRetention = null;
		}
	}

	async function loadAutoSync() {
		try {
			autoSync = (await threatIntelApi.status()).auto_sync;
		} catch {
			autoSync = null;
		}
	}

	onMount(() => {
		void loadDatasets();
		void checkWorkers();
		void loadRetention();
		void loadAutoSync();
	});

	onDestroy(() => {
		destroyed = true;
		if (timer) clearTimeout(timer);
	});

	function action(d: DatasetRead): string | null {
		if (d.status === FeedStatus.EMPTY) return 'Download';
		if (d.status === FeedStatus.FAILED) return 'Retry';
		if (d.status === FeedStatus.STALE) return 'Refresh';
		return null;
	}

	async function download(d: DatasetRead) {
		queued.set(d.kind, { at: Date.now(), attempt: d.last_attempt_at });
		try {
			const result = await datasetsApi.sync(d.kind);
			if (!result.queued) {
				queued.delete(d.kind);
				toast.error(result.detail ?? `${d.label} download not started`);
			}
		} catch (e) {
			queued.delete(d.kind);
			toast.error(e instanceof Error ? e.message : `${d.label} download not started`);
		}
		schedule();
	}

	async function toggleAuto(on: boolean) {
		togglingAuto = true;
		try {
			autoSync = (await threatIntelApi.setAutoSync(on)).auto_sync;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Nightly sync not saved');
		} finally {
			togglingAuto = false;
		}
	}

	async function handleNext() {
		const patch: InstanceSettingsUpdate = {};
		if (storedRetention && scanRetention !== storedRetention.scan)
			patch.scan_history_retention_days = Number(scanRetention);
		if (storedRetention && shotRetention !== storedRetention.shot)
			patch.screenshot_retention_days = Number(shotRetention);
		if (Object.keys(patch).length === 0) {
			next();
			return;
		}
		busy = true;
		try {
			const saved = await instanceSettingsApi.update(patch);
			storedRetention = {
				scan: String(saved.scan_history_retention_days),
				shot: String(saved.screenshot_retention_days)
			};
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Retention not saved');
		} finally {
			busy = false;
		}
	}
</script>

{#snippet dot(tone: string)}
	<span class="flex h-5 shrink-0 items-center">
		<span class="size-2 rounded-full {tone}"></span>
	</span>
{/snippet}

<div class="space-y-6">
	<section class="space-y-2">
		<h3 class="text-sm font-semibold">Workers</h3>
		<div
			class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 rounded-lg border px-4 py-3 sm:grid-cols-[auto_minmax(0,1fr)_auto]"
		>
			{@render dot(
				!health ? 'bg-muted-foreground' : workersOnline ? 'bg-success' : 'bg-destructive'
			)}
			<div class="flex min-w-0 flex-col gap-0.5">
				<span class="text-sm leading-5 font-medium">Scan and job queues</span>
				{#if health && !health.responded}
					<span class="text-xs text-muted-foreground">
						Workers did not respond. Check that the worker services are running.
					</span>
				{:else if missing.length}
					<span class="text-xs text-muted-foreground">
						Queues without a worker: {missing.map((q) => q.name).join(', ')}. Start {joined(
							services
						)}.
					</span>
				{:else if health}
					<span class="text-xs text-muted-foreground">
						{health.queues.length} of {health.queues.length} queues have a worker
					</span>
				{/if}
			</div>
			<div class="col-start-2 flex items-center gap-3 sm:col-start-3">
				{#if !health}
					<span class="text-xs text-muted-foreground">Checking</span>
				{:else if workersOnline}
					<span class="text-xs text-success">Online</span>
				{:else}
					<span class="text-xs text-destructive">
						{health.responded ? 'Not running' : 'No response'}
					</span>
					<LoadingButton
						variant="outline"
						size="sm"
						class="h-7 text-xs"
						loading={checking}
						loadingLabel="Checking"
						onclick={() => checkWorkers()}
					>
						<RefreshCwIcon class="size-3.5" />
						Check again
					</LoadingButton>
				{/if}
			</div>
		</div>
	</section>

	<section class="space-y-2">
		<h3 class="text-sm font-semibold">Datasets</h3>
		<div class="rounded-lg border">
			{#if datasets === null && !loadError}
				{#each [0, 1, 2, 3] as i (i)}
					<div class="border-b px-4 py-3 last:border-b-0">
						<Skeleton class="h-4 w-40" />
						<Skeleton class="mt-1.5 h-3 w-64 max-w-full" />
					</div>
				{/each}
			{:else if loadError && datasets === null}
				<div class="flex items-center justify-between gap-3 px-4 py-3">
					<span class="text-xs text-destructive">{loadError}</span>
					<Button variant="outline" size="sm" class="h-7 text-xs" onclick={() => loadDatasets()}>
						Retry
					</Button>
				</div>
			{:else if datasets}
				{#each datasets as d (d.kind)}
					{@const waiting = queued.has(d.kind) && d.status !== FeedStatus.SYNCING}
					{@const live = waiting || d.status === FeedStatus.SYNCING}
					{@const label = action(d)}
					<div
						class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 border-b px-4 py-3 sm:grid-cols-[auto_minmax(0,1fr)_auto]"
					>
						{@render dot(FEED_STATUS_DOT[waiting ? FeedStatus.SYNCING : d.status])}
						<div class="flex min-w-0 flex-col gap-0.5">
							<span class="text-sm leading-5 font-medium">{d.label}</span>
							<span class="text-xs text-muted-foreground">{d.description}</span>
							{#if d.status === FeedStatus.FAILED && d.error}
								<span class="font-mono text-xs break-all text-destructive">{d.error}</span>
							{/if}
						</div>
						<div class="col-start-2 flex flex-wrap items-center gap-3 sm:col-start-3">
							{#if d.rows}
								<span class="text-xs text-muted-foreground tabular-nums">
									{d.rows.toLocaleString()}
									{d.rows_noun}
								</span>
							{/if}
							<span class="text-xs {FEED_STATUS_TONE[waiting ? FeedStatus.SYNCING : d.status]}">
								{waiting ? 'Queued' : d.status_label}
							</span>
							{#if label && !live}
								<Button variant="outline" size="sm" class="h-7 text-xs" onclick={() => download(d)}>
									{label}
								</Button>
							{/if}
						</div>
					</div>
				{/each}
				{#if nightly.length && autoSync !== null}
					<div class="flex items-center justify-between gap-4 px-4 py-3">
						<div class="flex min-w-0 flex-col gap-0.5">
							<Label for="nightly-sync" class="text-sm font-medium">Nightly sync</Label>
							<span class="text-xs text-muted-foreground">
								{joined(nightly)} download every night.
							</span>
						</div>
						<Switch
							id="nightly-sync"
							checked={autoSync}
							disabled={togglingAuto}
							onCheckedChange={toggleAuto}
						/>
					</div>
				{/if}
			{/if}
		</div>
	</section>

	<section class="space-y-2">
		<h3 class="text-sm font-semibold">Retention</h3>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormField label="Scan history">
				{#snippet children({ id })}
					<Select.Root type="single" bind:value={scanRetention} disabled={!storedRetention}>
						<Select.Trigger {id} class="h-9 w-full text-sm">
							{scanRetention ? retentionLabel(SCAN_RETENTION, scanRetention) : ''}
						</Select.Trigger>
						<Select.Content>
							{#each SCAN_RETENTION as o (o.value)}
								<Select.Item value={o.value} label={o.label}>{o.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>
			<FormField label="Screenshots and response bodies">
				{#snippet children({ id })}
					<Select.Root type="single" bind:value={shotRetention} disabled={!storedRetention}>
						<Select.Trigger {id} class="h-9 w-full text-sm">
							{shotRetention ? retentionLabel(SCREENSHOT_RETENTION, shotRetention) : ''}
						</Select.Trigger>
						<Select.Content>
							{#each SCREENSHOT_RETENTION as o (o.value)}
								<Select.Item value={o.value} label={o.label}>{o.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>
		</div>
	</section>
</div>
