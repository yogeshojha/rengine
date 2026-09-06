<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import NetworkIcon from '@lucide/svelte/icons/network';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import ServerTab from '$lib/components/mcp/server-tab.svelte';
	import ToolsTab from '$lib/components/mcp/tools-tab.svelte';
	import AccessTab from '$lib/components/mcp/access-tab.svelte';
	import ActivityTab from '$lib/components/mcp/activity-tab.svelte';
	import TokenDialog from '$lib/components/mcp/token-dialog.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { MCP_TABS, routeLabels, type McpTab } from '$lib/config/routes';

	const DEFAULT_TAB: McpTab = MCP_TABS[0];
	const validTabs = new Set<string>(MCP_TABS);
	const TAB_LABELS: Record<McpTab, string> = {
		server: 'Server',
		tools: 'Tools',
		access: 'Access',
		activity: 'Activity'
	};

	const initialTab = page.url.searchParams.get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<McpTab>(validTabs.has(initialTab) ? (initialTab as McpTab) : DEFAULT_TAB);
	let tokenDialogOpen = $state(false);

	const status = $derived(mcp.status);
	const canAdmin = $derived(auth.user?.is_superuser ?? false);

	const counts = $derived<Partial<Record<McpTab, number>>>({
		tools: status?.tools_total ?? 0,
		access: status?.tokens_active ?? 0
	});

	$effect(() => {
		void mcp.fetch();
	});

	$effect(() => {
		if (activeTab === 'access' && canAdmin) void mcp.loadTokens();
		if (activeTab === 'activity') void mcp.loadCalls();
	});

	$effect(() => {
		void projectsStore.fetchProjects();
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

	function openTokenDialog() {
		tokenDialogOpen = true;
	}
</script>

<svelte:head><title>{routeLabels.mcp} · reNgine</title></svelte:head>

<div class="space-y-6">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="flex items-center gap-2 text-2xl font-semibold tracking-tight">
				<NetworkIcon class="size-5" />
				{routeLabels.mcp}
			</h1>
			<p class="mt-1 max-w-2xl text-sm text-muted-foreground">
				Model Context Protocol access for agents, scoped by service token
			</p>
		</div>
		{#if status}
			<Badge variant={status.enabled ? 'info' : 'outline'} class="gap-1.5">
				<span
					class="size-1.5 rounded-full {status.enabled ? 'bg-current' : 'bg-muted-foreground'}"
					aria-hidden="true"
				></span>
				{status.enabled ? 'Running' : 'Stopped'}
			</Badge>
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
				<Tabs.Trigger value={tab} class="gap-1.5">
					{TAB_LABELS[tab]}
					{#if counts[tab]}
						<span class="rounded-full bg-muted px-1.5 text-[11px] tabular-nums">
							{counts[tab]}
						</span>
					{/if}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>

		<Tabs.Content value="server" class="mt-6">
			<ServerTab {canAdmin} onIssueToken={openTokenDialog} />
		</Tabs.Content>
		<Tabs.Content value="tools" class="mt-6">
			<ToolsTab />
		</Tabs.Content>
		<Tabs.Content value="access" class="mt-6">
			{#if canAdmin}
				<AccessTab {canAdmin} onIssueToken={openTokenDialog} />
			{:else}
				<p class="text-sm text-muted-foreground">
					Only an administrator can see and issue service tokens.
				</p>
			{/if}
		</Tabs.Content>
		<Tabs.Content value="activity" class="mt-6">
			<ActivityTab />
		</Tabs.Content>
	</Tabs.Root>
</div>

<TokenDialog open={tokenDialogOpen} onOpenChange={(v) => (tokenDialogOpen = v)} />
