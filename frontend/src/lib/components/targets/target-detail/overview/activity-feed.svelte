<script lang="ts">
	import type { Target } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import {
		Scan,
		Globe,
		ShieldAlert,
		RefreshCw,
		Network,
		Radio
	} from 'lucide-svelte';

	interface Props {
		target: Target;
	}

	let { target }: Props = $props();

	type SeverityLevel = 'critical' | 'warning' | 'info' | 'neutral';

	interface FeedEvent {
		id: string;
		icon: typeof Scan;
		severity: SeverityLevel;
		message: string;
		detail?: string;
		timestamp: Date;
	}

	const severityConfig: Record<SeverityLevel, {
		color: string;
		bg: string;
		ring: string;
		glow: string;
		dotColor: string;
		accentBorder: string;
	}> = {
		critical: {
			color: 'text-red-400',
			bg: 'bg-red-500/10',
			ring: 'ring-red-500/25',
			glow: 'shadow-[0_0_12px_rgba(239,68,68,0.15)]',
			dotColor: 'bg-red-400',
			accentBorder: 'border-l-red-500/40'
		},
		warning: {
			color: 'text-amber-400',
			bg: 'bg-amber-500/10',
			ring: 'ring-amber-500/25',
			glow: 'shadow-[0_0_12px_rgba(245,158,11,0.12)]',
			dotColor: 'bg-amber-400',
			accentBorder: 'border-l-amber-500/40'
		},
		info: {
			color: 'text-emerald-400',
			bg: 'bg-emerald-500/10',
			ring: 'ring-emerald-500/25',
			glow: 'shadow-[0_0_12px_rgba(16,185,129,0.12)]',
			dotColor: 'bg-emerald-400',
			accentBorder: 'border-l-emerald-500/40'
		},
		neutral: {
			color: 'text-muted-foreground',
			bg: 'bg-muted/50',
			ring: 'ring-border/50',
			glow: '',
			dotColor: 'bg-muted-foreground/50',
			accentBorder: 'border-l-border'
		}
	};

	function timeAgo(date: Date): string {
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMin = Math.floor(diffMs / 60000);
		const diffHr = Math.floor(diffMin / 60);
		const diffDay = Math.floor(diffHr / 24);

		if (diffMin < 1) return 'just now';
		if (diffMin < 60) return `${diffMin}m ago`;
		if (diffHr < 24) return `${diffHr}h ago`;
		if (diffDay === 1) return 'yesterday';
		return `${diffDay}d ago`;
	}

	function generateFeed(): FeedEvent[] {
		const now = new Date();

		const events: Array<{
			icon: typeof Scan;
			severity: SeverityLevel;
			message: string;
			detail?: string;
			minutesAgo: number;
		}> = [
			{ icon: ShieldAlert, severity: 'critical', message: 'CVE-2024-1234 detected', detail: 'api.example.com:443', minutesAgo: 2 },
			{ icon: Globe, severity: 'info', message: 'New subdomain found', detail: 'staging.example.com', minutesAgo: 14 },
			{ icon: Network, severity: 'warning', message: 'Port 8443 opened', detail: '192.168.1.5', minutesAgo: 67 },
			{ icon: RefreshCw, severity: 'neutral', message: 'WHOIS refreshed', minutesAgo: 180 },
			{ icon: Scan, severity: 'info', message: 'Full scan completed', detail: '247 assets scanned', minutesAgo: 4320 },
			{ icon: ShieldAlert, severity: 'info', message: 'Vuln resolved', detail: 'CVE-2024-0892', minutesAgo: 5760 },
			{ icon: Globe, severity: 'info', message: 'DNS record changed', detail: 'A record updated', minutesAgo: 7200 },
			{ icon: Network, severity: 'warning', message: 'Port 22 closed', detail: '10.0.0.12', minutesAgo: 10080 },
			{ icon: RefreshCw, severity: 'neutral', message: 'BGP refreshed', minutesAgo: 12000 },
			{ icon: Scan, severity: 'info', message: 'Quick scan completed', detail: '12 new assets', minutesAgo: 14400 },
			{ icon: Globe, severity: 'info', message: 'Subdomain found', detail: 'beta.example.com', minutesAgo: 18000 },
			{ icon: ShieldAlert, severity: 'critical', message: 'CVE-2024-5678 detected', detail: 'cdn.example.com', minutesAgo: 20000 }
		];

		return events.map((e, i) => {
			const timestamp = new Date(now);
			timestamp.setMinutes(timestamp.getMinutes() - e.minutesAgo);
			return { ...e, id: `feed-${i}`, timestamp };
		});
	}

	const feedEvents = $derived(generateFeed());
	const criticalCount = $derived(feedEvents.filter(e => e.severity === 'critical').length);
</script>

<Card.Root class="overflow-hidden h-full flex flex-col border-border/50 bg-card/80 backdrop-blur-sm">
	<Card.Header class="space-y-0 border-b border-border/50 py-3 px-4 shrink-0">
		<div class="flex items-center gap-2">
			<Card.Title class="text-sm font-semibold tracking-tight">Activity Feed</Card.Title>
			{#if criticalCount > 0}
				<span class="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-red-400 ring-1 ring-red-500/20">
					{criticalCount}
				</span>
			{/if}
		</div>
	</Card.Header>

	<ScrollArea class="flex-1 min-h-0">
		<div class="p-2">
			{#each feedEvents as event, i}
				{@const config = severityConfig[event.severity]}
				{@const EventIcon = event.icon}
				{@const isRecent = i === 0}

				<div
					class="group relative flex {event.detail ? 'items-start' : 'items-center'} gap-2.5 rounded-lg px-2.5 py-2 transition-all duration-200 hover:bg-muted/40 {isRecent ? 'bg-muted/20' : ''}"
					style="animation: feedSlideIn 0.3s ease-out {i * 0.03}s both;"
				>
					<!-- Accent border for critical items -->
					{#if event.severity === 'critical'}
						<div class="absolute left-0 top-2 bottom-2 w-[2px] rounded-full bg-red-500/60"></div>
					{/if}

					<!-- Icon node -->
					<div class="relative shrink-0 mt-0.5">
						<div class="flex h-7 w-7 items-center justify-center rounded-lg {config.bg} ring-1 {config.ring} {config.glow} transition-all duration-200 group-hover:scale-110">
							<EventIcon class="h-3.5 w-3.5 {config.color}" strokeWidth={2} />
						</div>
						<!-- Pulse for most recent critical -->
						{#if isRecent && event.severity === 'critical'}
							<span class="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
								<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-60"></span>
								<span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500 ring-2 ring-card"></span>
							</span>
						{/if}
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0 {event.detail ? 'space-y-0.5' : 'flex items-center'}">
						<div class="flex items-baseline justify-between gap-2 {event.detail ? '' : 'flex-1'}">
							<p class="text-[11.5px] font-medium leading-snug text-foreground/90 group-hover:text-foreground transition-colors">
								{event.message}
							</p>
							<span class="text-[10px] text-muted-foreground/40 tabular-nums shrink-0 group-hover:text-muted-foreground/60 transition-colors">
								{timeAgo(event.timestamp)}
							</span>
						</div>
						{#if event.detail}
							<p class="text-[10px] text-muted-foreground/60 font-mono truncate group-hover:text-muted-foreground/80 transition-colors">
								{event.detail}
							</p>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</ScrollArea>

	<div class="shrink-0 h-px bg-gradient-to-r from-transparent via-border/50 to-transparent"></div>
</Card.Root>

<style>
	@keyframes feedSlideIn {
		from {
			opacity: 0;
			transform: translateX(-6px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}
</style>
