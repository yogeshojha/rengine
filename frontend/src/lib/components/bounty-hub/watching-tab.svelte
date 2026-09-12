<script lang="ts">
	import RadarIcon from '@lucide/svelte/icons/radar';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Spinner } from '$lib/components/ui/spinner';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { CADENCE_LABELS } from '$lib/config/watch';
	import { PLATFORM_LABELS, SUBMISSION_STATE_LABELS } from '$lib/config/bounty-programs';
	import { SubmissionState } from '$lib/types/bounty-program';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		WatchStatus,
		type StreamStatus,
		type Watch,
		type WatchHostFilter
	} from '$lib/types/watch';

	interface Props {
		watches: Watch[];
		loading: boolean;
		stream: StreamStatus | null;
		onOpen: (watch: Watch, filter?: WatchHostFilter, tab?: 'hosts' | 'activity') => void;
		onBrowsePrograms: () => void;
	}

	let { watches, loading, stream, onOpen, onBrowsePrograms }: Props = $props();

	function initials(name: string): string {
		return name
			.split(/\s+/)
			.slice(0, 2)
			.map((w) => w[0])
			.join('')
			.toUpperCase();
	}

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

<div class="flex flex-col gap-3">
	{#if stream}
		<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
			<span class="flex h-5 items-center">
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
					Certificate stream connected · {stream.items}
					{stream.items === 1 ? 'apex' : 'apexes'}
				</span>
				{#if stream.last_certificate_at}
					<span>Last certificate {relativeTime(stream.last_certificate_at)}</span>
				{/if}
			{:else if stream.reachable}
				<span>Certificate stream idle. No apex is watched.</span>
			{:else}
				<span>Certificate stream not running. Check that the ct-stream service is up.</span>
			{/if}
			<a href={ROUTES.settings('bounty-hub')} class="hover:underline">Details</a>
		</div>
	{/if}

	<Card.Root class="gap-0 overflow-hidden py-0">
		{#if loading && watches.length === 0}
			<div class="flex items-center justify-center gap-2 p-12 text-sm text-muted-foreground">
				<Spinner class="size-4" />
				Loading watches
			</div>
		{:else if watches.length === 0}
			<EmptyState
				icon={RadarIcon}
				title="No watched programs"
				description="Watch a program to follow its scope and probe every new in-scope host."
				class="p-12"
			>
				<Button variant="outline" size="sm" onclick={onBrowsePrograms}>Programs</Button>
			</EmptyState>
		{:else}
			<div
				class="hidden grid-cols-[minmax(0,1.8fr)_repeat(3,minmax(0,1fr))_auto] gap-3 border-b px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase sm:grid"
			>
				<span>Program</span>
				<span>New hosts</span>
				<span>Alerts</span>
				<span>Scope changes</span>
				<span class="w-32">Last certificate</span>
			</div>
			{#each watches as watch (watch.id)}
				{@const paused = watch.status === WatchStatus.Paused}
				{@const since = watch.seen_at ? 'since last visit' : 'total'}
				<div
					class="grid grid-cols-1 items-center gap-3 border-b px-4 py-3 last:border-b-0 sm:grid-cols-[minmax(0,1.8fr)_repeat(3,minmax(0,1fr))_auto]"
				>
					<button
						type="button"
						onclick={() => onOpen(watch)}
						class="flex min-w-0 items-center gap-3 rounded-md text-left hover:text-primary"
					>
						<span
							class="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted/50 text-2xs font-semibold text-muted-foreground"
						>
							{#if watch.profile_picture}
								<img
									src={watch.profile_picture}
									alt=""
									class="size-full object-cover"
									loading="lazy"
								/>
							{:else}
								{initials(watch.program_name)}
							{/if}
						</span>
						<span class="flex min-w-0 flex-col gap-0.5">
							<span class="flex min-w-0 items-center gap-2">
								<span class="truncate text-sm font-medium text-foreground"
									>{watch.program_name}</span
								>
								{#if paused}
									<Badge variant="secondary">Paused</Badge>
								{/if}
								{#if watch.submission_state !== SubmissionState.Open && watch.submission_state !== SubmissionState.Unknown}
									<Badge variant="warning">
										Submissions {SUBMISSION_STATE_LABELS[
											watch.submission_state as SubmissionState
										]?.toLowerCase() ?? watch.submission_state}
									</Badge>
								{/if}
							</span>
							<span class="truncate text-xs text-muted-foreground">
								{PLATFORM_LABELS[watch.platform] ?? watch.platform} · {watch.targets}
								{watch.targets === 1 ? 'target' : 'targets'} · {baselineLine(watch)}
							</span>
						</span>
					</button>

					{@render count(watch.new_hosts, 'New hosts', since, () => onOpen(watch, 'arrived'))}
					{@render count(watch.new_alerts, 'Alerts', since, () => onOpen(watch, 'alerted'))}
					{@render count(watch.scope_changes, 'Scope changes', since, () =>
						onOpen(watch, 'all', 'activity')
					)}

					<span class="flex w-32 flex-col leading-tight">
						{#if watch.last_certificate_at}
							<span class="font-mono text-xs">{relativeTime(watch.last_certificate_at)}</span>
							<span class="text-2xs tabular-nums text-muted-foreground">
								{watch.hosts_seen} seen · {watch.hosts_alerted} alerted
							</span>
						{:else}
							<span class="text-xs text-muted-foreground">None yet</span>
						{/if}
					</span>
				</div>
			{/each}
		{/if}
	</Card.Root>
</div>
