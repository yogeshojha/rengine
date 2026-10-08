<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import WrenchIcon from '@lucide/svelte/icons/wrench';
	import BotIcon from '@lucide/svelte/icons/bot';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { AGENT_SKELETON } from '$lib/components/agents/columns';
	import CopyButton from '$lib/components/copy-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import PageHeader from '$lib/components/page-header.svelte';
	import PowerIcon from '@lucide/svelte/icons/power';
	import AgentsTable from '$lib/components/agents/agents-table.svelte';
	import ConnectSheet from '$lib/components/agents/connect-sheet.svelte';
	import HistorySheet from '$lib/components/agents/history-sheet.svelte';
	import SettingsSheet from '$lib/components/agents/settings-sheet.svelte';
	import ToolsSheet from '$lib/components/agents/tools-sheet.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { routeLabels } from '$lib/config/routes';
	import { MCP_POLL_MS } from '$lib/utilities/mcp';
	import { MAX_TOKENS, SERVER_STATE_DOT, SERVER_STATE_LABEL, type McpToken } from '$lib/types/mcp';

	const TICK_MS = 1000;

	let now = $state(Date.now());
	let connectOpen = $state(false);
	let editing = $state<McpToken | null>(null);
	let settingsOpen = $state(false);
	let toolsOpen = $state(false);
	let historyId = $state<string | null>(null);
	let pending = $state<{ token: McpToken; action: 'cut' | 'delete' } | null>(null);
	let confirming = $state(false);

	const status = $derived(mcp.status);
	const canAdmin = $derived(auth.user?.is_superuser ?? false);
	const running = $derived(status?.enabled ?? false);
	const serverState = $derived(running ? 'running' : 'stopped');
	const tokens = $derived(mcp.tokens);
	const titles = $derived(new Map(mcp.tools.map((t) => [t.name, t.title])));
	const history = $derived(tokens.find((t) => t.id === historyId) ?? null);
	const atLimit = $derived(tokens.filter((t) => !t.revoked).length >= MAX_TOKENS);

	$effect(() => {
		const admin = canAdmin;
		untrack(() => {
			void mcp.fetch();
			if (admin) {
				void mcp.loadTokens();
				void mcp.loadCalls(true);
				void projectsStore.fetchProjects();
			}
		});
	});

	$effect(() => {
		if (!browser || !canAdmin) return;
		const poll = () => {
			if (document.hidden) return;
			void mcp.refreshStatus(true);
			void mcp.loadTokens(true);
			if (historyId) void mcp.loadCalls(true);
		};
		const id = setInterval(poll, MCP_POLL_MS);
		const tick = setInterval(() => (now = Date.now()), TICK_MS);
		return () => {
			clearInterval(id);
			clearInterval(tick);
		};
	});

	function openConnect(row: McpToken | null) {
		editing = row;
		connectOpen = true;
	}

	function openHistory(row: McpToken) {
		historyId = row.id;
		void mcp.loadCalls(true);
	}

	async function confirm() {
		if (!pending) return;
		const { token, action } = pending;
		confirming = true;
		try {
			const ok =
				action === 'cut' ? await mcp.revokeToken(token.id) : await mcp.deleteToken(token.id);
			if (ok) pending = null;
		} finally {
			confirming = false;
		}
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.agents)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<PageHeader title={routeLabels.agents} description="MCP clients with access to this instance">
		{#snippet actions()}
			{#if status && canAdmin}
				<span
					class="inline-flex h-8 min-w-0 items-center gap-2 rounded-md border pr-1 pl-3 text-sm"
				>
					<span
						class="size-2 shrink-0 rounded-full {SERVER_STATE_DOT[serverState]}"
						aria-hidden="true"
					></span>
					<span class={running ? '' : 'text-muted-foreground'}>
						{SERVER_STATE_LABEL[serverState]}
					</span>
					<span class="hidden truncate font-mono text-xs text-muted-foreground md:inline">
						{status.endpoint}
					</span>
					<CopyButton value={status.endpoint} />
				</span>
				<Button variant="outline" size="sm" onclick={() => (toolsOpen = true)}>
					<WrenchIcon class="size-4" />
					Tools
				</Button>
				<Button variant="outline" size="sm" onclick={() => (settingsOpen = true)}>
					<SettingsIcon class="size-4" />
					Settings
				</Button>
				{#if tokens.length}
					<Hint text={atLimit ? `Limit of ${MAX_TOKENS} agents reached.` : ''}>
						{#snippet child(props)}
							<span {...props} class="inline-flex">
								<Button size="sm" disabled={atLimit} onclick={() => openConnect(null)}>
									<PlusIcon class="size-4" />
									Connect an agent
								</Button>
							</span>
						{/snippet}
					</Hint>
				{/if}
			{/if}
		{/snippet}
	</PageHeader>

	{#if !canAdmin}
		<EmptyState icon={BotIcon} title="Agents are managed by administrators" />
	{:else if !status || !mcp.tokensLoaded}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<div class="@container/agents w-full">
				<TableSkeleton lead={AGENT_SKELETON} rows={3} actions={false} />
			</div>
		</Card.Root>
	{:else if !tokens.length && !running}
		<EmptyState
			icon={PowerIcon}
			title="MCP server stopped"
			description="Start the server so agents can connect."
		>
			<LoadingButton
				size="sm"
				loading={mcp.isSaving}
				loadingLabel="Starting"
				onclick={() => mcp.setRunning(true)}
			>
				Start server
			</LoadingButton>
		</EmptyState>
	{:else if !tokens.length}
		<EmptyState icon={BotIcon} title="No agents">
			<Button size="sm" onclick={() => openConnect(null)}>
				<PlusIcon class="size-4" />
				Connect an agent
			</Button>
		</EmptyState>
	{:else}
		{#if !running}
			<div
				class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/40 bg-warning/5 px-4 py-3 text-sm"
			>
				<span class="flex items-center gap-2">
					<PowerIcon class="size-4 shrink-0 text-warning" />
					MCP server stopped. Agents cannot connect.
				</span>
				<LoadingButton
					size="sm"
					loading={mcp.isSaving}
					loadingLabel="Starting"
					onclick={() => mcp.setRunning(true)}
				>
					Start server
				</LoadingButton>
			</div>
		{/if}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<AgentsTable
				{tokens}
				sessions={status.sessions}
				{now}
				onHistory={openHistory}
				onEdit={(t) => openConnect(t)}
				onCut={(t) => (pending = { token: t, action: 'cut' })}
				onDelete={(t) => (pending = { token: t, action: 'delete' })}
			/>
		</Card.Root>
	{/if}
</div>

{#if status && canAdmin}
	<ConnectSheet bind:open={connectOpen} {status} {editing} {titles} />
	<SettingsSheet {status} bind:open={settingsOpen} />
	<ToolsSheet bind:open={toolsOpen} tools={mcp.tools} ceiling={status.ceiling} />
	<HistorySheet
		token={history}
		{titles}
		onOpenChange={(v) => {
			if (!v) historyId = null;
		}}
	/>
{/if}

<ConfirmDialog
	open={pending !== null}
	title={pending?.action === 'cut' ? 'Cut access' : 'Delete agent'}
	description={pending
		? pending.action === 'cut'
			? `Agent ${pending.token.name} is disconnected and key ${pending.token.token_prefix}… stops working.`
			: `Agent ${pending.token.name} and its key are removed.`
		: ''}
	confirmLabel={pending?.action === 'cut' ? 'Cut access' : 'Delete'}
	loadingLabel={pending?.action === 'cut' ? 'Cutting access' : 'Deleting'}
	destructive
	loading={confirming}
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirm}
/>
