<script lang="ts">
	import type { Target } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as HoverCard from '$lib/components/ui/hover-card/index.js';
	import { Scan, Globe, ShieldAlert, RefreshCw, Network } from 'lucide-svelte';

	interface Props {
		target: Target;
	}

	let { target }: Props = $props();

	let timeRange = $state('3m');

	// ── Types ──

	interface DayEvent {
		icon: typeof Scan;
		label: string;
		color: string;
	}

	interface DayActivity {
		date: Date;
		count: number;
		formatted: string;
		events: DayEvent[];
	}

	// ── Dummy event generator ──

	function generateEvents(count: number): DayEvent[] {
		if (count === 0) return [];

		const possibleEvents: DayEvent[] = [
			{ icon: Scan, label: 'Scan completed', color: 'text-blue-400' },
			{ icon: Globe, label: 'Subdomains discovered', color: 'text-emerald-400' },
			{ icon: ShieldAlert, label: 'Vulnerability found', color: 'text-red-400' },
			{ icon: RefreshCw, label: 'Enrichment refreshed', color: 'text-muted-foreground' },
			{ icon: Network, label: 'Port change detected', color: 'text-amber-400' }
		];

		const events: DayEvent[] = [];
		const available = [...possibleEvents];

		for (let i = 0; i < Math.min(count, available.length); i++) {
			const idx = Math.floor(Math.random() * available.length);
			events.push(available.splice(idx, 1)[0]);
		}

		return events;
	}

	function generateActivityData(days: number): DayActivity[] {
		const data: DayActivity[] = [];
		const now = new Date();
		now.setHours(0, 0, 0, 0);

		for (let i = days - 1; i >= 0; i--) {
			const date = new Date(now);
			date.setDate(date.getDate() - i);

			const dayOfWeek = date.getDay();
			const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
			const rand = Math.random();

			let count: number;
			if (rand < 0.25) count = 0;
			else if (isWeekend && rand < 0.6) count = 0;
			else if (rand < 0.5) count = Math.floor(Math.random() * 2) + 1;
			else if (rand < 0.8) count = Math.floor(Math.random() * 4) + 3;
			else count = Math.floor(Math.random() * 6) + 7;

			const formatted = date.toLocaleDateString('en-US', {
				weekday: 'short',
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			});

			data.push({ date, count, formatted, events: generateEvents(Math.min(count, 5)) });
		}

		return data;
	}

	const totalDays = $derived.by(() => {
		switch (timeRange) {
			case '1m':
				return 30;
			case '3m':
				return 90;
			case '6m':
				return 180;
			case '1y':
				return 365;
			default:
				return 90;
		}
	});

	const activityData = $derived(generateActivityData(totalDays));

	// ── Organize into week columns ──

	interface GridCell {
		activity: DayActivity | null;
	}

	interface WeekColumn {
		cells: GridCell[];
		monthLabel?: string;
	}

	const weeks = $derived.by((): WeekColumn[] => {
		if (activityData.length === 0) return [];

		const result: WeekColumn[] = [];
		let currentWeek: GridCell[] = Array.from({ length: 7 }, () => ({ activity: null }));
		let lastMonth = -1;

		for (let i = 0; i < activityData.length; i++) {
			const day = activityData[i];
			const dayOfWeek = day.date.getDay();

			if (dayOfWeek === 0 && i > 0) {
				const prevDay = activityData[i - 1];
				const month = prevDay.date.getMonth();
				result.push({
					cells: currentWeek,
					monthLabel:
						month !== lastMonth
							? prevDay.date.toLocaleDateString('en-US', { month: 'short' })
							: undefined
				});
				if (month !== lastMonth) lastMonth = month;
				currentWeek = Array.from({ length: 7 }, () => ({ activity: null }));
			}

			currentWeek[dayOfWeek] = { activity: day };
		}

		if (currentWeek.some((c) => c.activity !== null)) {
			const lastDay = activityData[activityData.length - 1];
			const month = lastDay.date.getMonth();
			result.push({
				cells: currentWeek,
				monthLabel:
					month !== lastMonth
						? lastDay.date.toLocaleDateString('en-US', { month: 'short' })
						: undefined
			});
		}

		return result;
	});

	function getColor(count: number): string {
		if (count === 0) return 'bg-muted/50';
		if (count <= 2) return 'bg-sky-900/70';
		if (count <= 5) return 'bg-sky-700/80';
		if (count <= 8) return 'bg-sky-500/80';
		return 'bg-sky-400';
	}

	const dayLabels = ['', 'Mon', '', 'Wed', '', 'Fri', ''];

	const totalEvents = $derived(activityData.reduce((sum, d) => sum + d.count, 0));
	const activeDays = $derived(activityData.filter((d) => d.count > 0).length);
</script>

