<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import { mode } from 'mode-watcher';
	import { KIND_ICONS, kindColor } from '$lib/config/correlation';
	import { STATUS_CLASS_FILL, statusClassOf } from '$lib/config/endpoints';
	import type {
		CorrelationHost,
		CorrelationHub,
		CorrelationKindStat
	} from '$lib/types/correlation';
	import type { GraphNode } from './correlation-graph.svelte';

	interface Props {
		selected: GraphNode | null;
		hubs: CorrelationHub[];
		hosts: CorrelationHost[];
		kinds: CorrelationKindStat[];
		onPickHub: (hub: CorrelationHub) => void;
		onPickHost: (index: number) => void;
		onOpenHub: (hub: CorrelationHub) => void;
		onOpenHost: (host: CorrelationHost) => void;
		onClear: () => void;
	}

	let {
		selected,
		hubs,
		hosts,
		kinds,
		onPickHub,
		onPickHost,
		onOpenHub,
		onOpenHost,
		onClear
	}: Props = $props();

	const TOP = 14;
	const MEMBERS = 60;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
	let labelFor = $derived((kind: string) => kinds.find((k) => k.key === kind)?.label ?? kind);
	let top = $derived([...hubs].sort((a, b) => b.count - a.count).slice(0, TOP));
	let hostHubs = $derived(
		selected?.kind === 'host' && selected.hostIndex !== undefined
			? hubs
					.filter((h) => h.members.includes(selected.hostIndex!))
					.sort((a, b) => b.count - a.count)
			: []
	);
	let dot = $derived((kind: string) => `background:${kindColor(kind, mode.current === 'dark')}`);
</script>

