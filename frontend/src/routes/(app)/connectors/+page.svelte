<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import PlugZapIcon from '@lucide/svelte/icons/plug-zap';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ConnectorList from '$lib/components/connectors/connector-list.svelte';
	import ConnectorStats from '$lib/components/connectors/connector-stats.svelte';
	import QueuePanel from '$lib/components/connectors/queue-panel.svelte';
	import DiscoveredPanel from '$lib/components/connectors/discovered-panel.svelte';
	import SettingsPanel from '$lib/components/connectors/settings-panel.svelte';
	import NewConnectorDialog from '$lib/components/connectors/new-connector-dialog.svelte';
	import SetupDialog from '$lib/components/connectors/setup-dialog.svelte';
	import { connectors } from '$lib/stores/connectors.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { CONNECTOR_POLL_MS } from '$lib/config/connectors';
	import { CONNECTOR_TABS, routeLabels, type ConnectorTab } from '$lib/config/routes';
	import type { CandidateQuery, ConnectorCreated } from '$lib/types/connector';

	const DEFAULT_TAB: ConnectorTab = CONNECTOR_TABS[0];
	const validTabs = new Set<string>(CONNECTOR_TABS);
	const TAB_LABELS: Record<ConnectorTab, string> = {
		queue: 'Queue',
		discovered: 'Discovered',
		settings: 'Settings'
	};

	const initialTab = page.url.searchParams.get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<ConnectorTab>(
		validTabs.has(initialTab) ? (initialTab as ConnectorTab) : DEFAULT_TAB
	);
	let newOpen = $state(false);
	let setupOpen = $state(false);
	let created = $state<ConnectorCreated | null>(null);
	let preset = $state<CandidateQuery | null>(null);

	const projectId = $derived(projectsStore.activeProject?.id ?? null);
	const projectSlug = $derived(projectsStore.activeProject?.slug ?? null);
	const selected = $derived(connectors.selected);
	const tabCounts = $derived<Partial<Record<ConnectorTab, number | null>>>({
		queue: selected?.queued ?? null,
		discovered: selected?.discovered ?? null
	});

	$effect(() => {
		const id = projectId;
		const slug = projectSlug;
		if (!id) return;
		untrack(() => {
			void connectors.load(id);
			void connectors.loadCatalog();
			if (slug) void targetsStore.fetchAll(slug);
		});
	});

	$effect(() => {
		if (!browser) return;
		const url = new URL(page.url);
		if (url.searchParams.get('tab') === activeTab) return;
		url.searchParams.set('tab', activeTab);
		replaceState(url, page.state);
	});

	$effect(() => {
		if (!browser) return;
		const id = projectId;
		const tab = activeTab;
		const chosen = selected?.id;
		if (!id) return;
		const poll = () => {
			if (document.hidden) return;
			void connectors.load(id, true);
			if (!chosen) return;
			if (tab === 'discovered') void connectors.loadDiscovered(chosen, id);
		};
		const timer = setInterval(poll, CONNECTOR_POLL_MS);
		return () => clearInterval(timer);
	});

	function onCreated(next: ConnectorCreated) {
		created = next;
		setupOpen = true;
	}

	function showQueue(query: CandidateQuery) {
		preset = query;
		activeTab = 'queue';
	}

	async function togglePause() {
		if (!selected || !projectId) return;
		connectors.upsert(
			await connectorsApi.update(selected.id, projectId, { paused: !selected.paused })
		);
	}
</script>

<svelte:head><title>{routeLabels.connectors} · reNgine</title></svelte:head>

<div class="space-y-6 p-4 md:p-6">
	<header class="flex flex-wrap items-start justify-between gap-4">
		<div class="min-w-0">
			<h1 class="text-xl font-semibold">{routeLabels.connectors}</h1>
		</div>
		<Button size="sm" onclick={() => (newOpen = true)}>
			<PlusIcon class="size-4" />
			New connector
		</Button>
	</header>

	{#if connectors.isLoading && connectors.items.length === 0}
		<Skeleton class="h-64 w-full" />
	{:else if connectors.items.length === 0}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<div class="px-4 py-14">
				<EmptyState icon={PlugZapIcon} title="No connectors">
					<Button size="sm" onclick={() => (newOpen = true)}>
						<PlusIcon class="size-4" />
						New connector
					</Button>
				</EmptyState>
			</div>
		</Card.Root>
	{:else}
		<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_17rem]">
			{#if selected && projectId}
				<div class="min-w-0 space-y-4">
					<ConnectorStats connector={selected} onTogglePause={togglePause} onPick={showQueue} />

					<Tabs.Root value={activeTab} onValueChange={(v) => v && (activeTab = v as ConnectorTab)}>
						<Tabs.List class="w-full sm:w-fit">
							{#each CONNECTOR_TABS as tab (tab)}
								{@const n = tabCounts[tab]}
								<Tabs.Trigger value={tab} class="gap-1.5">
									{TAB_LABELS[tab]}
									{#if n}
										<span class="text-muted-foreground text-2xs tabular-nums">{n}</span>
									{/if}
								</Tabs.Trigger>
							{/each}
						</Tabs.List>

						<Tabs.Content value="queue" class="mt-6">
							<QueuePanel
								connector={selected}
								{projectId}
								{preset}
								onPresetApplied={() => (preset = null)}
							/>
						</Tabs.Content>
						<Tabs.Content value="discovered" class="mt-6">
							<DiscoveredPanel connector={selected} {projectId} />
						</Tabs.Content>
						<Tabs.Content value="settings" class="mt-6">
							<SettingsPanel connector={selected} {projectId} onrotated={onCreated} />
						</Tabs.Content>
					</Tabs.Root>
				</div>
			{:else}
				<div></div>
			{/if}

			<div class="lg:sticky lg:top-4 lg:self-start">
				<ConnectorList selectedId={selected?.id ?? null} projectId={projectId ?? ''} />
			</div>
		</div>
	{/if}
</div>

{#if projectId}
	<NewConnectorDialog bind:open={newOpen} {projectId} oncreated={onCreated} />
{/if}
<SetupDialog bind:open={setupOpen} {created} />
