<script lang="ts">
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { toast } from 'svelte-sonner';
	import EmptyState from '$lib/components/empty-state.svelte';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import { auth } from '$lib/stores/auth.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { SYNC_INTERVAL_LABELS } from '$lib/config/bounty-programs';
	import { relativeTime, untilTime } from '$lib/utilities/dates';
	import { externalHref } from '$lib/utilities/links';
	import {
		SyncInterval,
		type BountyEventSpec,
		type BountySettings,
		type BountySettingsUpdate,
		type BountyVocabulary
	} from '$lib/types/bounty-program';

	interface Props {
		open: boolean;
		onSaved?: (settings: BountySettings) => void;
	}

	let { open = $bindable(), onSaved }: Props = $props();

	const LABEL = 'text-2xs font-semibold tracking-wide text-muted-foreground uppercase';

	let settings = $state<BountySettings | null>(null);
	let vocabulary = $state<BountyVocabulary | null>(null);
	let loadError = $state<string | null>(null);
	let saving = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const connectable = $derived((settings?.platforms ?? []).filter((p) => p.api_provider));
	const specs = $derived<BountyEventSpec[]>(
		(settings?.notifiable_events ?? [])
			.map((kind) => vocabulary?.events.find((e) => e.kind === kind))
			.filter((e): e is BountyEventSpec => Boolean(e))
	);

	async function load() {
		try {
			[settings, vocabulary] = await Promise.all([
				bountyProgramsApi.settings(),
				bountyProgramsApi.vocabulary()
			]);
			loadError = null;
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Request failed.';
		}
	}

	$effect(() => {
		if (open) void load();
	});

	function schedule(interval: string, last: string | null, next: string | null): string {
		const parts: string[] = [];
		if (last) parts.push(`Last ${relativeTime(last)}`);
		if (interval !== SyncInterval.Off && next)
			parts.push(untilTime(next) ? `Next ${untilTime(next)}` : 'Overdue');
		return parts.join(' · ');
	}

	async function save(patch: BountySettingsUpdate, label: string) {
		saving = true;
		try {
			settings = await bountyProgramsApi.saveSettings(patch);
			onSaved?.(settings);
			toast.success(`${label} saved`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : `${label} not saved`);
			await load();
		} finally {
			saving = false;
		}
	}

	function toggleEvent(kind: string, on: boolean) {
		const current = settings?.notify_events ?? [];
		const next = on ? [...current, kind] : current.filter((k) => k !== kind);
		void save({ notify_events: [...new Set(next)] }, 'Alerts');
	}
