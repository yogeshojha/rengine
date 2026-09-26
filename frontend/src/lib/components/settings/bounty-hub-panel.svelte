<script lang="ts">
	import { errorMessage } from '$lib/utilities/errors';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { toast } from 'svelte-sonner';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import * as Select from '$lib/components/ui/select';
	import { Switch } from '$lib/components/ui/switch';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import CertificateStreamCard from './certificate-stream-card.svelte';
	import ConnectAlert from '$lib/components/bounty-hub/connect-alert.svelte';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import {
		EVENT_TONE,
		EVENT_TONE_BG,
		SYNC_INTERVAL_LABELS,
		assetIcon
	} from '$lib/config/bounty-programs';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import type {
		BountyEventSpec,
		BountySettings,
		BountyVocabulary
	} from '$lib/types/bounty-program';

	let settings = $state<BountySettings | null>(null);
	let vocabulary = $state<BountyVocabulary | null>(null);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let saving = $state(false);

	async function load() {
		loading = true;
		try {
			[settings, vocabulary] = await Promise.all([
				bountyProgramsApi.settings(),
				bountyProgramsApi.vocabulary()
			]);
			loadError = null;
		} catch (error) {
			loadError = errorMessage(error, 'Request failed.');
			toast.error(errorMessage(error, 'Bounty Hub settings not loaded'));
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void load();
	});

	const platforms = $derived(settings?.platforms ?? []);
	const connected = $derived(platforms.filter((p) => p.configured));
	const fedPlatforms = $derived(platforms.filter((p) => p.has_feed));

	const specs = $derived<BountyEventSpec[]>(
		(settings?.notifiable_events ?? [])
			.map((kind) => vocabulary?.events.find((e) => e.kind === kind))
			.filter((e): e is BountyEventSpec => Boolean(e))
	);

	async function save(patch: Parameters<typeof bountyProgramsApi.saveSettings>[0]) {
		saving = true;
		try {
			settings = await bountyProgramsApi.saveSettings(patch);
		} catch (error) {
			toast.error(errorMessage(error, 'Settings not saved'));
			await load();
		} finally {
			saving = false;
		}
	}

	function toggleEvent(kind: string, on: boolean) {
		const current = settings?.notify_events ?? [];
		const next = on ? [...current, kind] : current.filter((k) => k !== kind);
		void save({ notify_events: [...new Set(next)] });
	}
</script>

