<script lang="ts">
	import { TargetType, type BgpSummaryData } from '$lib/types/target';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import {
		Loader,
		TriangleAlert,
		Radio,
		RadioTower,
		Clock,
		Network,
		Server,
		Users,
		CircleDot,
		CircleCheck,
		CircleX,
		ExternalLink
	} from 'lucide-svelte';

	interface Props {
		status: string;
		bgp: BgpSummaryData | null;
		targetType: TargetType;
		targetValue: string;
		onClick?: () => void;
	}

	let { status, bgp, targetType, targetValue, onClick }: Props = $props();

	let isApplicable = $derived(
		targetType === TargetType.ASN ||
		targetType === TargetType.IP ||
		targetType === TargetType.IP_RANGE
	);

	let inlineSummary = $derived.by(() => {
		if (!bgp) return '';

		switch (targetType) {
			case TargetType.ASN: {
				if (bgp.announced === false) return 'Not announced';
				const parts: string[] = [];
				if (bgp.prefix_count != null) {
					parts.push(`${bgp.prefix_count} ${bgp.prefix_count === 1 ? 'prefix' : 'prefixes'}`);
				}
				if (bgp.peer_count != null) {
					parts.push(`${bgp.peer_count} ${bgp.peer_count === 1 ? 'peer' : 'peers'}`);
				}
				return parts.join(' · ') || 'Announced';
			}
			case TargetType.IP:
			case TargetType.IP_RANGE: {
				const parts: string[] = [];
				if (bgp.asn != null) parts.push(`AS${bgp.asn}`);
				if (bgp.holder) parts.push(truncate(bgp.holder, 20));
				return parts.join('  ·  ');
			}
			default:
				return '';
		}
	});

	let isNotAnnounced = $derived(
		targetType === TargetType.ASN && bgp?.announced === false
	);

	function formatNumber(n: number | null | undefined): string {
		if (n == null) return '—';
		return n.toLocaleString();
	}

	function truncate(str: string, max: number): string {
		if (str.length <= max) return str;
		return str.slice(0, max - 1) + '…';
	}

	function formatQueriedAt(dateStr: string | null | undefined): string {
		if (!dateStr) return 'Unknown';
		const d = new Date(dateStr);
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		onClick?.();
	}
</script>

{#if !isApplicable}
	<!-- DOMAIN/URL — no BGP data -->
{:else if status === 'pending' || status === 'enriching'}
	<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
		<Loader class="h-3 w-3 animate-spin" />
		<span class="animate-pulse">BGP…</span>
	</div>
{:else if status === 'failed'}
	<div class="flex items-center gap-1.5 text-xs text-red-500/70 dark:text-red-400/70">
		<TriangleAlert class="h-3 w-3" />
		<span>BGP failed</span>
	</div>
{:else if status === 'success' && bgp && inlineSummary}
	<HoverCard.Root openDelay={250} closeDelay={100}>
		<HoverCard.Trigger>
			<button
				type="button"
				class="flex items-center gap-1.5 text-xs transition-colors cursor-pointer max-w-full
					{isNotAnnounced
						? 'text-amber-600 dark:text-amber-400'
						: 'text-muted-foreground hover:text-foreground'}"
				onclick={handleClick}
			>
				{#if targetType === TargetType.ASN}
					<RadioTower class="h-3 w-3 shrink-0" />
				{:else}
					<Radio class="h-3 w-3 shrink-0" />
				{/if}
				<span class="truncate font-mono">{inlineSummary}</span>
				{#if isNotAnnounced}
					<span class="inline-block h-1.5 w-1.5 rounded-full shrink-0 bg-amber-500"></span>
				{/if}
			</button>
		</HoverCard.Trigger>
		<HoverCard.Content class="w-80 p-0" align="start" side="bottom">

			{#if targetType === TargetType.ASN}
				<!-- ASN hover card -->
				<div class="px-4 pt-3.5 pb-3 border-b border-border/50">
					<div class="flex items-center gap-2">
						<div class="flex items-center justify-center h-8 w-8 rounded-lg bg-orange-500/10">
							<RadioTower class="h-4 w-4 text-orange-500" />
						</div>
						<div class="min-w-0 flex-1">
							<p class="text-sm font-medium font-mono">{targetValue}</p>
							<p class="text-xs text-muted-foreground">BGP Summary</p>
						</div>
					</div>
				</div>

				<div class="px-4 py-3 space-y-3">
					<div class="flex items-start gap-2.5">
						{#if bgp.announced === false}
							<CircleX class="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
						{:else}
							<CircleCheck class="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
						{/if}
						<div>
							<p class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1">Status</p>
							<p class="text-sm font-medium {bgp.announced === false ? 'text-amber-500' : 'text-emerald-500'}">
								{bgp.announced === false ? 'Not Announced' : 'Announced'}
							</p>
						</div>
					</div>

					{#if bgp.announced !== false}
						<div class="flex items-start gap-2.5">
							<Network class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
							<div>
								<p class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1">Announced Prefixes</p>
								<p class="text-sm font-medium font-mono">{formatNumber(bgp.prefix_count)}</p>
							</div>
						</div>

						<div class="flex items-start gap-2.5">
							<Users class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
							<div>
								<p class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1">BGP Peers</p>
								<p class="text-sm font-medium font-mono">{formatNumber(bgp.peer_count)}</p>
							</div>
						</div>
					{/if}
				</div>

			{:else}
				<!-- IP / IP_RANGE hover card -->
				<div class="px-4 pt-3.5 pb-3 border-b border-border/50">
					<div class="flex items-center gap-2">
						<div class="flex items-center justify-center h-8 w-8 rounded-lg bg-cyan-500/10">
							<Radio class="h-4 w-4 text-cyan-500" />
						</div>
						<div class="min-w-0 flex-1">
							<p class="text-sm font-medium font-mono">{targetValue}</p>
							<p class="text-xs text-muted-foreground">BGP Routing Info</p>
						</div>
					</div>
				</div>

				<div class="px-4 py-3 space-y-3">
					{#if bgp.asn != null}
						<div class="flex items-start gap-2.5">
							<Server class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
							<div>
								<p class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1">Announcing ASN</p>
								<p class="text-sm font-medium font-mono">AS{bgp.asn}</p>
							</div>
						</div>
					{/if}

					{#if bgp.holder}
						<div class="flex items-start gap-2.5">
							<CircleDot class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
							<div>
								<p class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1">Holder</p>
								<p class="text-sm">{bgp.holder}</p>
							</div>
						</div>
					{/if}

					{#if bgp.prefix}
						<div class="flex items-start gap-2.5">
							<Network class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
							<div>
								<p class="text-[11px] text-muted-foreground uppercase tracking-wider leading-none mb-1">Containing Prefix</p>
								<p class="text-sm font-mono">{bgp.prefix}</p>
							</div>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Footer -->
			<div class="px-4 py-2.5 border-t border-border/50 bg-muted/30">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
						<Clock class="h-3 w-3" />
						<span>Queried {formatQueriedAt(bgp.queried_at)}</span>
					</div>
					<span class="flex items-center gap-1 text-[11px] text-primary/70">
						Click for details
						<ExternalLink class="h-2.5 w-2.5" />
					</span>
				</div>
			</div>
		</HoverCard.Content>
	</HoverCard.Root>
{/if}
