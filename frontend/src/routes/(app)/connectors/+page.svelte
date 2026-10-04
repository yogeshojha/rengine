<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import LinkCard from '$lib/components/connectors/link-card.svelte';
	import ConnectDialog from '$lib/components/connectors/connect-dialog.svelte';
	import SettingsDialog from '$lib/components/connectors/settings-dialog.svelte';
	import QueuePanel, { QUEUE_PARAMS } from '$lib/components/connectors/queue-panel.svelte';
	import DiscoveredPanel from '$lib/components/connectors/discovered-panel.svelte';
	import { connectors } from '$lib/stores/connectors.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { CONNECTOR_POLL_MS, LIVE_POLL_MS, ONLINE_STATES } from '$lib/config/connectors';
	import { CONNECTOR_TABS, routeLabels, type ConnectorTab } from '$lib/config/routes';
	import type { Connector, ConnectorSpec, QueueView } from '$lib/types/connector';

	type Action = 'pause' | 'resume' | 'rotate' | 'disconnect';

	const DEFAULT_TAB: ConnectorTab = CONNECTOR_TABS[0];
	const validTabs = new Set<string>(CONNECTOR_TABS);
	const TAB_LABELS: Record<ConnectorTab, string> = {
		missed: 'Missed by scans',
		flagged: 'Flagged',
		out_of_scope: 'Out of scope',
		all: 'All requests',
		domains: 'New domains'
	};

	const initialTab =
		new URLSearchParams(browser ? location.search : page.url.search).get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<ConnectorTab>(
		validTabs.has(initialTab) ? (initialTab as ConnectorTab) : DEFAULT_TAB
	);
	let connecting = $state<string | null>(null);
	let setupOpen = $state(false);
	let secret = $state<string | null>(null);
	let settingsOpen = $state(false);
	let pending = $state<Action | null>(null);
	let working = $state(false);

	const projectId = $derived(projectsStore.activeProject?.id ?? null);
	const specs = $derived(connectors.catalog);
	const linked = $derived(connectors.selected);
	const linkedId = $derived(linked?.id ?? null);
	const linkedSpec = $derived(specs.find((s) => s.kind === linked?.kind) ?? null);
	const live = $derived(linked ? ONLINE_STATES.has(linked.state) : false);
	const ready = $derived(specs.length > 0 && connectors.fetchedProjectId === projectId);
	const tabCounts = $derived<Record<ConnectorTab, number>>({
		missed: linked?.missed ?? 0,
		flagged: linked?.flagged ?? 0,
		out_of_scope: linked?.out_of_scope ?? 0,
		all: linked?.candidates ?? 0,
		domains: linked?.discovered ?? 0
	});

	const CONFIRM: Record<Action, (title: string, c: Connector) => [string, string, string, string]> =
		{
			pause: (title) => [
				`Pause ${title}`,
				`Requests from ${title} are refused.`,
				'Pause',
				'Pausing'
			],
			resume: (title) => [`Resume ${title}`, '', 'Resume', 'Resuming'],
			rotate: (_title, c) => [
				'Rotate token',
				`Token ${c.token_prefix}… is revoked.`,
				'Rotate',
				'Rotating'
			],
			disconnect: (title) => [
				`Disconnect ${title}`,
				'The connection, its token and its recorded requests are removed.',
				'Disconnect',
				'Disconnecting'
			]
		};
	const confirmCopy = $derived(
		pending && linked && linkedSpec ? CONFIRM[pending](linkedSpec.title, linked) : null
	);

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => {
			void connectors.load(id);
			void connectors.loadCatalog();
		});
	});

	let urlProjectId: string | null = null;

	$effect(() => {
		const tab = activeTab;
		const id = projectId;
		void page.url;
		if (!browser) return;
		untrack(() => {
			const switched = urlProjectId !== null && id !== null && id !== urlProjectId;
			if (id) urlProjectId = id;
			const url = new URL(location.href);
			if (tab === DEFAULT_TAB) url.searchParams.delete('tab');
			else url.searchParams.set('tab', tab);
			if (tab === 'domains' || switched) {
				for (const key of QUEUE_PARAMS) url.searchParams.delete(key);
			}
			if (url.search === location.search) return;
			replaceState(url, page.state);
		});
	});

	$effect(() => {
		if (!browser) return;
		const id = projectId;
		const tab = activeTab;
		const chosen = linkedId;
		const every = live ? LIVE_POLL_MS : CONNECTOR_POLL_MS;
		if (!id) return;
		const poll = () => {
			if (document.hidden) return;
			void connectors.load(id, true);
			if (chosen && tab === 'domains') void connectors.loadDiscovered(chosen, id);
		};
		const timer = setInterval(poll, every);
		return () => clearInterval(timer);
	});

	$effect(() => {
		if (!setupOpen) secret = null;
	});

	function retry() {
		if (!projectId) return;
		void connectors.loadCatalog();
		void connectors.load(projectId, true);
	}

	function connectorOf(spec: ConnectorSpec): Connector | null {
		return connectors.items.find((c) => c.kind === spec.kind) ?? null;
	}

	async function connect(spec: ConnectorSpec) {
		if (!projectId) return;
		connecting = spec.kind;
		try {
			const created = await connectorsApi.create({ kind: spec.kind, project_id: projectId });
			connectors.upsert(created.connector);
			secret = created.secret;
			setupOpen = true;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Connection not created');
		} finally {
			connecting = null;
		}
	}

	async function confirm() {
		if (!pending || !linked || !projectId) return;
		const action = pending;
		working = true;
		try {
			if (action === 'disconnect') {
				await connectorsApi.remove(linked.id, projectId);
				connectors.drop(linked.id);
				setupOpen = false;
			} else if (action === 'rotate') {
				const created = await connectorsApi.rotate(linked.id, projectId);
				connectors.upsert(created.connector);
				secret = created.secret;
			} else {
				connectors.upsert(
					await connectorsApi.update(linked.id, projectId, { paused: action === 'pause' })
				);
			}
			pending = null;
			if (action === 'rotate') setupOpen = true;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Change not applied');
		} finally {
			working = false;
		}
	}

	function dismiss() {
		if (pending === 'rotate') setupOpen = true;
		pending = null;
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.connectors)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<h1 class="text-2xl font-semibold tracking-tight">{routeLabels.connectors}</h1>

	{#if !ready && connectors.error}
		<EmptyState icon={TriangleAlertIcon} title={connectors.error}>
			<Button size="sm" variant="outline" onclick={retry}>Retry</Button>
		</EmptyState>
	{:else if !ready}
		<Card.Root class="gap-3 p-5">
			<Skeleton class="h-10 w-full" />
		</Card.Root>
	{:else}
		{#each specs as spec (spec.kind)}
			<LinkCard
				{spec}
				connector={connectorOf(spec)}
				connecting={connecting === spec.kind}
				onConnect={() => connect(spec)}
				onSetup={() => (setupOpen = true)}
				onSettings={() => (settingsOpen = true)}
				onPause={() => (pending = connectorOf(spec)?.paused ? 'resume' : 'pause')}
				onDisconnect={() => (pending = 'disconnect')}
			/>
		{/each}

		{#if linked && projectId}
			<Card.Root class="gap-0 overflow-hidden py-0">
				<div class="border-b px-2">
					<CountTabs
						tabs={CONNECTOR_TABS.map((key) => ({ key, label: TAB_LABELS[key] }))}
						counts={tabCounts}
						value={activeTab}
						onChange={(key) => (activeTab = key as ConnectorTab)}
					/>
				</div>
				{#if activeTab === 'domains'}
					<DiscoveredPanel connector={linked} {projectId} />
				{:else}
					<QueuePanel connector={linked} {projectId} view={activeTab as QueueView} {live} />
				{/if}
			</Card.Root>
		{/if}
	{/if}
</div>

{#if linked && linkedSpec && projectId}
	<ConnectDialog
		bind:open={setupOpen}
		{projectId}
		spec={linkedSpec}
		connector={linked}
		{secret}
		onRotate={() => {
			setupOpen = false;
			pending = 'rotate';
		}}
	/>
	<SettingsDialog bind:open={settingsOpen} spec={linkedSpec} connector={linked} {projectId} />
{/if}

<ConfirmDialog
	open={pending !== null}
	title={confirmCopy?.[0] ?? ''}
	description={confirmCopy?.[1] || undefined}
	confirmLabel={confirmCopy?.[2] ?? 'Continue'}
	loadingLabel={confirmCopy?.[3]}
	destructive={pending === 'rotate' || pending === 'disconnect'}
	loading={working}
	onOpenChange={(v) => {
		if (!v) dismiss();
	}}
	onConfirm={confirm}
/>