</script>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-md">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>{routeLabels['bounty-hub']} settings</Sheet.Title>
		</Sheet.Header>

		{#if loadError && !settings}
			<EmptyState
				icon={TriangleAlertIcon}
				title="Settings not loaded"
				description={loadError}
				compact
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" size="sm" onclick={() => load()}>Retry</Button>
			</EmptyState>
		{:else if !settings}
			<div class="flex flex-col gap-3 px-5 py-6">
				<Skeleton class="h-4 w-32" />
				<Skeleton class="h-9 w-full" />
				<Skeleton class="h-9 w-full" />
			</div>
		{:else}
			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col divide-y px-5">
					<section class="flex flex-col gap-3 py-5">
						<h3 class={LABEL}>Platforms</h3>
						{#each connectable as platform (platform.platform)}
							<div class="flex items-center justify-between gap-4 text-sm">
								<span class="font-medium">{platform.label}</span>
								{#if platform.configured}
									<span class="text-xs text-muted-foreground tabular-nums">
										{platform.programs.toLocaleString()} programs
										{#if platform.private_programs > 0}
											· {platform.private_programs.toLocaleString()} private
										{/if}
									</span>
								{:else}
									<a
										href={ROUTES.settings('api-keys')}
										class="text-xs text-primary transition-colors hover:text-foreground"
									>
										Add key
									</a>
								{/if}
							</div>
						{/each}
					</section>

					<section class="flex flex-col gap-4 py-5">
						<h3 class={LABEL}>Sync</h3>
						<div class="flex items-start justify-between gap-4">
							<div class="flex min-w-0 flex-col gap-0.5">
								<span class="text-sm font-medium">Platform APIs</span>
								<span class="text-xs text-muted-foreground">
									{schedule(settings.sync_interval, settings.last_synced_at, settings.next_sync_at)}
								</span>
							</div>
							<Select.Root
								type="single"
								value={settings.sync_interval}
								onValueChange={(v) => v && save({ sync_interval: v }, 'Platform sync')}
								disabled={!isAdmin || saving}
							>
								<Select.Trigger class="h-9 w-40 shrink-0" aria-label="Platform API interval">
									{SYNC_INTERVAL_LABELS[settings.sync_interval] ?? settings.sync_interval}
								</Select.Trigger>
								<Select.Content>
									{#each Object.entries(SYNC_INTERVAL_LABELS) as [value, label] (value)}
										<Select.Item {value} {label}>{label}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						</div>
						<div class="flex items-start justify-between gap-4">
							<div class="flex min-w-0 flex-col gap-0.5">
								<span class="text-sm font-medium">Public feed</span>
								<span class="text-xs text-muted-foreground">
									{schedule(
										settings.feed_interval,
										settings.feed_synced_at,
										settings.feed_next_sync_at
									)}
								</span>
								<a
									href={externalHref(settings.feed_url)}
									target="_blank"
									rel="noreferrer noopener"
									class="w-fit text-xs text-muted-foreground transition-colors hover:text-foreground"
								>
									{settings.feed_source} · {settings.feed_license}
								</a>
							</div>
							<Select.Root
								type="single"
								value={settings.feed_interval}
								onValueChange={(v) => v && save({ feed_interval: v }, 'Feed sync')}
								disabled={!isAdmin || saving}
							>
								<Select.Trigger class="h-9 w-40 shrink-0" aria-label="Public feed interval">
									{SYNC_INTERVAL_LABELS[settings.feed_interval] ?? settings.feed_interval}
								</Select.Trigger>
								<Select.Content>
									{#each Object.entries(SYNC_INTERVAL_LABELS) as [value, label] (value)}
										<Select.Item {value} {label}>{label}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						</div>
					</section>

					<section class="flex flex-col gap-3 py-5">
						<h3 class={LABEL}>Alerts</h3>
						<label class="flex items-start justify-between gap-4" for="bounty-notify">
							<span class="flex min-w-0 flex-col gap-0.5">
								<span class="text-sm font-medium">Program changes</span>
								<span class="text-xs text-muted-foreground">
									Inbox and channels subscribed to Program changes
								</span>
							</span>
							<Switch
								id="bounty-notify"
								checked={settings.notify}
								disabled={!isAdmin || saving}
								onCheckedChange={(v) => save({ notify: v }, 'Alerts')}
							/>
						</label>
						{#if settings.notify}
							<div class="flex flex-col divide-y rounded-lg border">
								{#each specs as spec (spec.kind)}
									<label
										class="flex items-start justify-between gap-4 px-3 py-2.5"
										for="bounty-event-{spec.kind}"
									>
										<span class="flex min-w-0 flex-col gap-0.5">
											<span class="text-sm">{spec.label}</span>
											<span class="text-xs text-muted-foreground">{spec.description}</span>
										</span>
										<Switch
											id="bounty-event-{spec.kind}"
											checked={settings.notify_events.includes(spec.kind)}
											disabled={!isAdmin || saving}
											onCheckedChange={(v) => toggleEvent(spec.kind, v)}
										/>
									</label>
								{/each}
							</div>
						{/if}
						<p class="text-xs text-muted-foreground tabular-nums">
							{settings.events_recorded.toLocaleString()} changes recorded ·
							<a
								href={ROUTES.settings('notifications')}
								class="text-primary transition-colors hover:text-foreground"
							>
								Notification channels
							</a>
						</p>
					</section>
				</div>
			</ScrollArea>
			{#if !isAdmin}
				<p class="border-t px-5 py-2.5 text-xs text-muted-foreground">
					Editable by administrators.
				</p>
			{/if}
		{/if}
	</Sheet.Content>
</Sheet.Root>
