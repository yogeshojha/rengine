<script lang="ts">
	import Send from '@lucide/svelte/icons/send';
	import Check from '@lucide/svelte/icons/check';
	import Clock from '@lucide/svelte/icons/clock';
	import Plug from '@lucide/svelte/icons/plug';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { Button } from '$lib/components/ui/button';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Spinner } from '$lib/components/ui/spinner';
	import { proxyLabel } from './proxy';
	import { proxyTool } from '$lib/stores/proxy-tool.svelte';
	import { connectors as connectorStore } from '$lib/stores/connectors.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { untrack } from 'svelte';
	import {
		ACTION_KIND_LABELS,
		DELIVERY_POLL_MS,
		DELIVERY_WAIT_MS,
		HANDOFF_KINDS,
		type ActionKind
	} from '$lib/config/connectors';
	import { ROUTES } from '$lib/config/routes';
	import type { Connector, ConnectorSpec, HandoffResult } from '$lib/types/connector';

	type Outcome = HandoffResult | null | boolean | void;

	interface Props {
		connectors: Connector[];
		catalog: ConnectorSpec[];
		onSend: (connectorId: string, kind: ActionKind) => Promise<Outcome> | Outcome;
		variant?: 'default' | 'outline' | 'ghost';
		dense?: boolean;
		shortcut?: string;
	}

	let {
		connectors,
		catalog,
		onSend,
		variant = 'default',
		dense = false,
		shortcut
	}: Props = $props();

	const SHOWN_MS = 4000;

	let busy = $state(false);
	let done = $state<'delivered' | 'queued' | null>(null);
	let run = 0;
	let timer: ReturnType<typeof setTimeout> | undefined;

	const connector = $derived(connectors[0] ?? null);
	const proxy = $derived(connector ? proxyLabel(connector, catalog) : '');
	const tool = $derived(ACTION_KIND_LABELS[proxyTool.kind]);
	const bar = $derived(variant === 'ghost');
	const height = $derived(dense ? 'h-7' : 'h-8');
	const text = $derived(
		bar ? 'gap-2 font-medium' : dense ? 'gap-1.5 text-xs font-medium' : 'gap-1.5 font-medium'
	);
	const split = $derived(variant === 'default' ? 'border-l border-primary-foreground/25' : '');
	const icon = $derived(bar ? 'h-3.5 w-3.5' : 'size-3.5');

	$effect(() => () => {
		run++;
		clearTimeout(timer);
	});

	const projectId = $derived(projectsStore.activeProject?.id ?? null);
	const known = $derived(projectId !== null && connectorStore.fetchedProjectId === projectId);

	$effect(() => {
		const id = projectId;
		if (!id || known) return;
		untrack(() => {
			void connectorStore.load(id);
			void connectorStore.loadCatalog();
		});
	});

	/** True once the proxy has collected everything queued for it. */
	async function collected(mine: number, id: string, projectId: string): Promise<boolean> {
		const until = Date.now() + DELIVERY_WAIT_MS;
		while (Date.now() < until && mine === run) {
			await new Promise((r) => setTimeout(r, DELIVERY_POLL_MS));
			try {
				const row = (await connectorsApi.list(projectId)).find((c) => c.id === id);
				if (row) connectorStore.upsert(row);
				if (row && row.pending_actions === 0) return true;
			} catch {
				return false;
			}
		}
		return false;
	}

	async function send(kind: ActionKind) {
		if (!connector || busy) return;
		const mine = ++run;
		const { id, project_id: projectId } = connector;
		proxyTool.set(kind);
		busy = true;
		clearTimeout(timer);
		done = null;
		try {
			const outcome = await onSend(id, kind);
			if (outcome === null || outcome === false) return;
			const online = typeof outcome !== 'object' || outcome.online;
			const next = online && (await collected(mine, id, projectId)) ? 'delivered' : 'queued';
			if (mine !== run) return;
			done = next;
			timer = setTimeout(() => (done = null), SHOWN_MS);
		} finally {
			if (mine === run) busy = false;
		}
	}

	function onKey(e: KeyboardEvent) {
		if (!shortcut || e.key !== shortcut || e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		if (t?.closest('[role=menu], [role=listbox], [role=combobox]')) return;
		e.preventDefault();
		void send(proxyTool.kind);
	}
</script>

<svelte:window onkeydown={onKey} />

{#if connector}
	<ButtonGroup>
		<Button
			{variant}
			size="sm"
			class="{height} {text}"
			disabled={busy}
			onclick={() => send(proxyTool.kind)}
		>
			{#if busy}
				<Spinner class={icon} />
				Sending to {tool}
			{:else if done === 'delivered'}
				<Check class={icon} />
				Delivered to {tool}
			{:else if done === 'queued'}
				<Clock class={icon} />
				Queued for {proxy}
			{:else}
				<Send class={icon} />
				Send to {tool}
				{#if shortcut}
					<kbd class="hidden font-mono text-2xs opacity-70 sm:inline">{shortcut}</kbd>
				{/if}
			{/if}
		</Button>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						{variant}
						size="icon-sm"
						class="{height} w-7 {split}"
						disabled={busy}
						aria-label="Choose the {proxy} tool"
					>
						<ChevronDown class="size-3.5" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-44">
				<DropdownMenu.Label class="text-xs font-normal text-muted-foreground">
					Send to {proxy}
				</DropdownMenu.Label>
				{#each HANDOFF_KINDS as kind (kind)}
					<DropdownMenu.Item onclick={() => send(kind)}>
						{ACTION_KIND_LABELS[kind]}
						{#if kind === proxyTool.kind}
							<Check class="ml-auto size-3.5 text-muted-foreground" />
						{/if}
					</DropdownMenu.Item>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</ButtonGroup>
{:else if !bar && known}
	<Button variant="outline" size="sm" class="{height} {text}" href={ROUTES.connectors()}>
		<Plug class={icon} />
		Connect Burp Suite
	</Button>
{/if}
