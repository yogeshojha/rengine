<script lang="ts">
	import { TargetType } from '$lib/types/target';
	import type { DnsSummaryData } from '$lib/types/target';
	import { TaskStatus } from '@/types/task-status';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { goto } from '$app/navigation';
	import {
		Loader,
		TriangleAlert,
		Clock,
		Globe,
		Mail,
		FileText,
		Server,
		Shield,
		Network,
		ExternalLink,
		ShieldCheck,
		Waypoints
	} from 'lucide-svelte';

	interface Props {
		status: string;
		dns: DnsSummaryData | null;
		targetType: TargetType;
		targetValue: string;
		targetId: string;
		onClick?: () => void;
	}

	let { status, dns, targetType, targetValue, targetId, onClick }: Props = $props();

	let isApplicable = $derived(targetType === TargetType.DOMAIN);

	let inlineSummary = $derived.by(() => {
		if (!dns?.record_counts) return '';
		const rc = dns.record_counts;
		const parts: string[] = [];
		if (rc.A) parts.push(`${rc.A} A`);
		if (rc.AAAA) parts.push(`${rc.AAAA} AAAA`);
		if (rc.NS) parts.push(`${rc.NS} NS`);
		if (rc.MX) parts.push(`${rc.MX} MX`);
		return parts.join(' · ');
	});

	let totalRecords = $derived.by(() => {
		if (!dns?.record_counts) return 0;
		return Object.values(dns.record_counts).reduce((sum, n) => sum + n, 0);
	});

	/** CDN provider display info common popular ones, we can fill up after more tests */
	let cdnInfo = $derived.by(() => {
		if (!dns?.cdn || !dns.cdn_name) return null;
		const name = dns.cdn_name.toLowerCase();

		if (name.includes('cloudflare'))
			return {
				label: 'Cloudflare',
				color: 'text-orange-500 dark:text-orange-400',
				bg: 'bg-orange-500/10 border-orange-500/25'
			};
		if (name.includes('akamai'))
			return {
				label: 'Akamai',
				color: 'text-blue-500 dark:text-blue-400',
				bg: 'bg-blue-500/10 border-blue-500/25'
			};
		if (name.includes('fastly'))
			return {
				label: 'Fastly',
				color: 'text-red-500 dark:text-red-400',
				bg: 'bg-red-500/10 border-red-500/25'
			};
		if (name.includes('cloudfront') || name.includes('amazon'))
			return {
				label: 'CloudFront',
				color: 'text-amber-600 dark:text-amber-400',
				bg: 'bg-amber-500/10 border-amber-500/25'
			};
		if (name.includes('google'))
			return {
				label: 'Google CDN',
				color: 'text-blue-500 dark:text-blue-400',
				bg: 'bg-blue-500/10 border-blue-500/25'
			};
		if (name.includes('azure') || name.includes('microsoft'))
			return {
				label: 'Azure CDN',
				color: 'text-sky-500 dark:text-sky-400',
				bg: 'bg-sky-500/10 border-sky-500/25'
			};
		if (name.includes('incapsula') || name.includes('imperva'))
			return {
				label: 'Imperva',
				color: 'text-rose-500 dark:text-rose-400',
				bg: 'bg-rose-500/10 border-rose-500/25'
			};
		if (name.includes('sucuri'))
			return {
				label: 'Sucuri',
				color: 'text-green-500 dark:text-green-400',
				bg: 'bg-green-500/10 border-green-500/25'
			};

		return {
			label: dns.cdn_name,
			color: 'text-cyan-500 dark:text-cyan-400',
			bg: 'bg-cyan-500/10 border-cyan-500/25'
		};
	});

	const RECORD_META: Record<string, { label: string; icon: typeof Globe; color: string }> = {
		A: { label: 'A (IPv4)', icon: Globe, color: 'text-blue-500' },
		AAAA: { label: 'AAAA (IPv6)', icon: Globe, color: 'text-purple-500' },
		NS: { label: 'Nameservers', icon: Server, color: 'text-emerald-500' },
		MX: { label: 'Mail Exchange', icon: Mail, color: 'text-amber-500' },
		TXT: { label: 'TXT Records', icon: FileText, color: 'text-slate-500 dark:text-slate-400' },
		SOA: { label: 'SOA', icon: Shield, color: 'text-indigo-500' },
		CNAME: { label: 'CNAME', icon: Network, color: 'text-cyan-500' },
		CAA: { label: 'CAA', icon: ShieldCheck, color: 'text-rose-500' },
		PTR: { label: 'PTR', icon: Globe, color: 'text-teal-500' },
		SRV: { label: 'SRV', icon: Server, color: 'text-orange-500' }
	};

	const RECORD_DISPLAY_ORDER = [
		'A',
		'AAAA',
		'CNAME',
		'NS',
		'MX',
		'TXT',
		'SOA',
		'CAA',
		'SRV',
		'PTR'
	];

	let orderedRecords = $derived.by(() => {
		if (!dns?.record_counts) return [];
		return RECORD_DISPLAY_ORDER.filter(
			(type) => dns.record_counts[type] && dns.record_counts[type] > 0
		).map((type) => ({
			type,
			count: dns.record_counts[type],
			meta: RECORD_META[type] ?? { label: type, icon: Globe, color: 'text-muted-foreground' }
		}));
	});

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

