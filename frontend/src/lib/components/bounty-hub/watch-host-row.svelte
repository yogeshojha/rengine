<script lang="ts">
	import BellOffIcon from '@lucide/svelte/icons/bell-off';
	import BellIcon from '@lucide/svelte/icons/bell';
	import ScanSearchIcon from '@lucide/svelte/icons/scan-search';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import ScreenshotThumb from '$lib/components/scans/results/screenshot-thumb.svelte';
	import { HOST_STATE_VARIANT } from '$lib/config/watch';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import { WatchHostState, type WatchHost } from '$lib/types/watch';

	interface Props {
		host: WatchHost;
		onMute: (host: WatchHost) => void;
	}

	let { host, onMute }: Props = $props();

	const MAX_TECH = 4;
	const muted = $derived(host.state === WatchHostState.Muted);
	const answer = $derived(
		host.status_code === null ? null : `${host.status_code}${host.title ? ` · ${host.title}` : ''}`
	);
	const isNew = $derived(
		host.state !== WatchHostState.Known && host.state !== WatchHostState.OutOfScope
	);
</script>

<div
	class="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-b px-4 py-3 last:border-b-0"
>
	<div class="flex min-w-0 gap-3">
		{#if host.screenshot_path}
			<ScreenshotThumb
				path={host.screenshot_path}
				alt={host.name}
				class="h-12 w-20 shrink-0"
				preview
			/>
		{/if}
		<div class="flex min-w-0 flex-col gap-1">
			<div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
				<span class="font-mono text-sm break-all">{host.name}</span>
				<Badge variant={HOST_STATE_VARIANT[host.state]}>{host.state_label}</Badge>
				{#if host.is_wildcard && isNew}
					<Badge variant="outline" class="text-muted-foreground">Wildcard DNS</Badge>
				{/if}
			</div>
			<div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
				{#if answer}
					<span class="text-foreground">{answer}</span>
				{/if}
				{#if host.tech.length > 0}
					<span>{host.tech.slice(0, MAX_TECH).join(', ')}</span>
				{/if}
				{#if host.resolved_ips.length > 0}
					<span class="font-mono">{host.resolved_ips.slice(0, 2).join(', ')}</span>
				{/if}
				{#if host.reason}
					<span>{host.reason}</span>
				{/if}
			</div>
			<div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-2xs text-muted-foreground">
				<span>Seen {relativeTime(host.first_seen_at)}</span>
				{#if host.sightings > 1}
					<span class="tabular-nums">{host.sightings} certificates</span>
				{/if}
				{#if host.issuer}
					<span class="truncate">{host.issuer}</span>
				{/if}
				{#if host.matched_item}
					<span class="font-mono">
						{host.matched_item.startsWith('.') ? `*${host.matched_item}` : host.matched_item}
					</span>
				{/if}
				{#if host.alerted_at}
					<span>Alerted {relativeTime(host.alerted_at)}</span>
				{/if}
			</div>
		</div>
	</div>

	<div class="flex shrink-0 items-center gap-1">
		{#if host.scan_id}
			<Hint text="Open the probe">
				{#snippet child(props)}
					<Button
						{...props}
						href={ROUTES.scan(host.scan_id ?? '')}
						variant="ghost"
						size="icon"
						class="size-8"
						aria-label="Open the probe"
					>
						<ScanSearchIcon class="size-4" />
					</Button>
				{/snippet}
			</Hint>
		{/if}
		{#if isNew}
			<Hint text={muted ? 'Alerts resume for this host' : 'No further alerts for this host'}>
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-8"
						aria-label={muted ? 'Unmute host' : 'Mute host'}
						onclick={() => onMute(host)}
					>
						{#if muted}
							<BellIcon class="size-4" />
						{:else}
							<BellOffIcon class="size-4" />
						{/if}
					</Button>
				{/snippet}
			</Hint>
		{/if}
	</div>
</div>
