<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import NetworkIcon from '@lucide/svelte/icons/network';
	import PlayIcon from '@lucide/svelte/icons/play';
	import SquareIcon from '@lucide/svelte/icons/square';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import OverviewTab from '$lib/components/mcp/overview-tab.svelte';
	import ToolsTab from '$lib/components/mcp/tools-tab.svelte';
	import AccessTab from '$lib/components/mcp/access-tab.svelte';
	import ActivityTab from '$lib/components/mcp/activity-tab.svelte';
	import TokenDialog from '$lib/components/mcp/token-dialog.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { MCP_TABS, routeLabels, type McpTab } from '$lib/config/routes';
	import { MCP_STATE_DOT, MCP_STATE_LABEL, MCP_TAB_LABELS } from '$lib/types/mcp';
	import { MCP_POLL_MS } from '$lib/utilities/mcp';
	import { relativeTime } from '$lib/utilities/dates';

	const DEFAULT_TAB: McpTab = MCP_TABS[0];
	const validTabs = new Set<string>(MCP_TABS);
	const TICK_MS = 1000;

	const initialTab = page.url.searchParams.get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<McpTab>(validTabs.has(initialTab) ? (initialTab as McpTab) : DEFAULT_TAB);
	let tokenDialogOpen = $state(false);
	let confirmStop = $state(false);
	let now = $state(Date.now());

	const status = $derived(mcp.status);
	const running = $derived(status?.enabled ?? false);
	const serverState = $derived(running ? 'running' : ('stopped' as const));
	const sessions = $derived(status?.sessions ?? []);
	const canAdmin = $derived(auth.user?.is_superuser ?? false);

	const counts = $derived<Partial<Record<McpTab, number | null>>>({
		tools: status?.tools_total ?? null,
		access: status?.tokens_active ?? null,
		activity: mcp.callsLoadedAt ? mcp.calls.length : null
	});

	$effect(() => {
		void mcp.fetch();
		void mcp.loadCalls(true);
	});

	$effect(() => {
		if (activeTab === 'access' && canAdmin) void mcp.loadTokens();
	});

	$effect(() => {
		void projectsStore.fetchProjects();
	});

	$effect(() => {
		if (!browser) return;
		const tab = activeTab;
		const poll = () => {
			if (document.hidden) return;
			void mcp.refreshStatus(true);
			if (tab === 'activity' || tab === 'server' || tab === 'tools') void mcp.loadCalls(true);
			if (tab === 'access' && canAdmin) void mcp.loadTokens();
		};
		const id = setInterval(poll, MCP_POLL_MS);
		const tick = setInterval(() => (now = Date.now()), TICK_MS);
		return () => {
			clearInterval(id);
			clearInterval(tick);
		};
	});

	$effect(() => {
		const tab = activeTab;
		if (!browser) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (tab === DEFAULT_TAB) params.delete('tab');
		else params.set('tab', tab);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

	function setTab(tab: McpTab) {
		activeTab = tab;
	}

	async function start() {
		await mcp.setRunning(true);
	}

	async function stop() {
		confirmStop = false;
		await mcp.setRunning(false);
	}

	function requestStop() {
		if (sessions.length) confirmStop = true;
		else void stop();
	}
</script>

<svelte:head><title>{routeLabels.mcp} · reNgine</title></svelte:head>

<div class="space-y-6">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="min-w-0">
			<h1 class="flex items-center gap-2 text-2xl font-semibold tracking-tight">
				<NetworkIcon class="size-5" />
				{routeLabels.mcp}
			</h1>
			<p class="mt-1 max-w-2xl text-sm text-muted-foreground">
				Model Context Protocol access for agents, scoped by service token
			</p>
		</div>
		{#if status}
			<div class="flex flex-wrap items-center gap-2">
				<span
					class="inline-flex h-8 items-center gap-2 rounded-md border px-3 text-sm {running
						? ''
						: 'text-muted-foreground'}"
				>
					<span class="size-2 rounded-full {MCP_STATE_DOT[serverState]}" aria-hidden="true"></span>
					{MCP_STATE_LABEL[serverState]}
					{#if running && status.started_at}
						<span class="text-xs text-muted-foreground">
							{relativeTime(status.started_at).replace(' ago', '')}
						</span>
					{/if}
				</span>
				{#if canAdmin}
					{#if running}
						<Button
							variant="outline"
							size="sm"
							disabled={mcp.isSaving}
							onclick={requestStop}
							class="text-destructive hover:text-destructive"
						>
							<SquareIcon class="size-4" />
							Stop server
						</Button>
					{:else}
						<LoadingButton size="sm" loading={mcp.isSaving} onclick={start}>
							<PlayIcon class="size-4" />
							Start server
						</LoadingButton>
					{/if}
					<Hint
						text={status.tokens_total >= 50 ? 'This instance holds the maximum of 50 tokens.' : ''}
					>
						{#snippet child(props)}
							<span {...props} class="inline-flex">
								<Button
									size="sm"
									variant={running ? 'default' : 'outline'}
									disabled={status.tokens_total >= 50}
									onclick={() => (tokenDialogOpen = true)}
								>
									<PlusIcon class="size-4" />
									New token
								</Button>
							</span>
						{/snippet}
					</Hint>
				{/if}
			</div>
		{/if}
	</div>

	<Tabs.Root
		value={activeTab}
		onValueChange={(v) => {
			if (v) activeTab = v as McpTab;
		}}
	>
		<Tabs.List class="w-full sm:w-fit">
			{#each MCP_TABS as tab (tab)}
				{@const n = counts[tab]}
				<Tabs.Trigger value={tab} class="gap-1.5">
					{MCP_TAB_LABELS[tab]}
					{#if n}
						<span class="text-[11px] text-muted-foreground tabular-nums">{n}</span>
					{/if}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>

		<Tabs.Content value="server" class="mt-6">
			{#if status}
				<OverviewTab {status} {canAdmin} {now} onStart={start} onTab={setTab} />
			{:else}
				<div class="grid gap-x-8 gap-y-6 lg:grid-cols-[minmax(0,1fr)_18.5rem]">
					<div class="flex flex-col gap-3">
						<Skeleton class="h-4 w-40" />
						<Skeleton class="h-16 w-full" />
						<Skeleton class="h-40 w-full" />
					</div>
					<Skeleton class="h-64 w-full" />
				</div>
			{/if}
		</Tabs.Content>
		<Tabs.Content value="tools" class="mt-6">
			<ToolsTab {canAdmin} onTab={setTab} />
		</Tabs.Content>
		<Tabs.Content value="access" class="mt-6">
			{#if canAdmin}
				<AccessTab {canAdmin} {now} onIssueToken={() => (tokenDialogOpen = true)} />
			{:else}
				<p class="text-sm text-muted-foreground">
					Only an administrator can see and issue service tokens.
				</p>
			{/if}
		</Tabs.Content>
		<Tabs.Content value="activity" class="mt-6">
			<ActivityTab {now} />
		</Tabs.Content>
	</Tabs.Root>
</div>

<TokenDialog open={tokenDialogOpen} onOpenChange={(v) => (tokenDialogOpen = v)} />

<ConfirmDialog
	bind:open={confirmStop}
	title="Stop the MCP server?"
	description="{sessions.length} connected agent{sessions.length === 1
		? ' is'
		: 's are'} disconnected immediately and every call is refused until the server is started again. Scans an agent started keep running. Tokens stay valid."
	confirmLabel="Stop server"
	destructive
	loading={mcp.isSaving}
	onOpenChange={(v) => (confirmStop = v)}
	onConfirm={stop}
/>
