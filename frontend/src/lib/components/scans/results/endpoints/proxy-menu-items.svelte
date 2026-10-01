<script lang="ts">
	import Send from '@lucide/svelte/icons/send';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { proxyLabel } from './proxy';
	import { proxyTool } from '$lib/stores/proxy-tool.svelte';
	import { ACTION_KIND_LABELS, HANDOFF_KINDS } from '$lib/config/connectors';
	import type { ActionKind } from '$lib/config/connectors';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		connectors: Connector[];
		catalog: ConnectorSpec[];
		onSend: (connectorId: string, kind: ActionKind) => void;
	}

	let { connectors, catalog, onSend }: Props = $props();

	const connector = $derived(connectors[0] ?? null);

	function send(kind: ActionKind) {
		if (!connector) return;
		proxyTool.set(kind);
		onSend(connector.id, kind);
	}
</script>

{#if connector}
	<DropdownMenu.Item onclick={() => send(proxyTool.kind)}>
		<Send class="size-3.5" />
		Send to {ACTION_KIND_LABELS[proxyTool.kind]}
	</DropdownMenu.Item>
	<DropdownMenu.Sub>
		<DropdownMenu.SubTrigger>
			<span class="size-3.5"></span>
			Send to {proxyLabel(connector, catalog)}
		</DropdownMenu.SubTrigger>
		<DropdownMenu.SubContent class="w-40">
			{#each HANDOFF_KINDS as kind (kind)}
				<DropdownMenu.Item onclick={() => send(kind)}>{ACTION_KIND_LABELS[kind]}</DropdownMenu.Item>
			{/each}
		</DropdownMenu.SubContent>
	</DropdownMenu.Sub>
{/if}
