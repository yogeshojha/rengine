<script lang="ts">
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import { Switch } from '$lib/components/ui/switch';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { ROUTES } from '$lib/config/routes';
	import Hint from '$lib/components/hint.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import {
		CHANNEL_META,
		LISTENER_STATE_DOT,
		LISTENER_STATE_LABELS,
		type ChannelKind
	} from '$lib/config/channels';
	import { allowedKeys, listenerState, type ChannelStatus } from '$lib/types/remote-control';
	import type { McpCapability } from '$lib/types/mcp';

	interface Props {
		channel: ChannelKind;
		status: ChannelStatus;
		canAdmin: boolean;
	}

	let { channel, status, canAdmin }: Props = $props();

	const LABEL = 'text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase';
	const ROW = 'grid grid-cols-[4.25rem_minmax(0,1fr)] gap-2 text-sm';
	const KEY = 'pt-px text-xs text-muted-foreground';

	let rateDraft = $state<string | null>(null);
	let verifying = $state(false);
	let verified = $state<string | null>(null);

	const meta = $derived(CHANNEL_META[channel]);
	const listener = $derived(listenerState(status));
	const grantable = $derived(allowedKeys(status).size);
	const rate = $derived(rateDraft ?? String(status.rate_limit_per_minute));

	async function setCeiling(key: McpCapability, value: boolean) {
		await remoteControl.save({ ceiling: { ...status.ceiling, [key]: value } });
	}

	async function commitRate() {
		if (rateDraft === null) return;
		const value = Math.min(10000, Math.max(1, Math.round(Number(rateDraft) || 0)));
		rateDraft = null;
		if (value !== status.rate_limit_per_minute)
			await remoteControl.save({ rate_limit_per_minute: value });
	}

	async function verify() {
		verifying = true;
		verified = null;
		const result = await remoteControl.verify();
		verifying = false;
		verified = result ? (result.ok ? 'Verified' : (result.error ?? 'Not verified')) : null;
	}
</script>

<aside class="flex flex-col divide-y">
	<div class="flex flex-col gap-1.5 pb-4">
		<h4 class="mb-1 {LABEL}">Listener</h4>
		<div class="flex items-start gap-2 text-sm">
			<span class="flex h-5 shrink-0 items-center">
				<span class="size-2 rounded-full {LISTENER_STATE_DOT[listener]}" aria-hidden="true"></span>
			</span>
			<span class="leading-5">
				<span class="font-medium">{LISTENER_STATE_LABELS[listener]}</span>
				{#if listener === 'listening' && status.started_at}
					<span class="text-muted-foreground"> · since {formatShortDate(status.started_at)}</span>
				{/if}
			</span>
		</div>
		{#if status.bot}
			<div class={ROW}>
				<span class={KEY}>Bot</span>
				<span class="flex min-w-0 items-start gap-1">
					<a
						href={meta.chatUrl(status.bot.username)}
						target="_blank"
						rel="noopener noreferrer"
						class="min-w-0 font-mono text-xs leading-5 wrap-anywhere hover:underline"
					>
						@{status.bot.username}
					</a>
					<ExternalLinkIcon class="mt-1 size-3 shrink-0 text-muted-foreground" />
				</span>
			</div>
		{/if}
		<div class={ROW}>
			<span class={KEY}>API key</span>
			<span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
				<span class="min-w-0 font-mono text-xs leading-5 wrap-anywhere">
					{status.secret_masked ?? 'None'}
				</span>
				{#if canAdmin}
					<a href={ROUTES.settings('api-keys')} class="text-xs text-primary hover:underline">
						Manage
					</a>
				{/if}
				{#if canAdmin && status.configured}
					<Button
						variant="ghost"
						size="sm"
						class="h-5 px-1.5 text-xs"
						disabled={verifying}
						onclick={verify}
					>
						{verifying ? 'Verifying' : 'Verify'}
					</Button>
					{#if verified}
						<span class="text-xs {verified === 'Verified' ? 'text-success' : 'text-destructive'}">
							{verified}
						</span>
					{/if}
				{/if}
			</span>
		</div>
		{#if status.enabled}
			<div class={ROW}>
				<span class={KEY}>Last poll</span>
				<span class="text-sm">
					{status.listener.last_poll_at ? relativeTime(status.listener.last_poll_at) : 'None'}
				</span>
			</div>
			<div class={ROW}>
				<span class={KEY}>Messages</span>
				<span class="tabular-nums">{status.listener.updates_seen.toLocaleString()}</span>
			</div>
		{/if}
		{#if status.listener.last_error}
			<div class={ROW}>
				<span class={KEY}>Error</span>
				<span class="text-xs leading-5 text-destructive wrap-anywhere">
					{status.listener.last_error}
					{#if status.listener.last_error_at}
						<span class="text-muted-foreground">
							· {relativeTime(status.listener.last_error_at)}</span
						>
					{/if}
				</span>
			</div>
		{/if}
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
						aria-label="Commands per minute for each chat"
					/>
					<span class="text-xs text-muted-foreground">commands / min</span>
				</span>
			{:else}
				<span class="tabular-nums">{status.rate_limit_per_minute} commands / min</span>
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
			{@const touches = capability.touches_targets}
			{@const on = capability.always || (status.ceiling[capability.key] ?? false)}
			<div class="flex items-start justify-between gap-3">
				<span class="flex min-w-0 flex-col">
					<span class="flex items-center gap-1.5 text-sm leading-5 font-medium">
						{capability.label}
						{#if capability.always}
							<span class="text-2xs font-normal text-muted-foreground">required</span>
						{:else if touches && on}
							<Hint text="Chats with this capability can send traffic to targets.">
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
						disabled={capability.always || !canAdmin || remoteControl.isSaving}
						onCheckedChange={(v) => setCeiling(capability.key, v)}
						aria-label="Allow {capability.label}"
					/>
				</span>
			</div>
		{/each}
		<p class="text-xs text-muted-foreground">
			Capabilities above read are confirmed with the account's authenticator code.
		</p>
		{#if !canAdmin}
			<p class="text-xs text-muted-foreground">The ceiling is read-only.</p>
		{/if}
	</div>

	<div class="flex flex-col gap-1.5 pt-4">
		<h4 class="mb-1 {LABEL}">Inventory</h4>
		<div class={ROW}>
			<span class={KEY}>Chats</span>
			<span class="tabular-nums">
				{status.chats_active} active{#if status.chats_total !== status.chats_active}<span
						class="ml-1 text-muted-foreground">· {status.chats_total} total</span
					>{/if}
			</span>
		</div>
		{#if status.pending_total}
			<div class={ROW}>
				<span class={KEY}>Pending</span>
				<span class="tabular-nums text-warning">{status.pending_total} pairing</span>
			</div>
		{/if}
		<div class={ROW}>
			<span class={KEY}>Commands</span>
			<span class="tabular-nums">{status.commands_total}</span>
		</div>
		<div class={ROW}>
			<span class={KEY}>Recent</span>
			<span class="tabular-nums">
				{status.calls_recent} commands{#if status.last_call_at}<span
						class="ml-1 text-muted-foreground">· last {relativeTime(status.last_call_at)}</span
					>{/if}
			</span>
		</div>
	</div>
</aside>
