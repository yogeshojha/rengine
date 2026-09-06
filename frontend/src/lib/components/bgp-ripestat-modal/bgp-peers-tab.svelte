<script lang="ts">
	import { type ASNNeighbourRead, PEER_RELATIONSHIP_LABELS } from '$lib/types/ripestat';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Empty from '$lib/components/ui/empty';
	import { Badge } from '$lib/components/ui/badge';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';
	import Info from '@lucide/svelte/icons/info';
	import CirclePlus from '@lucide/svelte/icons/circle-plus';
	import Zap from '@lucide/svelte/icons/zap';
	import { Spinner } from '$lib/components/ui/spinner';
	import type { IconComponent } from '$lib/config/icons';

	interface Props {
		neighbours: ASNNeighbourRead[];
		isLoading: boolean;
		error: string | null;
		onAddAsTarget?: (value: string) => void;
	}

	let { neighbours, isLoading, error, onAddAsTarget }: Props = $props();

	const MAX_DISPLAY = 50;

	let upstreamCount = $derived(neighbours.filter((n) => n.relationship === 'upstream').length);
	let downstreamCount = $derived(neighbours.filter((n) => n.relationship === 'downstream').length);
	let uncertainCount = $derived(neighbours.filter((n) => n.relationship === 'uncertain').length);

	let sortedNeighbours = $derived([...neighbours].sort((a, b) => b.power - a.power));
	let displayNeighbours = $derived(sortedNeighbours.slice(0, MAX_DISPLAY));
	let hasMore = $derived(neighbours.length > MAX_DISPLAY);

	let maxPower = $derived(displayNeighbours.length > 0 ? displayNeighbours[0].power : 1);

	const RELATIONSHIP_META: Record<
		string,
		{
			label: string;
			icon: IconComponent;
			badge: string;
			bar: string;
		}
	> = {
		upstream: {
			label: PEER_RELATIONSHIP_LABELS.upstream,
			icon: ArrowUpRight,
			badge: 'text-muted-foreground border-border/60',
			bar: 'bg-foreground'
		},
		downstream: {
			label: PEER_RELATIONSHIP_LABELS.downstream,
			icon: ArrowDownRight,
			badge: 'text-muted-foreground border-border/60',
			bar: 'bg-muted-foreground'
		},
		uncertain: {
			label: PEER_RELATIONSHIP_LABELS.uncertain,
			icon: Info,
			badge: 'text-muted-foreground border-border/60',
			bar: 'bg-muted-foreground/50'
		}
	};

	function getMeta(rel: string) {
		return (
			RELATIONSHIP_META[rel] ?? {
				label: rel,
				icon: Info,
				badge: 'text-muted-foreground border-border/60',
				bar: 'bg-muted-foreground/40'
			}
		);
	}

	function handleAddAsTarget(asn: number) {
		onAddAsTarget?.(`AS${asn}`);
	}
</script>

