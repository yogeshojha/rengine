<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import Clock from '@lucide/svelte/icons/clock';
	import Plug from '@lucide/svelte/icons/plug';
	import Send from '@lucide/svelte/icons/send';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { ButtonGroup } from '$lib/components/ui/button-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Spinner } from '$lib/components/ui/spinner';
	import { confirmSend, proxyLabel, proxyName } from './proxy';
	import {
		freshenProxyPresence,
		proxyTool,
		watchProxyPresence
	} from '$lib/stores/proxy-tool.svelte';
	import { connectors as connectorStore } from '$lib/stores/connectors.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import {
		ACTION_KIND_LABELS,
		DELIVERY_POLL_MS,
		DELIVERY_WAIT_MS,
		HANDOFF_KINDS,
		HANDOFF_SHOWN_MS,
		offlineNote,
		type ActionKind
	} from '$lib/config/connectors';
	import { ROUTES } from '$lib/config/routes';
	import { keyTaken, underLayer } from '$lib/utilities/layers';
	import { cn } from '$lib/utils';
	import type { Connector, ConnectorSpec, HandoffResult } from '$lib/types/connector';

	type Outcome = HandoffResult | null | boolean | void;
	type Phase = 'idle' | 'sending' | 'delivered' | 'queued';

	interface Props {
		connectors: Connector[];
		catalog: ConnectorSpec[];
		onSend: (connectorId: string, kind: ActionKind) => Promise<Outcome> | Outcome;
		count?: number | null;
		variant?: 'outline' | 'ghost';
		dense?: boolean;
		shortcut?: string;
		class?: string;
	}

	let {
		connectors,
		catalog,
		onSend,
		count = 1,
		variant = 'outline',
		dense = false,
		shortcut,
		class: className
	}: Props = $props();

	let phase = $state<Phase>('idle');
	let root = $state<HTMLElement | null>(null);
	let run = 0;
	let timer: ReturnType<typeof setTimeout> | undefined;

	const connector = $derived(connectors[0] ?? null);
	const proxy = $derived(connector ? proxyLabel(connector, catalog) : '');
	const name = $derived(connector ? proxyName(connector, catalog) : '');
	const tool = $derived(ACTION_KIND_LABELS[proxyTool.kind]);
	const note = $derived(connector ? offlineNote(connector.state, proxy) : null);
	const action = $derived(`Send to ${name} ${tool}`);
	const compact = $derived(variant === 'outline' || dense);
	const main = $derived(
		compact
			? 'h-auto gap-1.5 px-2.5 text-xs font-medium has-[>svg]:px-2.5'
			: 'h-auto gap-2 px-3 font-medium has-[>svg]:px-3'
	);
	const narrow = $derived(
		compact ? 'h-auto w-6 px-0 has-[>svg]:px-0' : 'h-auto w-7 px-0 has-[>svg]:px-0'
	);
	const icon = $derived(compact ? 'size-3' : 'size-3.5');
	const tone = $derived(
		phase === 'delivered'
			? 'text-success hover:text-success'
			: phase === 'queued'
				? 'text-warning hover:text-warning'
				: ''
	);

	const projectId = $derived(projectsStore.activeProject?.id ?? null);
	const known = $derived(projectId !== null && connectorStore.fetchedProjectId === projectId);

	$effect(() => () => {
		run++;
		clearTimeout(timer);
	});

	$effect(() => {
		const id = projectId;
		if (!id) return;
		if (variant === 'ghost') {
			untrack(() => freshenProxyPresence(id));
			return;
		}
		return untrack(() => watchProxyPresence(id));
	});

	function freshen() {
		if (projectId) freshenProxyPresence(projectId);
	}

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

	async function settle(mine: number, outcome: Outcome, id: string, projectId: string) {
		const online = typeof outcome !== 'object' || outcome === null || outcome.online;
		if (!online) void connectorStore.load(projectId, true);
		const next = online && (await collected(mine, id, projectId)) ? 'delivered' : 'queued';
		if (mine !== run) return;
		phase = next;
		timer = setTimeout(() => {
			if (mine === run) phase = 'idle';
		}, HANDOFF_SHOWN_MS);
	}

	async function send(kind: ActionKind) {
		if (!connector || phase === 'sending') return;
		const { id, project_id: projectId } = connector;
		if (!(await confirmSend(connector, catalog, kind, count))) return;
		if (connectors[0]?.id !== id) return;
		const mine = ++run;
		proxyTool.set(kind);
		clearTimeout(timer);
		phase = 'sending';
		let outcome: Outcome = null;
		try {
			outcome = await onSend(id, kind);
		} catch {
			outcome = null;
		}
		if (mine !== run) return;
		if (outcome === null || outcome === false) {
			phase = 'idle';
			return;
		}
		void settle(mine, outcome, id, projectId);
	}

	function onKey(e: KeyboardEvent) {
		if (!shortcut || e.key !== shortcut || e.repeat || e.defaultPrevented) return;
		if (e.metaKey || e.ctrlKey || e.altKey || !connector) return;
		if (keyTaken(e.target) || underLayer(root)) return;
		e.preventDefault();
		void send(proxyTool.kind);
	}
</script>

<svelte:window onkeydown={onKey} />

{#if connector}
	<ButtonGroup
		bind:ref={root}
		class={cn(compact ? 'h-7' : 'h-8', className)}
		onpointerenter={freshen}
	>
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						{variant}
						size="sm"
						class="{main} {tone}"
						aria-label={note ? `${action}. ${note}` : action}
						aria-busy={phase === 'sending'}
						onclick={() => send(proxyTool.kind)}
					>
						{#if phase === 'sending'}
							<Spinner class={icon} />
							{tool}
						{:else if phase === 'delivered'}
							<Check class={icon} />
							{tool}
						{:else if phase === 'queued'}
							<Clock class={icon} />
							Queued
						{:else}
							<Send class={icon} />
							{tool}
						{/if}
					</Button>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content class="flex flex-col gap-1">
				<span class="flex items-center gap-1.5">
					{action}
					{#if shortcut}<Kbd>{shortcut}</Kbd>{/if}
				</span>
				{#if note}<span class="opacity-70">{note}</span>{/if}
			</Tooltip.Content>
		</Tooltip.Root>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						{variant}
						size="sm"
						class={narrow}
						disabled={phase === 'sending'}
						aria-label="Choose the {proxy} tool"
					>
						<ChevronDown class={icon} />
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
				<DropdownMenu.Separator />
				<DropdownMenu.CheckboxItem
					checked={proxyTool.ask}
					onCheckedChange={(v) => proxyTool.setAsk(v)}
				>
					Confirm before sending
				</DropdownMenu.CheckboxItem>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</ButtonGroup>
{:else if variant !== 'ghost' && known && auth.user?.is_superuser}
	<Button
		variant="outline"
		size="sm"
		class={cn('h-7 gap-1.5 px-2.5 text-xs font-medium has-[>svg]:px-2.5', className)}
		href={ROUTES.connectors()}
	>
		<Plug class="size-3" />
		Connect Burp Suite
	</Button>
{/if}
