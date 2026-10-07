<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { page } from '$app/state';
	import { goto, replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import ListFilterIcon from '@lucide/svelte/icons/list-filter';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import ScanEyeIcon from '@lucide/svelte/icons/scan-eye';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import PageHeader from '$lib/components/page-header.svelte';
	import RulesPanel from '$lib/components/interest/rules-panel.svelte';
	import DismissedPanel from '$lib/components/interest/dismissed-panel.svelte';
	import ExposuresTable from '$lib/components/scans/results/interesting/interesting-table.svelte';
	import ScopeBar from '$lib/components/dashboard/scope-bar.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { EXPOSURE_TABS, routeLabels, type ExposureTab } from '$lib/config/routes';
	import { EXPOSURE_PARAMS } from '$lib/config/interest';
	import type { IconComponent } from '$lib/config/icons';
	import { scopeFromParams, scopeToParams } from '$lib/utilities/dashboard-scope';
	import { isScoped, type TargetScope } from '$lib/utilities/surface-scope';

	const TAB_META: Record<ExposureTab, { label: string; icon: IconComponent }> = {
		exposures: { label: 'Exposures', icon: ScanEyeIcon },
		rules: { label: 'Rules', icon: ListFilterIcon },
		dismissed: { label: 'Dismissed', icon: EyeOffIcon }
	};

	const DEFAULT_TAB = EXPOSURE_TABS[0];
	const validTabs = new Set<string>(EXPOSURE_TABS);

	const initialTab = page.url.searchParams.get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<ExposureTab>(
		validTabs.has(initialTab) ? (initialTab as ExposureTab) : DEFAULT_TAB
	);
	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let scope = $derived(scopeFromParams(page.url.searchParams));
	let initialBand = $derived(page.url.searchParams.get(EXPOSURE_PARAMS.band));
	let initialKinds = $derived(page.url.searchParams.getAll(EXPOSURE_PARAMS.kind).filter(Boolean));
	let filterKey = $derived(JSON.stringify([projectId, scope, initialBand, initialKinds]));

	function setScope(next: TargetScope) {
		const params = scopeToParams(page.url.searchParams, next);
		const qs = params.toString();
		void goto(qs ? `?${qs}` : page.url.pathname, { keepFocus: true, noScroll: true });
	}

	let lastProject = '';
	$effect(() => {
		const pid = projectId;
		untrack(() => {
			if (lastProject && pid && lastProject !== pid && isScoped(scope)) setScope({});
			if (pid) lastProject = pid;
		});
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
</script>

<svelte:head><title>{pageTitle(routeLabels.exposures)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<PageHeader
		title={routeLabels.exposures}
		description="Assets that stand out, like admin panels, remote access and staging hosts"
	/>

	<Tabs.Root
		class="gap-6"
		value={activeTab}
		onValueChange={(v) => {
			if (v) activeTab = v as ExposureTab;
		}}
	>
		<Tabs.List class="w-full sm:w-fit">
			{#each EXPOSURE_TABS as tab (tab)}
				{@const Icon = TAB_META[tab].icon}
				<Tabs.Trigger value={tab} class="gap-1.5">
					<Icon class="size-4" />
					{TAB_META[tab].label}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>

		<Tabs.Content value="exposures" class="space-y-4">
			{#if projectsStore.activeProject}
				<ScopeBar
					projectSlug={projectsStore.activeProject.slug}
					{scope}
					known={[]}
					onChange={setScope}
				/>
			{/if}
			{#key filterKey}
				<ExposuresTable
					{projectId}
					projectWide
					active={activeTab === 'exposures'}
					{initialBand}
					{initialKinds}
					{scope}
				/>
			{/key}
		</Tabs.Content>
		<Tabs.Content value="rules">
			<RulesPanel />
		</Tabs.Content>
		<Tabs.Content value="dismissed">
			<DismissedPanel />
		</Tabs.Content>
	</Tabs.Root>
</div>
