<script lang="ts">
	import CountTabs from '$lib/components/count-tabs.svelte';
	import {
		SCAN_STATUS_TABS,
		scanStatusTabCount,
		type ScanStatusTab
	} from '$lib/utilities/scan-status';
	import type { ScanStatusCounts } from '$lib/types/scan';

	interface Props {
		active: ScanStatusTab;
		counts: ScanStatusCounts | null;
		total: number;
		onChange: (tab: ScanStatusTab) => void;
	}

	let { active, counts, total, onChange }: Props = $props();

	let countMap = $derived(
		counts
			? Object.fromEntries(
					SCAN_STATUS_TABS.map((t) => [t.key, scanStatusTabCount(t.key, counts, total)])
				)
			: null
	);

	function countClass(tab: string, n: number): string {
		if (n === 0) return 'text-muted-foreground/50';
		if (tab === 'failed') return 'text-destructive';
		if (tab === 'active') return 'text-info';
		return 'text-muted-foreground';
	}
</script>

<CountTabs
	tabs={SCAN_STATUS_TABS}
	value={active}
	counts={countMap}
	{countClass}
	onChange={(k) => onChange(k as ScanStatusTab)}
/>
