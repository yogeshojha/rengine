<script lang="ts">
	import Send from '@lucide/svelte/icons/send';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Spinner } from '$lib/components/ui/spinner';
	import { proxyLabel, sendLabel } from './proxy';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		connectors: Connector[];
		catalog: ConnectorSpec[];
		onSend: (connectorId: string) => Promise<void> | void;
		count?: number;
		class?: string;
	}

	let { connectors, catalog, onSend, count = 0, class: className = '' }: Props = $props();

	let busy = $state(false);
	let label = $derived(sendLabel(connectors, catalog));
	let suffix = $derived(count > 1 ? ` · ${count.toLocaleString()}` : '');

	async function send(id: string) {
		busy = true;
		try {
			await onSend(id);
		} finally {
			busy = false;
		}
	}
</script>

{#if connectors.length === 1}
	<Button
		variant="outline"
		size="sm"
		class="h-8 gap-1.5 text-xs {className}"
		disabled={busy}
		onclick={() => send(connectors[0].id)}
	>
		{#if busy}<Spinner class="size-3" />{:else}<Send class="size-3" />{/if}
		{label}{suffix}
	</Button>
{:else if connectors.length > 1}
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					size="sm"
					class="h-8 gap-1.5 text-xs {className}"
					disabled={busy}
				>
					{#if busy}<Spinner class="size-3" />{:else}<Send class="size-3" />{/if}
					{label}{suffix}
					<ChevronDown class="size-3 text-muted-foreground" />
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="start" class="w-56">
			{#each connectors as c (c.id)}
				<DropdownMenu.Item onclick={() => send(c.id)}>
					<span class="flex-1 truncate">{c.name}</span>
					<span class="text-xs text-muted-foreground">{proxyLabel(c, catalog)}</span>
				</DropdownMenu.Item>
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/if}
