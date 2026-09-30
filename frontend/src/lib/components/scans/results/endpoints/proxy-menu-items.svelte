<script lang="ts">
	import Send from '@lucide/svelte/icons/send';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { proxyLabel } from './proxy';
	import { ACTION_KIND_HELP, ACTION_KIND_LABELS, HANDOFF_KINDS } from '$lib/config/connectors';
	import type { ActionKind } from '$lib/config/connectors';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		connectors: Connector[];
		catalog: ConnectorSpec[];
		onSend: (connectorId: string, kind: ActionKind) => void;
	}

	let { connectors, catalog, onSend }: Props = $props();
</script>

{#each connectors as c (c.id)}
	<DropdownMenu.Sub>
		<DropdownMenu.SubTrigger>
			<Send class="size-3.5" />
			Send to {proxyLabel(c, catalog)}
			{#if connectors.length > 1}
				<span class="ml-auto truncate text-xs text-muted-foreground">{c.name}</span>
			{/if}
		</DropdownMenu.SubTrigger>
		<DropdownMenu.SubContent class="w-60">
			{#each HANDOFF_KINDS as kind (kind)}
				<DropdownMenu.Item class="flex-col items-start gap-0" onclick={() => onSend(c.id, kind)}>
					<span>{ACTION_KIND_LABELS[kind]}</span>
					<span class="text-xs text-muted-foreground">{ACTION_KIND_HELP[kind]}</span>
				</DropdownMenu.Item>
			{/each}
		</DropdownMenu.SubContent>
	</DropdownMenu.Sub>
{/each}