{#if isLoading}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<Spinner />
			</Empty.Media>
			<Empty.Title>Loading BGP peers…</Empty.Title>
		</Empty.Header>
	</Empty.Root>
{:else if error}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<SearchX />
			</Empty.Media>
			<Empty.Title>Peers could not be loaded</Empty.Title>
			<Empty.Description>{error}</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else if neighbours.length === 0}
	<Empty.Root>
		<Empty.Header>
			<Empty.Media variant="icon">
				<Waypoints />
			</Empty.Media>
			<Empty.Title>No BGP peers found</Empty.Title>
			<Empty.Description>
				No neighbour ASNs were found for this autonomous system.
			</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else}
	<div class="space-y-4 py-1">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2 text-sm text-muted-foreground">
				<Waypoints class="h-4 w-4" />
				<span>
					<span class="font-medium text-foreground">{neighbours.length.toLocaleString()}</span>
					total {neighbours.length === 1 ? 'peer' : 'peers'}
				</span>
			</div>
		</div>

		<div class="flex items-center gap-3 flex-wrap">
			{#if upstreamCount > 0}
				<div class="flex items-center gap-1.5 text-xs">
					<ArrowUpRight class="h-3 w-3 text-muted-foreground" />
					<span class="text-muted-foreground">
						<span class="font-medium text-foreground">
							{upstreamCount.toLocaleString()}
						</span>
						upstream
					</span>
				</div>
			{/if}
			{#if downstreamCount > 0}
				<div class="flex items-center gap-1.5 text-xs">
					<ArrowDownRight class="h-3 w-3 text-muted-foreground" />
					<span class="text-muted-foreground">
						<span class="font-medium text-foreground">
							{downstreamCount.toLocaleString()}
						</span>
						downstream
					</span>
				</div>
			{/if}
			{#if uncertainCount > 0}
				<div class="flex items-center gap-1.5 text-xs">
					<Info class="h-3 w-3 text-muted-foreground" />
					<span class="text-muted-foreground">
						<span class="font-medium text-foreground">
							{uncertainCount.toLocaleString()}
						</span>
						uncertain
					</span>
				</div>
			{/if}
		</div>

		{#if neighbours.length > 0}
			<div class="h-2 rounded-full overflow-hidden flex bg-muted">
				{#if upstreamCount > 0}
					<div
						class="bg-foreground transition-all"
						style="width: {(upstreamCount / neighbours.length) * 100}%"
					></div>
				{/if}
				{#if downstreamCount > 0}
					<div
						class="bg-muted-foreground transition-all"
						style="width: {(downstreamCount / neighbours.length) * 100}%"
					></div>
				{/if}
				{#if uncertainCount > 0}
					<div
						class="bg-muted-foreground/50 transition-all"
						style="width: {(uncertainCount / neighbours.length) * 100}%"
					></div>
				{/if}
			</div>
		{/if}

		<div
			class="flex items-center justify-between px-3 text-[11px] text-muted-foreground uppercase tracking-wider"
		>
			<span>Top peers by BGP power</span>
			<Zap class="h-3 w-3" />
		</div>

		<div class="space-y-1">
			{#each displayNeighbours as neighbour (neighbour.neighbour_asn)}
				{@const meta = getMeta(neighbour.relationship)}
				{@const RelIcon = meta.icon}
				{@const powerPct = maxPower > 0 ? (neighbour.power / maxPower) * 100 : 0}
				<div
					class="flex items-center gap-3 px-3 py-2 rounded-lg border border-border/50 hover:border-border/80 transition-colors group/row relative overflow-hidden"
				>
					<div
						class="absolute inset-y-0 left-0 {meta.bar} opacity-[0.07] transition-all"
						style="width: {powerPct}%"
					></div>

					<div class="flex items-center gap-3 min-w-0 flex-1 relative z-10">
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<button
										{...props}
										class="font-mono text-sm font-medium hover:text-primary transition-colors cursor-pointer inline-flex items-center gap-1 group/asn"
										onclick={() => handleAddAsTarget(neighbour.neighbour_asn)}
									>
										AS{neighbour.neighbour_asn}
										<CirclePlus
											class="h-3 w-3 opacity-0 group-hover/asn:opacity-60 transition-opacity"
										/>
									</button>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content>
								<p>Add AS{neighbour.neighbour_asn} as target</p>
							</Tooltip.Content>
						</Tooltip.Root>

						<Badge variant="outline" class="text-[10px] font-normal gap-1 shrink-0 {meta.badge}">
							<RelIcon class="h-3 w-3" />
							{meta.label}
						</Badge>
					</div>

					<div class="flex items-center gap-1.5 shrink-0 relative z-10">
						<Zap class="h-3 w-3 text-muted-foreground/50" />
						<span class="text-xs font-mono text-muted-foreground">{neighbour.power}</span>
					</div>
				</div>
			{/each}
		</div>

		{#if hasMore}
			<p class="text-xs text-muted-foreground text-center pt-1">
				Showing {MAX_DISPLAY} of {neighbours.length.toLocaleString()} peers
			</p>
		{/if}
	</div>
{/if}
