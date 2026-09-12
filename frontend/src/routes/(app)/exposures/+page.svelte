<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import ListFilterIcon from '@lucide/svelte/icons/list-filter';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import ScanEyeIcon from '@lucide/svelte/icons/scan-eye';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import RulesPanel from '$lib/components/interest/rules-panel.svelte';
	import DismissedPanel from '$lib/components/interest/dismissed-panel.svelte';
	import ExposuresTable from '$lib/components/scans/results/interesting/interesting-table.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { EXPOSURE_TABS, routeLabels, type ExposureTab } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';

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

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">{routeLabels.exposures}</h1>
		<p class="mt-1 text-sm text-muted-foreground">
			Assets matched by rules, correlation signals and AI judgement
		</p>
	</div>

	<Tabs.Root
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

		<Tabs.Content value="exposures" class="mt-6">
			{#key projectId}
				<ExposuresTable {projectId} projectWide active={activeTab === 'exposures'} />
			{/key}
		</Tabs.Content>
		<Tabs.Content value="rules" class="mt-6">
			<RulesPanel />
		</Tabs.Content>
		<Tabs.Content value="dismissed" class="mt-6">
			<DismissedPanel />
		</Tabs.Content>
	</Tabs.Root>
</div>
