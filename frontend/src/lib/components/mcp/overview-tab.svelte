<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import SectionHead from '$lib/components/section-head.svelte';
	import CapabilityChips from './capability-chips.svelte';
	import CallPulse from './call-pulse.svelte';
	import ConnectPanel from './connect-panel.svelte';
	import ServerRail from './server-rail.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		hourlyPulse,
		parseClient,
		SESSION_LIVE_MS,
		timeOfDay,
		trailStart,
		type PulseBucket
	} from '$lib/utilities/mcp';
	import { MCP_STATE_DOT, type McpStatus } from '$lib/types/mcp';
	import type { McpTab } from '$lib/config/routes';

	interface Props {
		status: McpStatus;
		canAdmin: boolean;
		now: number;
		onStart: () => void;
		onTab: (tab: McpTab) => void;
	}

	let { status, canAdmin, now, onStart, onTab }: Props = $props();

	let hovered = $state<PulseBucket | null>(null);

	const running = $derived(status.enabled);
	const sessions = $derived(status.sessions);
	const sessionCalls = $derived(sessions.reduce((n, s) => n + s.calls, 0));
	const pulse = $derived(hourlyPulse(mcp.calls, now));
	const pulseTotal = $derived(pulse.reduce((n, b) => n + b.calls, 0));
	const pulseFailed = $derived(pulse.reduce((n, b) => n + b.failed, 0));
	const trailFrom = $derived.by(() => {
		const start = trailStart(mcp.calls);
		if (!start) return null;
		const t = new Date(start).getTime();
		return t > now - 24 * 3_600_000 ? t : null;
	});

	const hourLabel = (ms: number) =>
		new Date(ms).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
	const isLive = (seen: string) => now - new Date(seen).getTime() < SESSION_LIVE_MS;
</script>

<Card.Root class="grid gap-0 py-0 lg:grid-cols-[minmax(0,1fr)_18.5rem]">
	<div class="flex min-w-0 flex-col px-5 lg:border-r">
		<section class="flex flex-col gap-3 py-5">
			<SectionHead title="Connected agents" count={running ? sessions.length || 'None' : null}>
				{#if running && sessions.length}
					<span class="tabular-nums"
						>{sessionCalls.toLocaleString()} calls across these sessions</span
					>
				{/if}
			</SectionHead>

			{#if !running}
				<div
					class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-dashed px-4 py-3"
				>
					<span class="text-sm text-muted-foreground">
						The server is stopped. Agents cannot connect and every call is refused.
					</span>
					{#if canAdmin}
						<Button size="sm" onclick={onStart}>Start server</Button>
					{/if}
				</div>
			{:else if sessions.length}
				<div class="divide-y rounded-md border">
					{#each sessions as session (session.token_id + session.client)}
						{@const client = parseClient(session.client)}
						{@const live = isLive(session.last_seen)}
						<div class="flex items-start gap-3 px-4 py-3">
							<span class="flex h-5 shrink-0 items-center">
								<span
									class="size-2 rounded-full border {live
										? MCP_STATE_DOT.running
										: MCP_STATE_DOT.idle}"
									aria-hidden="true"
								></span>
							</span>
							<div class="min-w-0 flex-1">
								<div class="flex flex-wrap items-center gap-x-2 gap-y-1 leading-5">
									<span class="text-sm font-medium">{client.name}</span>
									{#if client.version}
										<span class="font-mono text-xs text-muted-foreground">{client.version}</span>
									{/if}
									{#if client.kind}
										<span class="text-xs text-muted-foreground">{client.kind}</span>
									{/if}
									<CapabilityChips granted={session.capabilities} />
								</div>
								<div
									class="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground"
								>
									<span>
										token <span class="font-mono text-foreground/80">{session.token_name}</span>
									</span>
									<span>connected {relativeTime(session.first_seen)}</span>
									<span class="tabular-nums">{session.calls} calls</span>
									{#if session.last_tool}
										<span>
											last <span class="font-mono">{session.last_tool}</span>
											{relativeTime(session.last_seen)}
										</span>
									{:else}
										<span>active {relativeTime(session.last_seen)}</span>
									{/if}
								</div>
							</div>
							{#if canAdmin}
								<Button
									variant="ghost"
									size="sm"
									class="shrink-0 text-muted-foreground"
									onclick={() => mcp.disconnect(session.token_id)}
								>
									Disconnect
								</Button>
							{/if}
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-sm text-muted-foreground">
					No agent is connected. A session is listed for five minutes after its last call.
				</p>
			{/if}
		</section>

		{#if pulseTotal}
			<section class="flex flex-col gap-3 border-t py-5">
				<SectionHead
					title="Calls"
					count={trailFrom
						? `since ${timeOfDay(new Date(trailFrom).toISOString())}`
						: 'last 24 hours'}
				>
					{#if hovered}
						<span class="font-mono tabular-nums">{hourLabel(hovered.start)}</span>
						<span class="tabular-nums">{hovered.calls} calls</span>
						{#if hovered.failed}
							<span class="tabular-nums text-destructive">{hovered.failed} failed</span>
						{/if}
					{:else}
						<span class="tabular-nums">{pulseTotal.toLocaleString()} calls</span>
						{#if pulseFailed}
							<span class="flex items-center gap-1.5 tabular-nums text-destructive">
								<span class="size-1.5 rounded-full bg-destructive" aria-hidden="true"></span>
								{pulseFailed} failed
							</span>
						{/if}
						<button
							type="button"
							class="text-xs font-medium text-primary hover:underline"
							onclick={() => onTab('activity')}
						>
							Activity
						</button>
					{/if}
				</SectionHead>
				<CallPulse buckets={pulse} since={trailFrom} onHover={(b) => (hovered = b)} />
			</section>
		{/if}

		<ConnectPanel {status} />
	</div>

	<div class="border-t px-5 py-5 lg:sticky lg:top-4 lg:self-start lg:border-t-0">
		<ServerRail {status} {canAdmin} {onTab} />
	</div>
</Card.Root>
