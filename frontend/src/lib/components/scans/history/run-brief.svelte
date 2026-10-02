<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs';
	import { Kbd } from '$lib/components/ui/kbd';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import type { ScanRead } from '$lib/types/scan';
	import { isOpenStatus } from '$lib/utilities/scan-status';
	import { BRIEF_TABS, BRIEF_TAB_LABELS, historyPrefs, type BriefTab } from './prefs.svelte';
	import BriefFindings from './brief-findings.svelte';
	import BriefChanges from './brief-changes.svelte';
	import BriefCoverage from './brief-coverage.svelte';
	import BriefEngine from './brief-engine.svelte';

	interface Props {
		projectId: string;
		scan: ScanRead;
		now: number;
		onChanged: () => void;
		onHover: (severity: string | null) => void;
	}

	let { projectId, scan, now, onChanged, onHover }: Props = $props();
	let live = $derived(isOpenStatus(scan.status));
</script>

<Tabs.Root
	value={historyPrefs.tab}
	onValueChange={(v) => (historyPrefs.tab = v as BriefTab)}
	class="gap-2"
>
	<Tabs.List class="h-8">
		{#each BRIEF_TABS as t, i (t)}
			<Tabs.Trigger value={t} class="gap-1.5 px-3 text-xs">
				{BRIEF_TAB_LABELS[t]}
				<Kbd class="hidden sm:inline-flex">{i + 1}</Kbd>
			</Tabs.Trigger>
		{/each}
	</Tabs.List>
	<Tabs.Content value="findings" class="rounded-md border bg-card">
		<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-[420px]">
			<BriefFindings
				{projectId}
				scanId={scan.id}
				findings={scan.findings}
				{live}
				{onChanged}
				{onHover}
			/>
		</ScrollArea>
	</Tabs.Content>
	<Tabs.Content value="changes">
		<BriefChanges {projectId} {scan} />
	</Tabs.Content>
	<Tabs.Content value="coverage">
		<BriefCoverage {projectId} {scan} {now} />
	</Tabs.Content>
	<Tabs.Content value="engine">
		<BriefEngine {scan} {now} />
	</Tabs.Content>
</Tabs.Root>
