<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import PanelHead from './panel-head.svelte';
	import OriginFindingRow from './origin-finding.svelte';
	import OriginDialog from '../origin-dialog.svelte';
	import { ORIGIN_EXPOSED, type OriginExposure, type OriginFinding } from '$lib/utilities/origins';

	interface Props {
		exposure: OriginExposure | null;
		onTab: (tab: string, filter?: string) => void;
	}

	let { exposure, onTab }: Props = $props();

	const SHOWN = 3;

	let selected = $state<OriginFinding | null>(null);
	let open = $state(false);

	let findings = $derived(exposure?.findings ?? []);
	let bypasses = $derived(findings.filter((f) => f.kind === ORIGIN_EXPOSED).length);
	let summary = $derived.by(() => {
		const parts: string[] = [];
		if (bypasses) parts.push(`${bypasses} reachable ${bypasses === 1 ? 'origin' : 'origins'}`);
		const other = findings.length - bypasses;
		if (other)
			parts.push(`${other} ${other === 1 ? 'address' : 'addresses'} serving a different site`);
		return parts.join(' · ');
	});

	function show(f: OriginFinding) {
		selected = f;
		open = true;
	}
</script>

{#if findings.length}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead
			title="Origin exposure"
			description="Services answering on an address directly as well as behind a CDN"
		>
			<span class="tabular-nums">{summary}</span>
		</PanelHead>
		<div class="-mt-px -ml-px flex flex-col">
			{#each findings.slice(0, SHOWN) as f (f.exposed.url)}
				<OriginFindingRow finding={f} onOpen={show} />
			{/each}
		</div>
		{#if findings.length > SHOWN}
			<div class="border-t px-5 py-3">
				<Button
					variant="link"
					size="sm"
					class="h-auto gap-1 px-0 text-xs"
					onclick={() => show(findings[SHOWN])}
				>
					{findings.length - SHOWN} more
					<ChevronRight class="size-3.5" />
				</Button>
			</div>
		{/if}
	</Card.Root>
{/if}

<OriginDialog
	finding={selected}
	{open}
	onOpenChange={(v) => (open = v)}
	onServices={(filter) => {
		open = false;
		onTab('services', filter);
	}}
/>
