<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Input } from '$lib/components/ui/input';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import * as Select from '$lib/components/ui/select';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Switch } from '$lib/components/ui/switch';
	import { Textarea } from '$lib/components/ui/textarea';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { watchesApi } from '$lib/api/watches';
	import {
		ALERT_QUERY_EXAMPLES,
		CADENCES,
		CADENCE_LABELS,
		DEFAULT_RATE_LIMIT,
		MAX_RATE_LIMIT
	} from '$lib/config/watch';
	import { notificationProviderMeta as metaFor } from '$lib/config/notification-providers';
	import { ROUTES } from '$lib/config/routes';
	import { SELECT_NONE } from '$lib/constants';
	import { notificationChannelsStore } from '$lib/stores/notificationChannels.svelte';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import type { BountyProgram } from '$lib/types/bounty-program';
	import type { NotifProvider } from '$lib/types/notification-channel';
	import { WatchCadence, type Watch, type WatchPreview } from '$lib/types/watch';

	interface Props {
		program: Pick<BountyProgram, 'name' | 'handle' | 'platform' | 'platform_label'>;
		projectId: string;
		open: boolean;
		existing?: Watch | null;
		onOpenChange: (open: boolean) => void;
		onSaved: (watch: Watch) => void;
	}

	let { program, projectId, open, existing = null, onOpenChange, onSaved }: Props = $props();

	const isEdit = $derived(existing !== null);

	let preview = $state<WatchPreview | null>(null);
	let previewError = $state<string | null>(null);
	let loadingPreview = $state(false);
	let saving = $state(false);

	let engineId = $state<string>(SELECT_NONE);
	let cadence = $state<WatchCadence>(WatchCadence.Weekly);
	let passiveOnly = $state(false);
	let runNow = $state(true);
	let rateLimit = $state(String(DEFAULT_RATE_LIMIT));
	let probeOnResolve = $state(true);
	let followScope = $state(true);
	let alertUnresolved = $state(false);
	let alertQuery = $state('');
	let queryError = $state<string | null>(null);
	let checkingQuery = $state(false);
	let channelIds = $state<string[]>([]);
	let notifyInApp = $state(true);

	const enginesReady = $derived(
		(scanEnginesStore.hasFetched || !!scanEnginesStore.error) && !scanEnginesStore.isLoading
	);
	const engineLabel = $derived(
		engineId === SELECT_NONE
			? 'No baseline'
			: (scanEnginesStore.engines.find((e) => e.id === engineId)?.name ?? 'Select engine')
	);
	const channels = $derived(notificationChannelsStore.channels.filter((c) => c.is_active));
	const rateValue = $derived.by(() => {
		if (String(rateLimit).trim() === '') return null;
		const n = Number(rateLimit);
		return Number.isInteger(n) && n >= 1 && n <= MAX_RATE_LIMIT ? n : null;
	});
	const rateInvalid = $derived(String(rateLimit).trim() !== '' && rateValue === null);
	const baselineNeedsEngine = $derived(cadence !== WatchCadence.Off && engineId === SELECT_NONE);
	const canSave = $derived(
		!saving &&
			!rateInvalid &&
			!baselineNeedsEngine &&
			!queryError &&
			!checkingQuery &&
			(isEdit || (preview !== null && preview.items.length > 0 && !preview.existing))
	);
	const existingTargets = $derived(preview?.targets.filter((t) => t.exists).length ?? 0);

	function reset() {
		const w = existing;
		engineId = w?.engine_id ?? SELECT_NONE;
		cadence = w?.cadence ?? WatchCadence.Weekly;
		passiveOnly = w?.intensity === 'passive';
		runNow = !isEdit;
		rateLimit = w
			? w.rate_limit === null
				? ''
				: String(w.rate_limit)
			: String(DEFAULT_RATE_LIMIT);
		probeOnResolve = w?.probe_on_resolve ?? true;
		followScope = w?.follow_scope ?? true;
		alertUnresolved = w?.alert_unresolved ?? false;
		alertQuery = w?.alert_query ?? '';
		queryError = null;
		channelIds = [...(w?.channel_ids ?? [])];
		notifyInApp = w?.notify_in_app ?? true;
	}

	async function loadPreview() {
		loadingPreview = true;
		previewError = null;
		try {
			preview = await watchesApi.preview(program.platform, program.handle, projectId);
		} catch (error) {
			previewError = error instanceof Error ? error.message : 'Scope not read';
			preview = null;
		} finally {
			loadingPreview = false;
		}
	}

	$effect(() => {
		if (!open || isEdit || engineId !== SELECT_NONE) return;
		const first = scanEnginesStore.engines[0];
		if (enginesReady && first) engineId = first.id;
	});

	$effect(() => {
		if (!open) return;
		untrack(() => {
			reset();
			void loadPreview();
			if (scanEnginesStore.fetchedProjectId !== projectId) {
				void scanEnginesStore.fetchEngines(projectId);
			}
			if (!notificationChannelsStore.hasFetched) {
				void notificationChannelsStore.fetch();
			}
		});
	});

	async function checkQuery() {
		const text = alertQuery.trim();
		if (!text) {
			queryError = null;
			return;
		}
		checkingQuery = true;
		try {
			queryError = (await watchesApi.validateQuery(text)).error;
		} catch {
			queryError = null;
		} finally {
			checkingQuery = false;
		}
	}

	function toggleChannel(id: string, on: boolean) {
		channelIds = on ? [...new Set([...channelIds, id])] : channelIds.filter((c) => c !== id);
	}

	function body() {
		return {
			engine_id: engineId === SELECT_NONE ? null : engineId,
			cadence,
			intensity: passiveOnly
				? 'passive'
				: existing && existing.intensity !== 'passive'
					? existing.intensity
					: null,
			rate_limit: rateValue,
			probe_on_resolve: probeOnResolve,
			probe_engine_id: existing?.probe_engine_id ?? null,
			follow_scope: followScope,
			alert_unresolved: alertUnresolved,
			alert_query: alertQuery.trim(),
			channel_ids: channelIds,
			notify_in_app: notifyInApp
		};
	}

	async function save() {
		if (!canSave) return;
		saving = true;
		try {
			const watch = existing
				? await watchesApi.update(existing.id, projectId, body())
				: await watchesApi.create(program.platform, program.handle, {
						...body(),
						project_id: projectId,
						run_baseline_now: runNow
					});
			toast.success(existing ? 'Watch updated' : `Watching ${program.name}`);
			onSaved(watch);
			onOpenChange(false);
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Watch not saved');
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 p-0 sm:max-w-xl">
		<Dialog.Header class="border-b p-5 pb-4">
			<Dialog.Title>{isEdit ? 'Watch settings' : `Watch ${program.name}`}</Dialog.Title>
			<Dialog.Description>
				Scope from {program.platform_label}, refreshed on every sync.
			</Dialog.Description>
		</Dialog.Header>

		<ScrollArea.Root class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[60vh]">
			<div class="flex flex-col gap-6 p-5">
				{#if !isEdit}
					<section class="flex flex-col gap-2">
						{#if loadingPreview}
							<Skeleton class="h-4 w-2/3" />
							<Skeleton class="h-4 w-1/2" />
							<Skeleton class="h-4 w-3/5" />
						{:else if previewError}
							<p class="text-sm text-destructive">{previewError}</p>
						{:else if preview}
							<dl class="grid grid-cols-[9rem_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
								<dt class="text-muted-foreground">Targets</dt>
								<dd class="tabular-nums">
									{preview.targets.length}
									<span class="text-muted-foreground">
										· {preview.wildcards}
										{preview.wildcards === 1 ? 'wildcard' : 'wildcards'}, {preview.domains}
										{preview.domains === 1 ? 'domain' : 'domains'}
										{#if existingTargets > 0}
											· {existingTargets} already in the project
										{/if}
									</span>
								</dd>
								<dt class="text-muted-foreground">Excluded</dt>
								<dd class="tabular-nums">
									{preview.excluded_hosts + preview.excluded_ips}
									<span class="text-muted-foreground"
										>out-of-scope entries applied to every run</span
									>
									{#if preview.unenforceable.length > 0}
										<span class="block text-xs text-warning">
											{preview.unenforceable.length}
											{preview.unenforceable.length === 1 ? 'entry' : 'entries'} cannot be enforced:
											{preview.unenforceable.slice(0, 3).join(', ')}
										</span>
									{/if}
								</dd>
								<dt class="text-muted-foreground">Certificates</dt>
								<dd class="flex flex-wrap gap-1">
									{#each preview.items as item (item)}
										<Badge variant="outline" class="font-mono text-2xs">
											{item.startsWith('.') ? `*${item}` : item}
										</Badge>
									{/each}
									{#if preview.items_total > preview.items.length}
										<Badge variant="outline" class="text-2xs">
											{preview.items_total - preview.items.length} more
										</Badge>
									{/if}
									{#if preview.items.length === 0}
										<span class="text-muted-foreground">No domain or wildcard in scope.</span>
									{:else}
										<span class="block w-full text-xs text-muted-foreground">
											Followed from now on. Earlier certificates come from the baseline scan.
											{#if preview.wildcards === 0}
												No wildcard in scope: only certificates for the listed names are followed.
											{/if}
										</span>
									{/if}
								</dd>
							</dl>
							{#if preview.existing}
								<p class="text-xs text-warning">This program is already watched in the project.</p>
							{/if}
						{/if}
					</section>
				{/if}

				<section class="flex flex-col gap-3">
					<span class="text-xs font-medium tracking-wide text-muted-foreground uppercase"
						>Baseline</span
					>
					<div class="grid gap-3 sm:grid-cols-2">
						<FormField label="Engine">
							{#snippet children({ id })}
								{#if !enginesReady}
									<Skeleton class="h-9 w-full rounded-md" />
								{:else}
									<Select.Root type="single" bind:value={engineId}>
										<Select.Trigger {id} class="w-full">{engineLabel}</Select.Trigger>
										<Select.Content>
											<Select.Item value={SELECT_NONE} label="No baseline">No baseline</Select.Item>
											{#each scanEnginesStore.engines as engine (engine.id)}
												<Select.Item value={engine.id} label={engine.name}
													>{engine.name}</Select.Item
												>
											{/each}
										</Select.Content>
									</Select.Root>
								{/if}
							{/snippet}
						</FormField>
						<FormField label="Repeat">
							{#snippet children({ id })}
								<Select.Root
									type="single"
									value={cadence}
									onValueChange={(v) => v && (cadence = v as WatchCadence)}
								>
									<Select.Trigger {id} class="w-full">{CADENCE_LABELS[cadence]}</Select.Trigger>
									<Select.Content>
										{#each CADENCES as value (value)}
											<Select.Item {value} label={CADENCE_LABELS[value]}>
												{CADENCE_LABELS[value]}
											</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							{/snippet}
						</FormField>
					</div>
					{#if baselineNeedsEngine}
						<p class="text-xs text-destructive">A repeating baseline needs an engine.</p>
					{/if}
					<label class="flex items-center justify-between gap-4 text-sm">
						<span class="flex flex-col gap-0.5">
							Passive only
							<span class="text-xs text-muted-foreground">
								Every baseline run at passive intensity. New hosts are not probed.
							</span>
						</span>
						<Switch
							checked={passiveOnly}
							onCheckedChange={(v) => {
								passiveOnly = v;
								if (v) probeOnResolve = false;
							}}
						/>
					</label>
					{#if !isEdit}
						<label class="flex items-center justify-between gap-4 text-sm">
							<span class="flex flex-col gap-0.5">
								Run the baseline now
								<span class="text-xs text-muted-foreground"
									>One scan per target with the chosen engine.</span
								>
							</span>
							<Switch
								checked={runNow && engineId !== SELECT_NONE}
								disabled={engineId === SELECT_NONE}
								onCheckedChange={(v) => (runNow = v)}
							/>
						</label>
					{/if}
					<FormField label="Rate ceiling" description="Requests per second per target, all tools.">
						{#snippet children({ id })}
							<div class="flex items-center gap-2">
								<Input
									{id}
									type="number"
									min="1"
									max={MAX_RATE_LIMIT}
									class="w-28"
									value={rateLimit}
									oninput={(e) => (rateLimit = e.currentTarget.value)}
									placeholder="No ceiling"
									aria-invalid={rateInvalid}
								/>
								<span class="text-xs text-muted-foreground">req/s</span>
							</div>
						{/snippet}
					</FormField>
				</section>

				<section class="flex flex-col gap-3">
					<span class="text-xs font-medium tracking-wide text-muted-foreground uppercase">
						New hosts
					</span>
					<label class="flex items-center justify-between gap-4 text-sm">
						<span class="flex flex-col gap-0.5">
							Probe a new host when it resolves
							<span class="text-xs text-muted-foreground">
								One HTTP request and a screenshot. Status, title and technologies are included in
								the alert.
							</span>
						</span>
						<Switch
							checked={probeOnResolve && !passiveOnly}
							disabled={passiveOnly}
							onCheckedChange={(v) => (probeOnResolve = v)}
						/>
					</label>
					<label class="flex items-center justify-between gap-4 text-sm">
						<span class="flex flex-col gap-0.5">
							Follow scope changes
							<span class="text-xs text-muted-foreground">
								An added asset becomes a target. A removed asset leaves the baseline.
							</span>
						</span>
						<Switch checked={followScope} onCheckedChange={(v) => (followScope = v)} />
					</label>
					<label class="flex items-center justify-between gap-4 text-sm">
						<span class="flex flex-col gap-0.5">
							Alert on names that do not resolve
							<span class="text-xs text-muted-foreground">After 48 hours without a DNS answer.</span
							>
						</span>
						<Switch checked={alertUnresolved} onCheckedChange={(v) => (alertUnresolved = v)} />
					</label>
					<FormField
						label="Alert when"
						description="A Web Assets query evaluated against the probe alone. Empty matches every resolving host."
					>
						{#snippet children({ id })}
							<Textarea
								{id}
								bind:value={alertQuery}
								rows={2}
								class="font-mono text-sm"
								placeholder={ALERT_QUERY_EXAMPLES[0]}
								onblur={checkQuery}
								aria-invalid={!!queryError}
							/>
						{/snippet}
					</FormField>
					{#if queryError}
						<p class="text-xs text-destructive">{queryError}</p>
					{:else if checkingQuery}
						<p class="text-xs text-muted-foreground">Checking</p>
					{:else}
						<div class="flex flex-wrap gap-1">
							{#each ALERT_QUERY_EXAMPLES as example (example)}
								<button
									type="button"
									class="rounded-md border px-2 py-0.5 font-mono text-2xs text-muted-foreground hover:text-foreground"
									onclick={() => {
										alertQuery = example;
										void checkQuery();
									}}
								>
									{example}
								</button>
							{/each}
						</div>
					{/if}
				</section>

				<section class="flex flex-col gap-3">
					<span class="text-xs font-medium tracking-wide text-muted-foreground uppercase">
						Alerts to
					</span>
					<label class="flex items-center justify-between gap-4 text-sm">
						<span>In-app inbox</span>
						<Switch checked={notifyInApp} onCheckedChange={(v) => (notifyInApp = v)} />
					</label>
					{#if channels.length === 0}
						<p class="text-xs text-muted-foreground">
							No notification channel is set up.
							<a href={ROUTES.settings('notifications')} class="underline hover:text-foreground">
								Notifications
							</a>
						</p>
					{:else}
						<div class="flex flex-col gap-2">
							{#each channels as channel (channel.id)}
								{@const meta = metaFor(channel.provider as NotifProvider)}
								{@const Icon = meta.icon}
								<label class="flex items-center gap-3 text-sm">
									<Checkbox
										checked={channelIds.includes(channel.id)}
										onCheckedChange={(v) => toggleChannel(channel.id, v === true)}
									/>
									<Icon class="size-4 text-muted-foreground" />
									<span class="min-w-0 truncate">{channel.name}</span>
									<span class="text-xs text-muted-foreground">{meta.name}</span>
								</label>
							{/each}
						</div>
						{#if channelIds.length === 0}
							<p class="text-xs text-muted-foreground">
								With none chosen, channels subscribed to Program watches receive the alert.
							</p>
						{/if}
					{/if}
				</section>
			</div>
		</ScrollArea.Root>

		<Dialog.Footer class="border-t p-4">
			<Button variant="outline" onclick={() => onOpenChange(false)}>Cancel</Button>
			<LoadingButton loading={saving} disabled={!canSave} onclick={() => save()}>
				{isEdit ? 'Save' : 'Watch program'}
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
