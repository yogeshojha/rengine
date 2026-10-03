<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ProgramAvatar from './program-avatar.svelte';
	import SubmissionBadge from './submission-badge.svelte';
	import { CADENCE_LABELS } from '$lib/config/watch';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { WatchHostFilter, WatchStatus, type StreamStatus, type Watch } from '$lib/types/watch';

	interface Props {
		watches: Watch[];
		loading: boolean;
		error: string | null;
		stream: StreamStatus | null;
		onOpen: (watch: Watch, filter?: WatchHostFilter, tab?: 'hosts' | 'activity') => void;
		onRetry: () => void;
		onBrowsePrograms: () => void;
	}

	let { watches, loading, error, stream, onOpen, onRetry, onBrowsePrograms }: Props = $props();

	const COLS = 'sm:grid-cols-[minmax(0,1.8fr)_repeat(3,minmax(0,1fr))_auto]';

	function baselineLine(w: Watch): string {
		if (!w.baseline.status) return 'No baseline';
		if (w.baseline.running > 0) return `Baseline running · ${w.baseline.running}`;
		if (w.baseline.last_run_at) return `Baseline ${relativeTime(w.baseline.last_run_at)}`;
		if (w.baseline.next_run_at) return `Baseline ${CADENCE_LABELS[w.cadence].toLowerCase()}`;
		return 'Baseline scheduled';
	}
</script>

{#snippet count(n: number, name: string, label: string, open: () => void)}
	<button
		type="button"
		onclick={open}
		class="flex flex-col items-start leading-tight text-left"
		aria-label={`${n} ${name} ${label}`}
	>
		<span
			class="text-lg font-semibold tabular-nums {n === 0
				? 'text-muted-foreground'
				: 'underline decoration-foreground/25 underline-offset-4 hover:text-primary'}"
		>
			{n}
		</span>
		<span class="text-2xs text-muted-foreground">
			<span class="sm:hidden">{name} · </span>{label}
		</span>
	</button>
{/snippet}

{#snippet header()}
	<div
		class="hidden {COLS} gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase sm:grid"
	>
		<span>Program</span>
		<span>New hosts</span>
		<span>Alerts</span>
		<span>Scope changes</span>
		<span class="w-32">Last certificate</span>
	</div>
{/snippet}

<div class="flex flex-col gap-3">
	{#if stream}
		<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
			<span class="flex h-5 items-center" aria-hidden="true">
				<span
					class="size-2 rounded-full {stream.running
						? 'bg-success'
						: stream.reachable
							? 'bg-warning'
							: 'bg-destructive'}"
				></span>
			</span>
			{#if stream.running}
				<span>
					Certificate stream connected · {plural(stream.items, 'apex', 'apexes')}
				</span>
				{#if stream.last_certificate_at}
					<span>Last certificate {relativeTime(stream.last_certificate_at)}</span>
				{/if}
			{:else if stream.reachable}
				<span>Certificate stream idle. No apex is watched.</span>
			{:else}
				<span>Certificate stream not running. Check that the ct-stream service is up.</span>
			{/if}
			{#if stream.last_error}
				<span class="text-destructive">
					{stream.last_error}
					{#if stream.last_error_at}
						<span class="text-muted-foreground">· {relativeTime(stream.last_error_at)}</span>
					{/if}
				</span>
			{/if}
		</div>
	{/if}

	<Card.Root class="gap-0 overflow-hidden py-0">
		{#if loading && watches.length === 0}
			<div aria-busy="true">
				{@render header()}
				{#each Array(5) as _, i (i)}
					<div
						class="grid grid-cols-1 items-center gap-3 border-b px-4 py-3 last:border-b-0 {COLS}"
					>
						<div class="flex flex-col gap-1.5">
							<Skeleton class="h-4 w-48 max-w-full" />
							<Skeleton class="h-3 w-28" />
						</div>
						<Skeleton class="hidden h-4 w-10 sm:block" />
						<Skeleton class="hidden h-4 w-10 sm:block" />
						<Skeleton class="hidden h-4 w-10 sm:block" />
						<Skeleton class="hidden h-4 w-32 sm:block" />
					</div>
				{/each}
			</div>
		{:else if error && watches.length === 0}
			<EmptyState
				icon={TriangleAlertIcon}
				title="Watched programs not loaded"
				description={error}
				compact
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" size="sm" onclick={() => onRetry()}>Retry</Button>
			</EmptyState>
		{:else if watches.length === 0}
			<EmptyState
				icon={RadarIcon}
				title="No watched programs"
				compact
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" size="sm" onclick={onBrowsePrograms}>Programs</Button>
			</EmptyState>
		{:else}
			{@render header()}
			{#each watches as watch (watch.id)}
				{@const paused = watch.status === WatchStatus.Paused}
				{@const since = watch.seen_at ? 'since last visit' : 'total'}
				<div class="grid grid-cols-1 items-center gap-3 border-b px-4 py-3 last:border-b-0 {COLS}">
					<button
						type="button"
						onclick={() => onOpen(watch)}
						class="flex min-w-0 items-center gap-3 rounded-md text-left hover:text-primary"
					>
						<ProgramAvatar name={watch.program_name} picture={watch.profile_picture} />
						<span class="flex min-w-0 flex-col gap-0.5">
							<span class="flex min-w-0 items-center gap-2">
								<span class="truncate text-sm font-medium text-foreground"
									>{watch.program_name}</span
								>
								{#if paused}
									<Badge variant="secondary">Paused</Badge>
								{/if}
								<SubmissionBadge submission={watch.submission_state} />
							</span>
							<span class="truncate text-xs text-muted-foreground">
								{bountyVocabulary.label(watch.platform)} · {plural(watch.targets, 'target')} · {baselineLine(
									watch
								)}
							</span>
						</span>
					</button>

					{@render count(watch.new_hosts, 'New hosts', since, () =>
						onOpen(watch, WatchHostFilter.Arrived)
					)}
					{@render count(watch.new_alerts, 'Alerts', since, () =>
						onOpen(watch, WatchHostFilter.Alerted)
					)}
					{@render count(watch.scope_changes, 'Scope changes', since, () =>
						onOpen(watch, WatchHostFilter.All, 'activity')
					)}

					<span class="flex w-32 flex-col leading-tight">
						{#if watch.last_certificate_at}
							<span class="font-mono text-xs">{relativeTime(watch.last_certificate_at)}</span>
							<span class="text-2xs tabular-nums text-muted-foreground">
								{watch.hosts_seen} seen · {watch.hosts_alerted} alerted
							</span>
						{:else}
							<span class="text-xs text-muted-foreground">None</span>
						{/if}
					</span>
				</div>
			{/each}
		{/if}
	</Card.Root>
</div>