<div class="flex h-full min-h-0 flex-col">
	{#if selected?.kind === 'hub' && selected.hub}
		{@const hub = selected.hub}
		{@const Icon = KIND_ICONS[hub.kind]}
		<div class="flex items-start gap-2 border-b px-4 py-3">
			<span class="mt-0.5 size-2.5 shrink-0 rounded-full" style={dot(hub.kind)}></span>
			<div class="min-w-0 flex-1">
				<p
					class="flex items-center gap-1.5 text-2xs font-medium tracking-wider text-muted-foreground uppercase"
				>
					{#if Icon}<Icon class="size-3" />{/if}
					{labelFor(hub.kind)}
				</p>
				<p class="mt-0.5 font-mono text-xs break-all">{hub.value}</p>
				<p class="mt-1 text-xs text-muted-foreground">
					{plural(hub.count, 'web asset', 'web assets')} · {Math.round(hub.share * 100)}% of the
					scan{hub.common ? ' · common' : ''}
				</p>
			</div>
			<Button
				variant="ghost"
				size="icon"
				class="size-6 shrink-0"
				aria-label="Clear selection"
				onclick={onClear}
			>
				<X class="size-3.5" />
			</Button>
		</div>
		<div class="border-b px-4 py-2">
			<Button
				variant="outline"
				size="sm"
				class="h-7 w-full gap-1.5 text-xs"
				onclick={() => onOpenHub(hub)}
			>
				Open {hub.count.toLocaleString()} in Web assets <ArrowUpRight class="size-3" />
			</Button>
		</div>
		<ScrollArea class="min-h-0 flex-1">
			<ul class="divide-y divide-border/60">
				{#each hub.members.slice(0, MEMBERS) as index (index)}
					{@const host = hosts[index]}
					{#if host}
						<li>
							<button
								type="button"
								class="flex w-full items-center gap-2 px-4 py-1.5 text-left hover:bg-muted/40"
								onclick={() => onPickHost(index)}
							>
								<span
									class="size-1.5 shrink-0 rounded-full"
									style="background:{STATUS_CLASS_FILL[statusClassOf(host.status)]}"
								></span>
								<span class="min-w-0 flex-1 truncate font-mono text-xs">{host.name}</span>
								{#if host.status !== null}
									<span class="font-mono text-2xs text-muted-foreground tabular-nums"
										>{host.status}</span
									>
								{/if}
							</button>
						</li>
					{/if}
				{/each}
			</ul>
			{#if hub.members.length > MEMBERS}
				<p class="px-4 py-2 text-2xs text-muted-foreground">
					{hub.members.length - MEMBERS} more in Web assets
				</p>
			{/if}
		</ScrollArea>
	{:else if selected?.kind === 'host' && selected.host}
		{@const host = selected.host}
		<div class="flex items-start gap-2 border-b px-4 py-3">
			<span
				class="mt-1.5 size-2 shrink-0 rounded-full"
				style="background:{STATUS_CLASS_FILL[statusClassOf(host.status)]}"
			></span>
			<div class="min-w-0 flex-1">
				<p class="font-mono text-xs font-medium break-all">{host.name}</p>
				<p class="mt-0.5 truncate text-xs text-muted-foreground">
					{host.status !== null ? `HTTP ${host.status}` : 'No HTTP response'}{host.title
						? ` · ${host.title}`
						: ''}
				</p>
			</div>
			<Button
				variant="ghost"
				size="icon"
				class="size-6 shrink-0"
				aria-label="Clear selection"
				onclick={onClear}
			>
				<X class="size-3.5" />
			</Button>
		</div>
		<div class="border-b px-4 py-2">
			<Button
				variant="outline"
				size="sm"
				class="h-7 w-full gap-1.5 text-xs"
				onclick={() => onOpenHost(host)}
			>
				Open in Web assets <ArrowUpRight class="size-3" />
			</Button>
		</div>
		<p class="px-4 pt-3 pb-1 text-2xs font-medium tracking-wider text-muted-foreground uppercase">
			Shared identities
		</p>
		<ScrollArea class="min-h-0 flex-1">
			<ul class="divide-y divide-border/60">
				{#each hostHubs as hub (hub.id)}
					<li>
						<button
							type="button"
							class="flex w-full items-center gap-2 px-4 py-1.5 text-left hover:bg-muted/40"
							onclick={() => onPickHub(hub)}
						>
							<span class="size-2 shrink-0 rounded-full" style={dot(hub.kind)}></span>
							<span class="flex min-w-0 flex-1 flex-col">
								<span class="truncate font-mono text-xs">{hub.label}</span>
								<span class="text-2xs text-muted-foreground">{labelFor(hub.kind)}</span>
							</span>
							<span class="text-xs tabular-nums text-muted-foreground">{hub.count}</span>
						</button>
					</li>
				{/each}
			</ul>
		</ScrollArea>
	{:else}
		<p class="px-4 pt-3 pb-1 text-2xs font-medium tracking-wider text-muted-foreground uppercase">
			Largest clusters
		</p>
		<ScrollArea class="min-h-0 flex-1">
			<ul class="divide-y divide-border/60">
				{#each top as hub (hub.id)}
					{@const Icon = KIND_ICONS[hub.kind]}
					<li>
						<Hint text={hub.value}>
							{#snippet child(props)}
								<button
									{...props}
									type="button"
									class="flex w-full items-center gap-2 px-4 py-1.5 text-left hover:bg-muted/40"
									onclick={() => onPickHub(hub)}
								>
									<span class="size-2 shrink-0 rounded-full" style={dot(hub.kind)}></span>
									<span class="flex min-w-0 flex-1 flex-col">
										<span class="truncate font-mono text-xs">{hub.label}</span>
										<span class="flex items-center gap-1 text-2xs text-muted-foreground">
											{#if Icon}<Icon class="size-3" />{/if}
											{labelFor(hub.kind)}{hub.common ? ' · common' : ''}
										</span>
									</span>
									<span class="text-xs font-medium tabular-nums">{hub.count}</span>
								</button>
							{/snippet}
						</Hint>
					</li>
				{/each}
			</ul>
		</ScrollArea>
	{/if}
</div>
