<script lang="ts">
	import type { SignalFilter, TargetSummary } from '$lib/utilities/target-signals';
	import { Boxes, CalendarClock, TriangleAlert, Loader, ShieldCheck } from 'lucide-svelte';

	interface Props {
		summary: TargetSummary;
		activeSignal: SignalFilter | null;
		onSelect: (signal: SignalFilter | null) => void;
	}

	let { summary, activeSignal, onSelect }: Props = $props();

	interface Tile {
		signal: SignalFilter | null;
		label: string;
		value: number;
		icon: typeof Boxes;
		accent: string;
		activeRing: string;
	}

	let tiles = $derived<Tile[]>([
		{
			signal: null,
			label: 'Total',
			value: summary.total,
			icon: Boxes,
			accent: 'text-foreground',
			activeRing: 'ring-primary/40 border-primary/40 bg-primary/5'
		},
		{
			signal: 'expiring',
			label: 'Expiring',
			value: summary.expiring,
			icon: CalendarClock,
			accent: 'text-amber-500',
			activeRing: 'ring-amber-500/40 border-amber-500/40 bg-amber-500/5'
		},
		{
			signal: 'attention',
			label: 'Needs attention',
			value: summary.attention,
			icon: TriangleAlert,
			accent: 'text-red-500',
			activeRing: 'ring-red-500/40 border-red-500/40 bg-red-500/5'
		},
		{
			signal: 'awaiting',
			label: 'Enriching',
			value: summary.awaiting,
			icon: Loader,
			accent: 'text-sky-500',
			activeRing: 'ring-sky-500/40 border-sky-500/40 bg-sky-500/5'
		},
		{
			signal: 'enriched',
			label: 'Enriched',
			value: summary.enriched,
			icon: ShieldCheck,
			accent: 'text-emerald-500',
			activeRing: 'ring-emerald-500/40 border-emerald-500/40 bg-emerald-500/5'
		}
	]);

	function isActive(tile: Tile): boolean {
		return tile.signal === null ? activeSignal === null : activeSignal === tile.signal;
	}
</script>

<div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
	{#each tiles as tile (tile.label)}
		<button
			type="button"
			onclick={() => onSelect(tile.signal)}
			aria-pressed={isActive(tile)}
			class="flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5 text-left transition-all hover:bg-muted/40 {isActive(
				tile
			)
				? `ring-1 ${tile.activeRing}`
				: 'border-border/60'}"
		>
			<tile.icon class="h-4 w-4 shrink-0 {tile.accent}" />
			<div class="min-w-0">
				<div class="text-lg font-semibold leading-none tabular-nums">{tile.value}</div>
				<div class="mt-1 truncate text-[11px] text-muted-foreground">{tile.label}</div>
			</div>
		</button>
	{/each}
</div>
