<script lang="ts">
	import type { SignalFilter, TargetSummary } from '$lib/utilities/target-signals';
	import type { IconComponent } from '$lib/config/icons';
	import Boxes from '@lucide/svelte/icons/boxes';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Loader from '@lucide/svelte/icons/loader';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';

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
		icon: IconComponent;
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
			accent: 'text-warning',
			activeRing: 'ring-warning/40 border-warning/40 bg-warning/10'
		},
		{
			signal: 'attention',
			label: 'Needs attention',
			value: summary.attention,
			icon: TriangleAlert,
			accent: 'text-destructive',
			activeRing: 'ring-destructive/40 border-destructive/40 bg-destructive/10'
		},
		{
			signal: 'awaiting',
			label: 'Enriching',
			value: summary.awaiting,
			icon: Loader,
			accent: 'text-chart-1',
			activeRing: 'ring-chart-1/40 border-chart-1/40 bg-chart-1/10'
		},
		{
			signal: 'enriched',
			label: 'Enriched',
			value: summary.enriched,
			icon: ShieldCheck,
			accent: 'text-foreground',
			activeRing: 'ring-primary/40 border-primary/40 bg-primary/5'
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
