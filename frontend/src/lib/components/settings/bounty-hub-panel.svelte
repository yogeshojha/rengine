<script lang="ts">
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Select from '$lib/components/ui/select';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Switch } from '$lib/components/ui/switch';
	import SectionHead from '$lib/components/section-head.svelte';
	import CertificateStreamCard from './certificate-stream-card.svelte';
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
		BountyStatus,
		BountyVocabulary
	} from '$lib/types/bounty-program';

	let settings = $state<BountySettings | null>(null);
	let vocabulary = $state<BountyVocabulary | null>(null);
	let status = $state<BountyStatus | null>(null);
	let loading = $state(true);
	let saving = $state(false);

	async function load() {
		loading = true;
		try {
			[settings, vocabulary, status] = await Promise.all([
				bountyProgramsApi.settings(),
				bountyProgramsApi.vocabulary(),
				bountyProgramsApi.status()
			]);
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Bounty Hub settings not loaded');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void load();
	});

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
			toast.error(error instanceof Error ? error.message : 'Settings not saved');
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
	<div class="flex items-center justify-center gap-2 p-12 text-sm text-muted-foreground">
		<Spinner class="size-4" />
		Loading settings
	</div>
{:else if settings}
	<div class="flex flex-col gap-6">
		<CertificateStreamCard />
		{#if status && !status.configured}
			<Card.Root class="border-dashed">
				<div class="flex flex-wrap items-center justify-between gap-3 p-4">
					<div class="flex min-w-0 items-start gap-3">
						<KeyRoundIcon class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
						<div class="flex min-w-0 flex-col gap-0.5">
							<span class="text-sm font-medium">HackerOne not connected</span>
							<span class="text-xs text-muted-foreground">
								A HackerOne token adds its public and private programs.
							</span>
						</div>
					</div>
					<Button href={ROUTES.settings('api-keys')} size="sm" variant="outline">
						Add credentials
					</Button>
				</div>
			</Card.Root>
		{/if}
		<Card.Root class="gap-0 py-0">
			<div class="border-b p-4">
				<SectionHead title="HackerOne" count={`${settings.programs} programs`}>
					{#if settings.last_synced_at}
						<span>Last synced {relativeTime(settings.last_synced_at)}</span>
					{/if}
					{#if settings.next_sync_at}
						<span>Next {relativeTime(settings.next_sync_at)}</span>
					{/if}
				</SectionHead>
			</div>

			<div class="flex flex-wrap items-center justify-between gap-4 p-4">
				<div class="flex min-w-0 flex-col gap-0.5">
					<span class="text-sm font-medium">HackerOne sync interval</span>
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

			<div class="flex flex-wrap items-center justify-between gap-4 p-4">
				<div class="flex min-w-0 flex-col gap-0.5">
					<span class="text-sm font-medium"> Bugcrowd, Intigriti and YesWeHack sync interval </span>
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
{/if}