{#if loading}
	<div class="flex flex-col gap-6" aria-busy="true">
		{#each Array(3) as _, i (i)}
			<div class="flex flex-col gap-3 rounded-xl border p-4">
				<Skeleton class="h-4 w-40" />
				<Skeleton class="h-3 w-64 max-w-full" />
				<div class="flex flex-col gap-2 pt-1">
					{#each Array(3) as _, j (j)}
						<div class="flex items-center justify-between gap-3">
							<Skeleton class="h-4 w-48 max-w-full" />
							<Skeleton class="h-5 w-9 rounded-full" />
						</div>
					{/each}
				</div>
			</div>
		{/each}
	</div>
{:else if settings}
	<div class="flex flex-col gap-6">
		<CertificateStreamCard />
		<ConnectAlert {platforms} />
		<Card.Root class="gap-0 py-0">
			<div class="border-b p-4">
				<SectionHead title="Platform APIs" count={`${connected.length} connected`}>
					{#if settings.last_synced_at}
						<span>Last synced {relativeTime(settings.last_synced_at)}</span>
					{/if}
					{#if settings.next_sync_at}
						<span>Next {relativeTime(settings.next_sync_at)}</span>
					{/if}
				</SectionHead>
			</div>

			{#each connected as platform (platform.platform)}
				<div class="flex flex-wrap items-center justify-between gap-4 border-b px-4 py-2.5 text-sm">
					<span class="font-medium">{platform.label}</span>
					<span class="text-xs text-muted-foreground">
						{platform.programs.toLocaleString()} programs
						{#if platform.private_programs > 0}
							· {platform.private_programs.toLocaleString()} private
						{/if}
					</span>
				</div>
			{/each}

			<div class="flex flex-wrap items-center justify-between gap-4 p-4">
				<div class="flex min-w-0 flex-col gap-0.5">
					<span class="text-sm font-medium">Sync interval</span>
				</div>
				<Select.Root
					type="single"
					value={settings.sync_interval}
					onValueChange={(v) => v && save({ sync_interval: v })}
				>
					<Select.Trigger class="w-44 shrink-0">
						{SYNC_INTERVAL_LABELS[settings.sync_interval] ?? settings.sync_interval}
					</Select.Trigger>
					<Select.Content>
						{#each Object.entries(SYNC_INTERVAL_LABELS) as [value, label] (value)}
							<Select.Item {value}>{label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>

			{#if settings.sync_interval === 'off'}
				<div class="border-t px-4 py-2.5 text-xs text-muted-foreground">
					Programs update on manual refresh only.
				</div>
			{/if}
		</Card.Root>

		<Card.Root class="gap-0 py-0">
			<div class="border-b p-4">
				<SectionHead title="Public program feed" count={`${settings.feed_programs} programs`}>
					{#if settings.feed_synced_at}
						<span>Last synced {relativeTime(settings.feed_synced_at)}</span>
					{/if}
					{#if settings.feed_next_sync_at}
						<span>Next {relativeTime(settings.feed_next_sync_at)}</span>
					{/if}
				</SectionHead>
			</div>

			{#each fedPlatforms as platform (platform.platform)}
				<div class="flex flex-wrap items-center justify-between gap-4 border-b px-4 py-2.5 text-sm">
					<span class="font-medium">{platform.label}</span>
					<span class="text-xs text-muted-foreground">
						{platform.feed_programs.toLocaleString()} programs
					</span>
				</div>
			{/each}

			<div class="flex flex-wrap items-center justify-between gap-4 p-4">
				<div class="flex min-w-0 flex-col gap-0.5">
					<span class="text-sm font-medium">Sync interval</span>
					<span class="text-xs text-muted-foreground">
						From
						<a
							href={settings.feed_url}
							target="_blank"
							rel="noreferrer noopener"
							class="underline hover:text-foreground"
						>
							{settings.feed_source}
						</a>
						under {settings.feed_license}. Public programs only.
					</span>
				</div>
				<Select.Root
					type="single"
					value={settings.feed_interval}
					onValueChange={(v) => v && save({ feed_interval: v })}
				>
					<Select.Trigger class="w-44 shrink-0">
						{SYNC_INTERVAL_LABELS[settings.feed_interval] ?? settings.feed_interval}
					</Select.Trigger>
					<Select.Content>
						{#each Object.entries(SYNC_INTERVAL_LABELS) as [value, label] (value)}
							<Select.Item {value}>{label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>
		</Card.Root>

		<Card.Root class="gap-0 py-0">
			<div class="border-b p-4">
				<SectionHead title="Notifications" count={`${settings.events_recorded} recorded`}>
					<a href={ROUTES.settings('notifications')} class="hover:underline">
						Channels
						<ExternalLinkIcon class="inline size-3" />
					</a>
				</SectionHead>
			</div>

			<div class="flex flex-wrap items-center justify-between gap-4 p-4">
				<div class="flex min-w-0 flex-col gap-0.5">
					<span class="text-sm font-medium">Notify on program changes</span>
					<span class="text-xs text-muted-foreground">
						Sent to the inbox and every notification channel.
					</span>
				</div>
				<Switch
					checked={settings.notify}
					disabled={saving}
					onCheckedChange={(v) => save({ notify: v })}
				/>
			</div>

			{#if settings.notify}
				<div class="border-t">
					{#each specs as spec (spec.kind)}
						{@const Icon = assetIcon(spec.icon)}
						{@const on = settings.notify_events.includes(spec.kind)}
						<div class="flex items-center justify-between gap-4 border-b px-4 py-3 last:border-b-0">
							<div class="flex min-w-0 items-start gap-3">
								<span
									class="flex size-7 shrink-0 items-center justify-center rounded-md {EVENT_TONE_BG[
										spec.tone
									] ?? 'bg-muted'}"
								>
									<Icon class="size-3.5 {EVENT_TONE[spec.tone] ?? 'text-muted-foreground'}" />
								</span>
								<div class="flex min-w-0 flex-col gap-0.5">
									<span class="text-sm">{spec.label}</span>
									<span class="text-xs text-muted-foreground">{spec.description}</span>
								</div>
							</div>
							<Switch
								checked={on}
								disabled={saving}
								onCheckedChange={(v) => toggleEvent(spec.kind, v)}
							/>
						</div>
					{/each}
				</div>
			{:else}
				<div class="border-t px-4 py-2.5 text-xs text-muted-foreground">
					Changes are recorded in the Updates tab. Nothing is sent.
				</div>
			{/if}
		</Card.Root>
	</div>
{:else}
	<EmptyState
		icon={TriangleAlert}
		title="Bounty Hub settings not loaded"
		description={loadError ?? undefined}
	>
		<Button variant="outline" size="sm" onclick={() => void load()}>Retry</Button>
	</EmptyState>
{/if}
