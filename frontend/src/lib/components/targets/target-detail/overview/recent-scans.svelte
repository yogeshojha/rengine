<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import {
		Scan,
		ShieldAlert,
		Network,
		Clock,
		Radar,
		Zap,
		Search,
		Check,
		X,
		Ban,
		Loader2,
		ChevronRight,
		TrendingUp,
		TrendingDown
	} from 'lucide-svelte';

	interface Props {
		target: Target;
	}

	let { target }: Props = $props();

	type ScanType = 'full' | 'quick' | 'vuln' | 'port' | 'dns';
	type ScanStatus = 'completed' | 'failed' | 'aborted' | 'running';

	const scanTypeConfig: Record<
		ScanType,
		{ label: string; icon: typeof Scan; bg: string; text: string; ringColor: string }
	> = {
		full: {
			label: 'Full Scan',
			icon: Radar,
			bg: 'bg-blue-500/10',
			text: 'text-blue-400',
			ringColor: 'ring-blue-500/20'
		},
		quick: {
			label: 'Quick Scan',
			icon: Zap,
			bg: 'bg-emerald-500/10',
			text: 'text-emerald-400',
			ringColor: 'ring-emerald-500/20'
		},
		vuln: {
			label: 'Vuln Scan',
			icon: ShieldAlert,
			bg: 'bg-red-500/10',
			text: 'text-red-400',
			ringColor: 'ring-red-500/20'
		},
		port: {
			label: 'Port Scan',
			icon: Network,
			bg: 'bg-amber-500/10',
			text: 'text-amber-400',
			ringColor: 'ring-amber-500/20'
		},
		dns: {
			label: 'DNS Scan',
			icon: Search,
			bg: 'bg-purple-500/10',
			text: 'text-purple-400',
			ringColor: 'ring-purple-500/20'
		}
	};

	const statusConfig: Record<
		ScanStatus,
		{
			label: string;
			icon: typeof Check;
			bg: string;
			text: string;
			ring: string;
			dotColor: string;
		}
	> = {
		completed: {
			label: 'Completed',
			icon: Check,
			bg: 'bg-emerald-500/10',
			text: 'text-emerald-400',
			ring: 'ring-emerald-500/25',
			dotColor: 'bg-emerald-500'
		},
		failed: {
			label: 'Failed',
			icon: X,
			bg: 'bg-red-500/10',
			text: 'text-red-400',
			ring: 'ring-red-500/25',
			dotColor: 'bg-red-500'
		},
		aborted: {
			label: 'Aborted',
			icon: Ban,
			bg: 'bg-amber-500/10',
			text: 'text-amber-400',
			ring: 'ring-amber-500/25',
			dotColor: 'bg-amber-500'
		},
		running: {
			label: 'Running',
			icon: Loader2,
			bg: 'bg-blue-500/10',
			text: 'text-blue-400',
			ring: 'ring-blue-500/25',
			dotColor: 'bg-blue-500'
		}
	};

	interface RecentScan {
		id: string;
		type: ScanType;
		status: ScanStatus;
		date: Date;
		duration: string;
		deltas: { label: string; value: number }[];
	}

	function getRecentScans(type: TargetType): RecentScan[] {
		const now = new Date();
		const scanTypes: ScanType[] = ['full', 'quick', 'vuln', 'full', 'port', 'dns', 'quick', 'full'];
		const statuses: ScanStatus[] = [
			'running',
			'completed',
			'completed',
			'failed',
			'completed',
			'completed',
			'aborted',
			'completed'
		];

		const domainDeltas = [
			[
				{ label: 'subs', value: 12 },
				{ label: 'vulns', value: 3 }
			],
			[
				{ label: 'subs', value: 0 },
				{ label: 'vulns', value: -2 }
			],
			[
				{ label: 'subs', value: 0 },
				{ label: 'vulns', value: 5 }
			],
			[
				{ label: 'subs', value: 8 },
				{ label: 'vulns', value: 1 }
			],
			[
				{ label: 'ports', value: -4 },
				{ label: 'vulns', value: 0 }
			],
			[
				{ label: 'subs', value: 1 },
				{ label: 'vulns', value: 0 }
			],
			[
				{ label: 'subs', value: 3 },
				{ label: 'vulns', value: -1 }
			],
			[
				{ label: 'subs', value: 15 },
				{ label: 'vulns', value: 2 }
			]
		];

		const ipDeltas = [
			[
				{ label: 'ports', value: 2 },
				{ label: 'vulns', value: 1 }
			],
			[
				{ label: 'ports', value: 0 },
				{ label: 'vulns', value: -1 }
			],
			[
				{ label: 'ports', value: 0 },
				{ label: 'vulns', value: 3 }
			],
			[
				{ label: 'ports', value: -1 },
				{ label: 'vulns', value: 0 }
			],
			[
				{ label: 'ports', value: 1 },
				{ label: 'vulns', value: 2 }
			],
			[
				{ label: 'ports', value: 0 },
				{ label: 'vulns', value: 0 }
			],
			[
				{ label: 'ports', value: -2 },
				{ label: 'vulns', value: -1 }
			],
			[
				{ label: 'ports', value: 3 },
				{ label: 'vulns', value: 1 }
			]
		];

		const durations = ['—', '48s', '1m 12s', '3m 12s', '1m 55s', '32s', '52s', '4m 08s'];
		const dayOffsets = [0, 1, 3, 5, 9, 12, 16, 22];

		const deltas = [TargetType.IP, TargetType.IP_RANGE, TargetType.ASN].includes(type)
			? ipDeltas
			: domainDeltas;

		return dayOffsets.map((offset, i) => {
			const date = new Date(now);
			date.setDate(date.getDate() - offset);
			return {
				id: `scan-${i}`,
				type: scanTypes[i],
				status: statuses[i],
				date,
				duration: durations[i],
				deltas: statuses[i] === 'completed' ? deltas[i] : []
			};
		});
	}

	function formatScanDate(date: Date): string {
		const now = new Date();
		const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
		if (diffDays === 0) return 'Today';
		if (diffDays === 1) return 'Yesterday';
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	const recentScans = $derived(getRecentScans(target.target_type));
	const runningCount = $derived(recentScans.filter((s) => s.status === 'running').length);
</script>

<Card.Root
	class="overflow-hidden h-full flex flex-col border-border/50 bg-card/80 backdrop-blur-sm"
>
	<!-- Header -->
	<Card.Header class="space-y-0 border-b border-border/50 py-3 px-4 shrink-0">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<Card.Title class="text-sm font-semibold tracking-tight">Recent Scans</Card.Title>
				{#if runningCount > 0}
					<span
						class="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-1.5 py-0.5 ring-1 ring-blue-500/20"
					>
						<span class="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse"></span>
						<span class="text-[10px] font-semibold text-blue-400">{runningCount} active</span>
					</span>
				{/if}
			</div>
			<span class="text-[10px] text-muted-foreground/50 tabular-nums"
				>{recentScans.length} scans</span
			>
		</div>
	</Card.Header>

	<ScrollArea class="flex-1 min-h-0">
		<div class="p-1.5 space-y-0.5">
			{#each recentScans as scan, i}
				{@const typeConf = scanTypeConfig[scan.type]}
				{@const statConf = statusConfig[scan.status]}
				{@const ScanIcon = typeConf.icon}
				{@const StatusIcon = statConf.icon}
				{@const isRunning = scan.status === 'running'}

				<div
					class="group relative rounded-lg px-2.5 py-2.5 transition-all duration-200 hover:bg-muted/40 cursor-pointer {isRunning
						? 'bg-muted/20'
						: ''}"
					style="animation: scanSlideIn 0.3s ease-out {i * 0.04}s both;"
				>
					<!-- Running scan left accent -->
					{#if isRunning}
						<div
							class="absolute left-0 top-2 bottom-2 w-[2px] rounded-full bg-blue-500/60 animate-pulse"
						></div>
					{/if}

					<div class="flex items-start gap-2.5">
						<!-- Scan type icon -->
						<div class="relative shrink-0 mt-0.5">
							<div
								class="flex h-8 w-8 items-center justify-center rounded-lg {typeConf.bg} ring-1 {typeConf.ringColor} transition-all duration-200 group-hover:scale-105"
							>
								<ScanIcon class="h-3.5 w-3.5 {typeConf.text}" strokeWidth={2} />
							</div>
						</div>

						<!-- Content area -->
						<div class="flex-1 min-w-0 space-y-1.5">
							<!-- Top row: scan name + status badge -->
							<div class="flex items-center justify-between gap-2">
								<span
									class="text-[12px] font-medium text-foreground/90 group-hover:text-foreground transition-colors"
								>
									{typeConf.label}
								</span>

								<!-- Status Badge -->
								<span
									class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 {statConf.bg} ring-1 {statConf.ring} transition-all duration-200"
								>
									{#if isRunning}
										<StatusIcon class="h-2.5 w-2.5 {statConf.text}" />
									{:else}
										<StatusIcon class="h-2.5 w-2.5 {statConf.text}" strokeWidth={2.5} />
									{/if}
									<span class="text-[9px] font-semibold uppercase tracking-wider {statConf.text}">
										{statConf.label}
									</span>
								</span>
							</div>

							<!-- Bottom row: metadata -->
							<div class="flex items-center gap-2 flex-wrap">
								<!-- Duration -->
								{#if !isRunning}
									<span
										class="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground/50"
									>
										<Clock class="h-2.5 w-2.5" />
										{scan.duration}
									</span>
								{:else}
									<span class="inline-flex items-center gap-0.5 text-[10px] text-blue-400/60">
										<Clock class="h-2.5 w-2.5" />
										<span class="tabular-nums">running…</span>
									</span>
								{/if}

								<!-- Date -->
								<span class="text-[10px] text-muted-foreground/40 tabular-nums">
									{formatScanDate(scan.date)}
								</span>

								<!-- Spacer -->
								<span class="flex-1"></span>

								<!-- Delta chips -->
								{#each scan.deltas as delta}
									{#if delta.value !== 0}
										{@const isNegativeVuln = delta.value < 0 && delta.label === 'vulns'}
										{@const isPositiveVuln = delta.value > 0 && delta.label === 'vulns'}
										{@const chipColor = isPositiveVuln
											? 'text-red-400 bg-red-500/8'
											: isNegativeVuln
												? 'text-emerald-400 bg-emerald-500/8'
												: delta.value > 0
													? 'text-sky-400 bg-sky-500/8'
													: 'text-muted-foreground bg-muted/50'}

										<span
											class="inline-flex items-center gap-0.5 rounded px-1 py-px text-[10px] tabular-nums font-medium {chipColor}"
										>
											{#if isPositiveVuln || (delta.value > 0 && delta.label !== 'vulns')}
												<TrendingUp class="h-2 w-2" />
											{:else}
												<TrendingDown class="h-2 w-2" />
											{/if}
											{delta.value > 0 ? '+' : ''}{delta.value}
											<span class="text-[9px] opacity-60">{delta.label}</span>
										</span>
									{/if}
								{/each}
							</div>
						</div>

						<!-- Chevron hint on hover -->
						<ChevronRight
							class="h-3.5 w-3.5 text-muted-foreground/0 group-hover:text-muted-foreground/40 transition-all duration-200 shrink-0 mt-1"
						/>
					</div>
				</div>
			{/each}
		</div>
	</ScrollArea>

	<!-- Bottom edge line -->
	<div class="shrink-0 h-px bg-gradient-to-r from-transparent via-border/50 to-transparent"></div>
</Card.Root>

<style>
	@keyframes scanSlideIn {
		from {
			opacity: 0;
			transform: translateY(4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
