<script lang="ts">
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import { Switch } from '$lib/components/ui/switch';
	import { Input } from '$lib/components/ui/input';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import {
		MCP_STATE_DOT,
		MCP_STATE_LABEL,
		TOUCHES_TARGETS,
		type McpCapability,
		type McpStatus
	} from '$lib/types/mcp';
	import type { McpTab } from '$lib/config/routes';

	interface Props {
		status: McpStatus;
		canAdmin: boolean;
		onTab: (tab: McpTab) => void;
	}

	let { status, canAdmin, onTab }: Props = $props();

	const LABEL = 'text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase';
	const ROW = 'grid grid-cols-[4.25rem_minmax(0,1fr)] gap-2 text-sm';
	const KEY = 'pt-px text-xs text-muted-foreground';

	let rateDraft = $state<string | null>(null);

	const running = $derived(status.enabled);
	const serverState = $derived(running ? 'running' : ('stopped' as const));
	const grantable = $derived(
		status.capabilities.filter((c) => c.always || status.ceiling[c.key]).length
	);
	const rate = $derived(rateDraft ?? String(status.rate_limit_per_minute));

	async function setCeiling(key: McpCapability, value: boolean) {
		await mcp.save({ ceiling: { ...status.ceiling, [key]: value } });
	}

	async function commitRate() {
		if (rateDraft === null) return;
		const value = Math.min(10000, Math.max(1, Math.round(Number(rateDraft) || 0)));
		rateDraft = null;
		if (value !== status.rate_limit_per_minute) await mcp.save({ rate_limit_per_minute: value });
	}
</script>

<aside class="flex flex-col divide-y">
	<div class="flex flex-col gap-1.5 pb-4">
		<h4 class="mb-1 {LABEL}">Server</h4>
		<div class="flex items-start gap-2 text-sm">
			<span class="flex h-5 shrink-0 items-center">
				<span class="size-2 rounded-full {MCP_STATE_DOT[serverState]}" aria-hidden="true"></span>
			</span>
			<span class="leading-5">
				<span class="font-medium">{MCP_STATE_LABEL[serverState]}</span>
				{#if running && status.started_at}
					<span class="text-muted-foreground"> · since {formatShortDate(status.started_at)}</span>
				{/if}
			</span>
		</div>
		<div class={ROW}>
			<span class={KEY}>Endpoint</span>
			<span class="flex min-w-0 items-start gap-1">
				<span class="min-w-0 font-mono text-xs leading-5 wrap-anywhere">{status.endpoint}</span>
				<CopyButton value={status.endpoint} class="size-5" />
			</span>
		</div>
		<div class={ROW}>
			<span class={KEY}>Protocol</span>
			<span class="font-mono text-xs leading-5">{status.protocol_version}</span>
		</div>
		<div class={ROW}>
			<span class={KEY}>Transport</span>
			<span>HTTP and stdio</span>
		</div>
		<div class="{ROW} items-center">
			<span class={KEY}>Rate limit</span>
			{#if canAdmin}
				<span class="flex items-center gap-1.5">
					<Input
						type="number"
						min="1"
						max="10000"
						class="h-7 w-16 px-2 text-right text-xs tabular-nums"
						value={rate}
						oninput={(e) => (rateDraft = e.currentTarget.value)}
						onblur={commitRate}
						onkeydown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
						aria-label="Calls per minute for each token"
					/>
					<span class="text-xs text-muted-foreground">calls / min</span>
				</span>
			{:else}
				<span class="tabular-nums">{status.rate_limit_per_minute} calls / min</span>
			{/if}
		</div>
	</div>

	<div class="flex flex-col gap-2.5 py-4">
		<h4 class="flex items-baseline gap-2 {LABEL}">
			Ceiling
			<span class="text-xs font-medium tracking-normal normal-case tabular-nums">
				{grantable} of {status.capabilities.length}
			</span>
		</h4>
		{#each status.capabilities as capability (capability.key)}
			{@const touches = TOUCHES_TARGETS.includes(capability.key)}
			{@const on = capability.always || (status.ceiling[capability.key] ?? false)}
			<div class="flex items-start justify-between gap-3">
				<span class="flex min-w-0 flex-col">
					<span class="flex items-center gap-1.5 text-sm leading-5 font-medium">
						{capability.label}
						{#if capability.always}
							<span class="text-2xs font-normal text-muted-foreground">always on</span>
						{:else if touches && on}
							<Hint text="Tokens with this capability can send traffic to targets.">
								{#snippet child(props)}
									<span {...props} class="inline-flex text-warning">
										<TriangleAlertIcon class="size-3.5" />
									</span>
								{/snippet}
							</Hint>
						{/if}
					</span>
					<span class="text-xs leading-snug text-muted-foreground">{capability.help}</span>
				</span>
				<span class="flex h-5 shrink-0 items-center">
					<Switch
						checked={on}
						disabled={capability.always || !canAdmin || mcp.isSaving}
						onCheckedChange={(v) => setCeiling(capability.key, v)}
						aria-label="Allow {capability.label}"
					/>
				</span>
			</div>
		{/each}
		{#if !canAdmin}
			<p class="text-xs text-muted-foreground">Only an administrator can change the ceiling.</p>
		{/if}
	</div>

	<div class="flex flex-col gap-1.5 pt-4">
		<h4 class="mb-1 {LABEL}">Inventory</h4>
		<button type="button" class="group {ROW} text-left" onclick={() => onTab('tools')}>
			<span class={KEY}>Tools</span>
			<span class="flex items-center gap-1 tabular-nums group-hover:underline">
				{status.tools_available} of {status.tools_total} available
				<ArrowRight class="size-3 text-muted-foreground" />
			</span>
		</button>
		<button type="button" class="group {ROW} text-left" onclick={() => onTab('access')}>
			<span class={KEY}>Tokens</span>
			<span class="flex items-center gap-1 tabular-nums group-hover:underline">
				{status.tokens_active} active{#if status.tokens_total !== status.tokens_active}<span
						class="ml-1 text-muted-foreground">· {status.tokens_total} total</span
					>{/if}
				<ArrowRight class="size-3 text-muted-foreground" />
			</span>
		</button>
		<div class={ROW}>
			<span class={KEY}>Today</span>
			<span class="tabular-nums">
				{status.calls_today.toLocaleString()} calls{#if status.last_call_at}<span
						class="ml-1 text-muted-foreground">· last {relativeTime(status.last_call_at)}</span
					>{/if}
			</span>
		</div>
	</div>
</aside>
