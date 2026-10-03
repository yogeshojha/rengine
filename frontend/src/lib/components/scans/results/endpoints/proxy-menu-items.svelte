<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import { untrack } from 'svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { proxyLabel, proxyName } from './proxy';
	import { freshenProxyPresence, proxyTool } from '$lib/stores/proxy-tool.svelte';
	import { ACTION_KIND_LABELS, HANDOFF_KINDS, presenceDot } from '$lib/config/connectors';
	import type { ActionKind } from '$lib/config/connectors';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		connectors: Connector[];
		catalog: ConnectorSpec[];
		onSend: (connectorId: string, kind: ActionKind) => void;
	}

	let { connectors, catalog, onSend }: Props = $props();

	const connector = $derived(connectors[0] ?? null);

	$effect(() => {
		const id = connector?.project_id;
		if (id) untrack(() => freshenProxyPresence(id));
	});

	function send(kind: ActionKind) {
		if (!connector) return;
		proxyTool.set(kind);
		onSend(connector.id, kind);
	}
</script>

{#if connector}
	<DropdownMenu.Item onclick={() => send(proxyTool.kind)}>
		<span class="flex size-4 shrink-0 items-center justify-center" aria-hidden="true">
			<span class="size-1.5 rounded-full {presenceDot(connector.state)}"></span>
		</span>
		Send to {proxyName(connector, catalog)}
		{ACTION_KIND_LABELS[proxyTool.kind]}
	</DropdownMenu.Item>
	<DropdownMenu.Sub>
		<DropdownMenu.SubTrigger>
			<span class="size-4" aria-hidden="true"></span>
			Send to {proxyLabel(connector, catalog)}
		</DropdownMenu.SubTrigger>
		<DropdownMenu.SubContent class="w-40">
			{#each HANDOFF_KINDS as kind (kind)}
				<DropdownMenu.Item onclick={() => send(kind)}>
					{ACTION_KIND_LABELS[kind]}
					{#if kind === proxyTool.kind}
						<Check class="ml-auto size-3.5 text-muted-foreground" />
					{/if}
				</DropdownMenu.Item>
			{/each}
		</DropdownMenu.SubContent>
	</DropdownMenu.Sub>
{/if}