<Card.Root class="overflow-hidden">
	<Card.Header class="flex items-center gap-2 space-y-0 border-b py-3 sm:flex-row">
		<div class="grid flex-1 gap-0.5 text-center sm:text-start">
			<Card.Title class="text-sm">Target Activity</Card.Title>
			<Card.Description class="text-xs">
				<span class="tabular-nums">{totalEvents.toLocaleString()}</span> events across
				<span class="tabular-nums">{activeDays}</span> active days
				<span class="text-muted-foreground/60">·</span>
			</Card.Description>
		</div>
		<Tabs.Root bind:value={timeRange}>
			<Tabs.List class="h-8">
				<Tabs.Trigger value="1m" class="text-xs px-2.5 h-7">1M</Tabs.Trigger>
				<Tabs.Trigger value="3m" class="text-xs px-2.5 h-7">3M</Tabs.Trigger>
				<Tabs.Trigger value="6m" class="text-xs px-2.5 h-7">6M</Tabs.Trigger>
				<Tabs.Trigger value="1y" class="text-xs px-2.5 h-7">1Y</Tabs.Trigger>
			</Tabs.List>
		</Tabs.Root>
	</Card.Header>
	<Card.Content class="pt-3 pb-3">
		<div class="flex gap-[3px] w-full">
			<!-- Day labels -->
			<div class="flex flex-col gap-[3px] shrink-0 pt-[18px]">
				{#each dayLabels as label}
					<div class="h-[11px] w-[24px] flex items-center">
						{#if label}
							<span class="text-[10px] text-muted-foreground leading-none">{label}</span>
						{/if}
					</div>
				{/each}
			</div>

			<!-- Week columns — each flex-1 to fill available width -->
			{#each weeks as week}
				<div class="flex flex-col gap-[3px] flex-1 min-w-0">
					<!-- Month label -->
					<div class="h-[15px] flex items-end overflow-visible">
						{#if week.monthLabel}
							<span class="text-[10px] text-muted-foreground leading-none whitespace-nowrap"
								>{week.monthLabel}</span
							>
						{/if}
					</div>

					<!-- Day cells -->
					{#each week.cells as cell}
						{#if cell.activity}
							{#if cell.activity.count > 0}
								<HoverCard.Root>
									<HoverCard.Trigger>
										<div
											class="h-[11px] w-full rounded-[2px] {getColor(
												cell.activity.count
											)} transition-all duration-150 hover:ring-1 hover:ring-foreground/20 cursor-default"
										></div>
									</HoverCard.Trigger>
									<HoverCard.Content class="w-64 p-0" side="top" sideOffset={8}>
										<div class="px-3 py-2 border-b">
											<p class="text-xs font-medium">{cell.activity.formatted}</p>
											<p class="text-[11px] text-muted-foreground">
												{cell.activity.count} event{cell.activity.count !== 1 ? 's' : ''}
											</p>
										</div>
										<div class="px-3 py-2 space-y-1.5">
											{#each cell.activity.events as event}
												{@const EventIcon = event.icon}
												<div class="flex items-center gap-2">
													<EventIcon class="h-3 w-3 {event.color} shrink-0" />
													<span class="text-xs text-muted-foreground">{event.label}</span>
												</div>
											{/each}
										</div>
									</HoverCard.Content>
								</HoverCard.Root>
							{:else}
								<HoverCard.Root>
									<HoverCard.Trigger>
										<div
											class="h-[11px] w-full rounded-[2px] {getColor(
												0
											)} transition-all duration-150 cursor-default"
										></div>
									</HoverCard.Trigger>
									<HoverCard.Content class="w-48 p-0" side="top" sideOffset={8}>
										<div class="px-3 py-2">
											<p class="text-xs font-medium">{cell.activity.formatted}</p>
											<p class="text-[11px] text-muted-foreground">No activity</p>
										</div>
									</HoverCard.Content>
								</HoverCard.Root>
							{/if}
						{:else}
							<div class="h-[11px] w-full"></div>
						{/if}
					{/each}
				</div>
			{/each}
		</div>

		<!-- Legend -->
		<div class="flex items-center justify-end gap-1.5 mt-2.5 text-[10px] text-muted-foreground">
			<span>Less</span>
			<div class="h-[10px] w-[10px] rounded-[2px] bg-muted/50"></div>
			<div class="h-[10px] w-[10px] rounded-[2px] bg-sky-900/70"></div>
			<div class="h-[10px] w-[10px] rounded-[2px] bg-sky-700/80"></div>
			<div class="h-[10px] w-[10px] rounded-[2px] bg-sky-500/80"></div>
			<div class="h-[10px] w-[10px] rounded-[2px] bg-sky-400"></div>
			<span>More</span>
		</div>
	</Card.Content>
</Card.Root>