{#if !isApplicable}{:else if status === TaskStatus.PENDING || status === TaskStatus.QUERYING}
	<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
		<Loader class="h-3 w-3 animate-spin" />
		<span class="animate-pulse">DNS…</span>
	</div>
{:else if status === TaskStatus.FAILED}
	<div class="flex items-center gap-1.5 text-xs text-red-500/70 dark:text-red-400/70">
		<TriangleAlert class="h-3 w-3" />
		<span>DNS failed</span>
	</div>
{:else if status === TaskStatus.SUCCESS && dns}
	<div class="flex items-center gap-1.5 flex-wrap">
		{#if cdnInfo}
			<span
				class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium border {cdnInfo.bg} {cdnInfo.color}"
			>
				<ShieldCheck class="h-3 w-3" />
				{cdnInfo.label}
			</span>
		{/if}

		<!-- Record counts with hover card -->
		{#if inlineSummary}
			<HoverCard.Root openDelay={250} closeDelay={100}>
				<HoverCard.Trigger>
					<button
						type="button"
						class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer max-w-full"
						onclick={handleClick}
					>
						<Waypoints class="h-3 w-3 shrink-0" />
						<span class="truncate font-mono">{inlineSummary}</span>
					</button>
				</HoverCard.Trigger>
				<HoverCard.Content class="w-72 p-0" align="start" side="bottom">
					<!-- Header -->
					<div class="px-4 pt-3.5 pb-3 border-b border-border/50">
						<div class="flex items-center gap-2">
							<div class="flex items-center justify-center h-8 w-8 rounded-lg bg-blue-500/10">
								<Waypoints class="h-4 w-4 text-blue-500" />
							</div>
							<div class="min-w-0 flex-1">
								<p class="text-sm font-medium font-mono truncate">{targetValue}</p>
								<p class="text-xs text-muted-foreground">
									{totalRecords} DNS record{totalRecords !== 1 ? 's' : ''}
									{#if dns.status_code}
										· <span class="font-mono">{dns.status_code}</span>
									{/if}
								</p>
							</div>
						</div>
					</div>

					<!-- CDN callout -->
					{#if cdnInfo}
						<div class="px-4 py-2.5 border-b border-border/50 bg-muted/20">
							<div class="flex items-center gap-2">
								<ShieldCheck class="h-3.5 w-3.5 {cdnInfo.color} shrink-0" />
								<span class="text-xs font-medium {cdnInfo.color}">
									Behind {cdnInfo.label}
								</span>
								<span class="text-[11px] text-muted-foreground">— WAF / Proxy detected</span>
							</div>
						</div>
					{/if}

					<!-- Record type breakdown -->
					<div class="px-4 py-3">
						<div class="grid grid-cols-2 gap-x-4 gap-y-2">
							{#each orderedRecords as { type, count, meta }}
								{@const RecordIcon = meta.icon}
								<div class="flex items-center gap-2">
									<RecordIcon class="h-3 w-3 {meta.color} shrink-0" />
									<span class="text-xs text-muted-foreground flex-1">{meta.label}</span>
									<span class="text-xs font-medium font-mono">{count}</span>
								</div>
							{/each}
						</div>
					</div>

					<!-- Footer -->
					<div class="px-4 py-2.5 border-t border-border/50 bg-muted/30">
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
								<Clock class="h-3 w-3" />
								<span>Queried {formatQueriedAt(dns.queried_at)}</span>
							</div>
							<button
								type="button"
								class="flex items-center gap-1 text-[11px] text-primary/70 hover:text-primary transition-colors"
								onclick={() => goto(`/targets/${targetId}`)}
							>
								See Details
								<ExternalLink class="h-2.5 w-2.5" />
							</button>
						</div>
					</div>
				</HoverCard.Content>
			</HoverCard.Root>
		{/if}
	</div>
{/if}
