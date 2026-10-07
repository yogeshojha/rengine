<script lang="ts">
	import { BODY_ROW, HEAD_ROW } from '$lib/components/settings/columns';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import RungMeter from '$lib/components/access/rung-meter.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { expiryLabel, expiryTone, parseClient, presenceOf } from '$lib/utilities/mcp';
	import {
		AGENT_PRESENCE_DOT,
		AGENT_PRESENCE_LABELS,
		ISSUER_GONE,
		ISSUER_LAPSED,
		MCP_CAPABILITIES,
		MCP_CAPABILITY_LABELS,
		TOUCHES_TARGETS,
		ladderLevel,
		tokenUsable,
		type McpSession,
		type McpToken
	} from '$lib/types/mcp';
	import { AGENT_COL } from './columns';

	interface Props {
		tokens: McpToken[];
		sessions: McpSession[];
		now: number;
		onHistory: (token: McpToken) => void;
		onEdit: (token: McpToken) => void;
		onCut: (token: McpToken) => void;
		onDelete: (token: McpToken) => void;
	}

	let { tokens, sessions, now, onHistory, onEdit, onCut, onDelete }: Props = $props();

	const rows = $derived(
		[...tokens].sort((a, b) => {
			const ua = tokenUsable(a) ? 0 : 1;
			const ub = tokenUsable(b) ? 0 : 1;
			if (ua !== ub) return ua - ub;
			return (b.last_used_at ?? b.created_at).localeCompare(a.last_used_at ?? a.created_at);
		})
	);
</script>

<div class="@container/agents w-full" role="table" aria-label="Agents">
	<div class={HEAD_ROW} role="row">
		<div class={AGENT_COL.agent} role="columnheader">Agent</div>
		<div class={AGENT_COL.access} role="columnheader">Access</div>
		<div class={AGENT_COL.scope} role="columnheader">Scope</div>
		<div class={AGENT_COL.last} role="columnheader">Last call</div>
		<div class={AGENT_COL.expires} role="columnheader">Expires</div>
		<div class={AGENT_COL.issuer} role="columnheader">Issued by</div>
		<div class={AGENT_COL.actions} role="columnheader"><span class="sr-only">Actions</span></div>
	</div>
	{#each rows as token (token.id)}
		{@const usable = tokenUsable(token)}
		{@const presence = presenceOf(token, sessions, now)}
		{@const client = token.last_client ? parseClient(token.last_client) : null}
		{@const top = MCP_CAPABILITIES[ladderLevel(token.capabilities)]}
		{@const tone = expiryTone(token)}
		<div class="{BODY_ROW} {usable ? '' : 'text-muted-foreground'}" role="row">
			<div class="{AGENT_COL.agent} flex items-start gap-2.5" role="cell">
				<span class="flex h-5 shrink-0 items-center">
					<span class="size-2 rounded-full {AGENT_PRESENCE_DOT[presence]}" aria-hidden="true"
					></span>
				</span>
				<div class="min-w-0">
					<button
						type="button"
						class="text-left text-sm leading-5 font-medium wrap-anywhere hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
						onclick={() => onHistory(token)}
					>
						{token.name}
					</button>
					<div class="text-2xs text-muted-foreground">
						{#if !usable}
							{AGENT_PRESENCE_LABELS[presence]}
						{:else if client}
							{client.name}{#if client.version}<span class="ml-1 font-mono">{client.version}</span
								>{/if}
						{:else}
							<span class="font-mono">{token.token_prefix}…</span>
						{/if}
					</div>
				</div>
			</div>
			<div class={AGENT_COL.access} role="cell">
				{#if usable}
					<div class="flex flex-col gap-1">
						<RungMeter granted={token.capabilities} class="w-20" />
						<span
							class="text-2xs {TOUCHES_TARGETS.includes(top)
								? 'text-warning'
								: 'text-muted-foreground'}"
						>
							{MCP_CAPABILITY_LABELS[top]}
						</span>
					</div>
				{/if}
			</div>
			<div class={AGENT_COL.scope} role="cell">
				<div class="text-sm leading-5 wrap-anywhere">{token.project_name ?? 'Every project'}</div>
				<div class="text-2xs text-muted-foreground tabular-nums">
					{token.targets.toLocaleString()} target{token.targets === 1 ? '' : 's'}
				</div>
			</div>
			<div class="{AGENT_COL.last} text-sm leading-5" role="cell">
				{#if token.last_used_at}
					{relativeTime(token.last_used_at)}
					<div class="text-2xs text-muted-foreground tabular-nums">
						{token.calls.toLocaleString()} call{token.calls === 1 ? '' : 's'}
					</div>
				{:else}
					<span class="text-muted-foreground">Unused</span>
				{/if}
			</div>
			<div
				class="{AGENT_COL.expires} text-sm leading-5 {tone === 'soon'
					? 'text-warning'
					: tone === 'expired'
						? 'text-destructive'
						: ''}"
				role="cell"
			>
				{#if token.revoked}
					<span class="text-muted-foreground">Revoked</span>
				{:else}
					{expiryLabel(token)}
				{/if}
			</div>
			<div class="{AGENT_COL.issuer} text-sm leading-5 wrap-anywhere" role="cell">
				{#if token.issuer_valid}
					{token.issuer}
				{:else}
					<Hint text={ISSUER_LAPSED}>
						{#snippet child(props)}
							<span {...props} class="text-muted-foreground">{token.issuer ?? ISSUER_GONE}</span>
						{/snippet}
					</Hint>
				{/if}
			</div>
			<div class={AGENT_COL.actions} role="cell">
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="size-7"
								aria-label="{token.name} actions"
							>
								<EllipsisIcon class="size-4" />
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end">
						<DropdownMenu.Item onSelect={() => onHistory(token)}>History</DropdownMenu.Item>
						{#if usable}
							<DropdownMenu.Item onSelect={() => onEdit(token)}>Edit access</DropdownMenu.Item>
							<DropdownMenu.Separator />
							<DropdownMenu.Item variant="destructive" onSelect={() => onCut(token)}>
								Cut access
							</DropdownMenu.Item>
						{:else}
							<DropdownMenu.Separator />
							<DropdownMenu.Item variant="destructive" onSelect={() => onDelete(token)}>
								Delete
							</DropdownMenu.Item>
						{/if}
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</div>
		</div>
	{/each}
</div>
