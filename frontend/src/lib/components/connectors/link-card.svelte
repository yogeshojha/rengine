<script lang="ts">
	import PlugIcon from '@lucide/svelte/icons/plug';
	import PauseIcon from '@lucide/svelte/icons/pause';
	import PlayIcon from '@lucide/svelte/icons/play';
	import WrenchIcon from '@lucide/svelte/icons/wrench';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import UnplugIcon from '@lucide/svelte/icons/unplug';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import {
		CONNECTOR_STATE_DOT,
		CONNECTOR_STATE_LABELS,
		clientVersion,
		isOutdated
	} from '$lib/config/connectors';
	import { auth } from '$lib/stores/auth.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		spec: ConnectorSpec;
		connector: Connector | null;
		connecting: boolean;
		onConnect: () => void;
		onSetup: () => void;
		onSettings: () => void;
		onPause: () => void;
		onDisconnect: () => void;
	}

	let {
		spec,
		connector,
		connecting,
		onConnect,
		onSetup,
		onSettings,
		onPause,
		onDisconnect
	}: Props = $props();

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const version = $derived(clientVersion(connector?.last_client));
	const outdated = $derived(isOutdated(connector?.last_client ?? null, spec.client_file));
	const facts = $derived.by(() => {
		if (!connector) return [];
		const out: string[] = [];
		if (connector.last_seen_at) out.push(`Last request ${relativeTime(connector.last_seen_at)}`);
		out.push(plural(connector.requests_seen, 'request'));
		if (connector.pending_actions)
			out.push(`${connector.pending_actions.toLocaleString()} queued for ${spec.title}`);
		return out;
	});
</script>

<Card.Root class="gap-0 py-0">
	<div class="flex flex-wrap items-center gap-x-6 gap-y-4 px-5 py-4">
		<div class="flex min-w-0 flex-1 items-center gap-3.5">
			<span
				class="flex size-10 shrink-0 items-center justify-center rounded-lg border bg-muted/40 text-muted-foreground"
			>
				<PlugIcon class="size-5" />
			</span>
			<div class="min-w-0">
				<div class="flex flex-wrap items-center gap-x-3 gap-y-1">
					<h2 class="text-base leading-6 font-semibold">{spec.title}</h2>
					{#if connector}
						<span class="flex items-center gap-1.5 text-sm">
							<span
								class="size-2 rounded-full {CONNECTOR_STATE_DOT[connector.state]}"
								aria-hidden="true"
							></span>
							{CONNECTOR_STATE_LABELS[connector.state]}
						</span>
						{#if version}
							<span class="font-mono text-xs {outdated ? 'text-warning' : 'text-muted-foreground'}">
								extension {version}{outdated
									? ` · ${clientVersion(spec.client_file)} available`
									: ''}
							</span>
						{/if}
					{:else}
						<span class="text-sm text-muted-foreground">Not connected</span>
					{/if}
				</div>
				{#if connector}
					<p class="mt-0.5 text-sm text-muted-foreground">{facts.join(' · ')}</p>
				{/if}
			</div>
		</div>

		<div class="flex min-w-0 flex-wrap items-center gap-2">
			{#if !isAdmin}
				<span class="text-xs text-muted-foreground">Managed by administrators</span>
			{:else if connector}
				<Button variant="outline" size="sm" onclick={onPause}>
					{#if connector.paused}
						<PlayIcon class="size-4" /> Resume
					{:else}
						<PauseIcon class="size-4" /> Pause
					{/if}
				</Button>
				<Button variant="outline" size="sm" onclick={onSetup}>
					<WrenchIcon class="size-4" /> Setup
				</Button>
				<Button variant="outline" size="sm" onclick={onSettings}>
					<SettingsIcon class="size-4" /> Settings
				</Button>
				<Button
					variant="outline"
					size="sm"
					class="text-destructive hover:text-destructive"
					onclick={onDisconnect}
				>
					<UnplugIcon class="size-4" /> Disconnect
				</Button>
			{:else}
				<LoadingButton size="sm" loading={connecting} loadingLabel="Connecting" onclick={onConnect}>
					<PlugIcon class="size-4" />
					Connect {spec.title}
				</LoadingButton>
			{/if}
		</div>
	</div>
</Card.Root>
