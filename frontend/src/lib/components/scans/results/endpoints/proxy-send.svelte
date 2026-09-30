<script lang="ts">
	import Send from '@lucide/svelte/icons/send';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { Button } from '$lib/components/ui/button';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Spinner } from '$lib/components/ui/spinner';
	import { proxyLabel, sendLabel } from './proxy';
	import {
		ACTION_KIND_HELP,
		ACTION_KIND_LABELS,
		ActionKind,
		DEFAULT_ACTION_KIND,
		HANDOFF_KINDS
	} from '$lib/config/connectors';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		connectors: Connector[];
		catalog: ConnectorSpec[];
		onSend: (connectorId: string, kind: ActionKind) => Promise<void> | void;
		variant?: 'outline' | 'ghost';
		dense?: boolean;
		class?: string;
	}

	let {
		connectors,
		catalog,
		onSend,
		variant = 'outline',
		dense = false,
		class: className = ''
	}: Props = $props();

	let busy = $state(false);
	let label = $derived(sendLabel(connectors, catalog));
	let one = $derived(connectors.length === 1 ? connectors[0] : null);
	let height = $derived(dense ? 'h-7' : 'h-8');
	let button = $derived(
		variant === 'ghost' ? `${height} gap-2 font-medium` : `${height} gap-1.5 text-xs`
	);
	let icon = $derived(variant === 'ghost' ? 'h-3.5 w-3.5 text-muted-foreground' : 'size-3');

	async function send(id: string, kind: ActionKind) {
		busy = true;
		try {
			await onSend(id, kind);
		} finally {
			busy = false;
		}
	}
</script>

{#snippet tools(connector: Connector)}
	{#each HANDOFF_KINDS as kind (kind)}
		<DropdownMenu.Item class="flex-col items-start gap-0" onclick={() => send(connector.id, kind)}>
			<span>{ACTION_KIND_LABELS[kind]}</span>
			<span class="text-xs text-muted-foreground">{ACTION_KIND_HELP[kind]}</span>
		</DropdownMenu.Item>
	{/each}
{/snippet}

{#if connectors.length}
	<ButtonGroup class={className}>
		{#if one}
			<Button
				{variant}
				size="sm"
				class={button}
				disabled={busy}
				onclick={() => send(one.id, DEFAULT_ACTION_KIND)}
			>
				{#if busy}<Spinner class={icon} />{:else}<Send class={icon} />{/if}
				{label}
			</Button>
		{/if}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					{#if one}
						<Button
							{...props}
							{variant}
							size="icon-sm"
							class="{height} w-7"
							disabled={busy}
							aria-label="Choose the tool"
						>
							<ChevronDown class="size-3 text-muted-foreground" />
						</Button>
					{:else}
						<Button {...props} {variant} size="sm" class={button} disabled={busy}>
							{#if busy}<Spinner class={icon} />{:else}<Send class={icon} />{/if}
							{label}
							<ChevronDown class="size-3 text-muted-foreground" />
						</Button>
					{/if}
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="start" class="w-64">
				{#if one}
					{@render tools(one)}
				{:else}
					{#each connectors as c, i (c.id)}
						{#if i > 0}<DropdownMenu.Separator />{/if}
						<DropdownMenu.Group>
							<DropdownMenu.GroupHeading class="flex items-baseline gap-2">
								<span class="truncate">{c.name}</span>
								<span class="text-xs font-normal text-muted-foreground"
									>{proxyLabel(c, catalog)}</span
								>
							</DropdownMenu.GroupHeading>
							{@render tools(c)}
						</DropdownMenu.Group>
					{/each}
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</ButtonGroup>
{/if}
