<script lang="ts">
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Select from '$lib/components/ui/select';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Switch } from '$lib/components/ui/switch';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
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
			toast.error(error instanceof Error ? error.message : 'Could not load Bounty Hub settings');
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
			toast.error(error instanceof Error ? error.message : 'Could not save');
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
		Loading
	</div>
{:else if status && !status.configured}
	<Card.Root>
		<EmptyState
			icon={KeyRoundIcon}
			title="Connect your HackerOne account"
			description="Bounty Hub reads programs and their scope with your HackerOne API username and token."
			class="p-10"
		>
			<Button href={ROUTES.settings('api-keys')} size="sm">Add HackerOne credentials</Button>
		</EmptyState>
	</Card.Root>
{:else if settings}
	<div class="flex flex-col gap-6">
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
					<span class="text-sm font-medium">How often to ask HackerOne what changed</span>
					<span class="text-xs text-muted-foreground">
						A full sync is about 640 requests against a 600-per-minute limit, so daily is
						comfortable. Refresh from HackerOne always runs whatever this says.
					</span>
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
					Nothing leaves this instance on a timer. You will only see changes after a manual refresh.
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
					<span class="text-sm font-medium">
						How often to refresh Bugcrowd, Intigriti and YesWeHack
					</span>
					<span class="text-xs text-muted-foreground">
						Four small files from
						<a
							href={settings.feed_url}
							target="_blank"
							rel="noreferrer noopener"
							class="underline hover:text-foreground"
						>
							{settings.feed_source}
						</a>
						({settings.feed_license}), no credentials needed. Public programs only — private
						programs come from a platform API.
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
					<span class="text-sm font-medium">Tell me when a program changes</span>
					<span class="text-xs text-muted-foreground">
						Sends to the in-app inbox and every notification channel you have configured.
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
					Changes are still recorded and shown in the Bounty Hub Updates tab. Nothing is sent.
				</div>
			{/if}
		</Card.Root>
	</div>
{/if}
