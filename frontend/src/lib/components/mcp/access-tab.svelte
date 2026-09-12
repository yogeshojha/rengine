<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import MoreVerticalIcon from '@lucide/svelte/icons/more-vertical';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import CapabilityChips from './capability-chips.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		expiryLabel,
		expiryTone,
		parseClient,
		SESSION_LIVE_MS,
		sessionsByToken
	} from '$lib/utilities/mcp';
	import {
		MCP_STATE_DOT,
		MCP_TOKEN_STATE_LABELS,
		MCP_TOKEN_STATES,
		tokenState,
		type McpToken,
		type McpTokenState
	} from '$lib/types/mcp';

	interface Props {
		canAdmin: boolean;
		now: number;
		onIssueToken: () => void;
	}

	let { canAdmin, now, onIssueToken }: Props = $props();

	const ALL = 'all';
	const HEAD =
		'px-4 py-2 text-left text-2xs font-semibold tracking-wider text-muted-foreground uppercase whitespace-nowrap';

	let filter = $state<string>(ALL);
	let pending = $state<{ token: McpToken; action: 'revoke' | 'delete' } | null>(null);

	const stateOf = (t: McpToken): McpTokenState => {
		const base = tokenState(t);
		return base === 'active' && expiryTone(t) === 'soon' ? 'expiring' : base;
	};
	const usable = (s: McpTokenState) => s === 'active' || s === 'expiring';

	const tokens = $derived(
		[...mcp.tokens].sort((a, b) => {
			const ua = usable(stateOf(a)) ? 0 : 1;
			const ub = usable(stateOf(b)) ? 0 : 1;
			if (ua !== ub) return ua - ub;
			return (b.last_used_at ?? b.created_at).localeCompare(a.last_used_at ?? a.created_at);
		})
	);
	const counts = $derived.by(() => {
		const out: Record<string, number> = { [ALL]: tokens.length };
		for (const s of MCP_TOKEN_STATES) out[s] = tokens.filter((t) => stateOf(t) === s).length;
		return out;
	});
	const tabs = $derived([
		{ key: ALL, label: 'All' },
		...MCP_TOKEN_STATES.filter((s) => counts[s] > 0).map((s) => ({
			key: s,
			label: MCP_TOKEN_STATE_LABELS[s]
		}))
	]);
	const partitioned = $derived(tabs.length > 2);
	const shown = $derived(tokens.filter((t) => filter === ALL || stateOf(t) === filter));
	const launching = $derived(
		tokens.filter((t) => usable(stateOf(t)) && t.capabilities.includes('launch')).length
	);
	const liveByToken = $derived(sessionsByToken(mcp.status?.sessions ?? []));

	async function confirm() {
		if (!pending) return;
		const { token, action } = pending;
		pending = null;
		if (action === 'revoke') await mcp.revokeToken(token.id);
		else await mcp.deleteToken(token.id);
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	{#if tokens.length}
		<div class="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-b px-2">
			{#if partitioned}
				<CountTabs {tabs} value={filter} {counts} onChange={(k) => (filter = k)} />
			{:else}
				<span class="px-3 pb-2.5 text-sm font-medium">
					Service tokens
					<span class="ml-1 text-xs text-muted-foreground tabular-nums">{tokens.length}</span>
				</span>
			{/if}
			<div class="flex items-center gap-3 pr-3 pb-2.5 text-xs text-muted-foreground">
				{#if launching}
					<span class="flex items-center gap-1.5 text-warning">
						<span class="size-1.5 rounded-full bg-warning" aria-hidden="true"></span>
						{launching} can launch scans
					</span>
				{/if}
				<span class="tabular-nums">
					{counts.active + counts.expiring} of {tokens.length} active
				</span>
			</div>
		</div>

		<div class="overflow-x-auto">
			<table class="w-full min-w-[52rem] text-sm">
				<thead>
					<tr class="border-b bg-muted/40">
						<th class={HEAD}>Token</th>
						<th class={HEAD}>Scope</th>
						<th class={HEAD}>Capabilities</th>
						<th class={HEAD}>Usage</th>
						<th class={HEAD}>Expires</th>
						<th class={HEAD}><span class="sr-only">Actions</span></th>
					</tr>
				</thead>
				<tbody>
					{#each shown as token (token.id)}
						{@const state = stateOf(token)}
						{@const live = liveByToken.get(token.id) ?? []}
						{@const client = token.last_client ? parseClient(token.last_client) : null}
						{@const tone = expiryTone(token)}
						<tr class="border-b last:border-b-0 {usable(state) ? '' : 'text-muted-foreground'}">
							<td class="px-4 py-2.5">
								<div class="min-w-0">
									<div class="flex flex-wrap items-center gap-2 leading-5">
										<span class="max-w-[18rem] truncate font-medium">{token.name}</span>
										{#if live.length}
											{@const recent = live.some(
												(s) => now - new Date(s.last).getTime() < SESSION_LIVE_MS
											)}
											<Hint
												text="Connected · {live.map((s) => parseClient(s.client).name).join(', ')}"
											>
												{#snippet child(props)}
													<span {...props} class="flex h-5 items-center">
														<span
															class="size-2 rounded-full border {recent
																? MCP_STATE_DOT.running
																: MCP_STATE_DOT.idle}"
														></span>
													</span>
												{/snippet}
											</Hint>
										{/if}
										{#if state === 'revoked' || state === 'expired'}
											<span class="text-2xs text-muted-foreground">
												{MCP_TOKEN_STATE_LABELS[state]}
											</span>
										{/if}
									</div>
									<div class="font-mono text-xs text-muted-foreground">{token.token_prefix}…</div>
								</div>
							</td>
							<td class="px-4 py-2.5 whitespace-nowrap">
								{#if token.project_name}
									{token.project_name}
								{:else}
									<span class="text-muted-foreground">Every project</span>
								{/if}
							</td>
							<td class="px-4 py-2.5">
								<CapabilityChips granted={token.capabilities} ladder class="flex-nowrap" />
							</td>
							<td class="px-4 py-2.5 whitespace-nowrap">
								{#if token.last_used_at}
									<div class="leading-5">
										<span class="tabular-nums">{token.calls.toLocaleString()} calls</span>
										<span class="text-muted-foreground"> · {relativeTime(token.last_used_at)}</span>
									</div>
									{#if client}
										<div class="text-xs text-muted-foreground">
											{client.name}{#if client.version}
												<span class="ml-1 font-mono">{client.version}</span>{/if}
										</div>
									{/if}
								{:else}
									<span class="text-muted-foreground">Never used</span>
								{/if}
							</td>
							<td
								class="px-4 py-2.5 whitespace-nowrap {tone === 'soon'
									? 'text-warning'
									: tone === 'expired'
										? 'text-destructive'
										: token.expires_at
											? ''
											: 'text-muted-foreground'}"
							>
								{#if state === 'revoked'}
									<span class="text-muted-foreground">—</span>
								{:else}
									{expiryLabel(token)}
								{/if}
							</td>
							<td class="w-12 px-2 py-2.5 text-right">
								{#if canAdmin}
									<DropdownMenu.Root>
										<DropdownMenu.Trigger>
											{#snippet child({ props })}
												<Button {...props} variant="ghost" size="icon" class="size-7">
													<MoreVerticalIcon class="size-4" />
													<span class="sr-only">Token actions</span>
												</Button>
											{/snippet}
										</DropdownMenu.Trigger>
										<DropdownMenu.Content align="end">
											{#if usable(state)}
												<DropdownMenu.Item onSelect={() => (pending = { token, action: 'revoke' })}>
													Revoke
												</DropdownMenu.Item>
											{/if}
											<DropdownMenu.Item
												variant="destructive"
												onSelect={() => (pending = { token, action: 'delete' })}
											>
												Delete
											</DropdownMenu.Item>
										</DropdownMenu.Content>
									</DropdownMenu.Root>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<div class="p-5">
			<EmptyState
				compact
				icon={KeyRoundIcon}
				title="No service tokens"
				description="An agent needs a service token to reach this instance."
			>
				{#if canAdmin}
					<Button size="sm" onclick={onIssueToken}>New token</Button>
				{/if}
			</EmptyState>
		</div>
	{/if}
</Card.Root>

<ConfirmDialog
	open={pending !== null}
	title={pending?.action === 'revoke' ? 'Revoke this token?' : 'Delete this token?'}
	description={pending
		? `${pending.token.name} stops working on its next call and any connected agent loses access. Scans it started keep running. This action cannot be undone.`
		: ''}
	confirmLabel={pending?.action === 'revoke' ? 'Revoke' : 'Delete'}
	destructive
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirm}
/>
