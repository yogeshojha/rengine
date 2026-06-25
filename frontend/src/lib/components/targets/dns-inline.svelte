<script lang="ts">
	import { TargetType } from '$lib/types/target';
	import type { DnsSummaryData } from '$lib/types/target';
	import { DnsRecordType, DNS_RECORD_DISPLAY_ORDER } from '$lib/types/dns';
	import { TaskStatus } from '@/types/task-status';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';
	import { formatShortDate } from '$lib/utilities/dates';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Clock from '@lucide/svelte/icons/clock';
	import Globe from '@lucide/svelte/icons/globe';
	import Mail from '@lucide/svelte/icons/mail';
	import FileText from '@lucide/svelte/icons/file-text';
	import Server from '@lucide/svelte/icons/server';
	import Shield from '@lucide/svelte/icons/shield';
	import Network from '@lucide/svelte/icons/network';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import { Spinner } from '$lib/components/ui/spinner';

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

	let cdnInfo = $derived.by(() => {
		if (!dns?.cdn || !dns.cdn_name) return null;
		const name = dns.cdn_name.toLowerCase();

		if (name.includes('cloudflare')) return { label: 'Cloudflare' };
		if (name.includes('akamai')) return { label: 'Akamai' };
		if (name.includes('fastly')) return { label: 'Fastly' };
		if (name.includes('cloudfront') || name.includes('amazon')) return { label: 'CloudFront' };
		if (name.includes('google')) return { label: 'Google CDN' };
		if (name.includes('azure') || name.includes('microsoft')) return { label: 'Azure CDN' };
		if (name.includes('incapsula') || name.includes('imperva')) return { label: 'Imperva' };
		if (name.includes('sucuri')) return { label: 'Sucuri' };

		return { label: dns.cdn_name };
	});

	const RECORD_META: Partial<Record<DnsRecordType, { label: string; icon: IconComponent }>> = {
		[DnsRecordType.A]: { label: 'A (IPv4)', icon: Globe },
		[DnsRecordType.AAAA]: { label: 'AAAA (IPv6)', icon: Globe },
		[DnsRecordType.NS]: { label: 'Nameservers', icon: Server },
		[DnsRecordType.MX]: { label: 'Mail Exchange', icon: Mail },
		[DnsRecordType.TXT]: { label: 'TXT Records', icon: FileText },
		[DnsRecordType.SOA]: { label: 'SOA', icon: Shield },
		[DnsRecordType.CNAME]: { label: 'CNAME', icon: Network },
		[DnsRecordType.CAA]: { label: 'CAA', icon: ShieldCheck },
		[DnsRecordType.PTR]: { label: 'PTR', icon: Globe },
		[DnsRecordType.SRV]: { label: 'SRV', icon: Server }
	};

	let orderedRecords = $derived.by(() => {
		if (!dns?.record_counts) return [];
		return DNS_RECORD_DISPLAY_ORDER.filter(
			(type) => dns.record_counts[type] && dns.record_counts[type] > 0
		).map((type) => ({
			type,
			count: dns.record_counts[type],
			meta: RECORD_META[type] ?? { label: type, icon: Globe }
		}));
	});

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		onClick?.();
	}
</script>

{#if !isApplicable}{:else if status === TaskStatus.PENDING || status === TaskStatus.QUERYING}
	<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
		<Spinner class="h-3 w-3" />
		<span class="animate-pulse">DNS…</span>
	</div>
{:else if status === TaskStatus.FAILED}
	<div class="flex items-center gap-1.5 text-xs text-destructive/70">
		<TriangleAlert class="h-3 w-3" />
		<span>DNS failed</span>
	</div>
{:else if status === TaskStatus.SUCCESS && dns}
	<div class="flex items-center gap-1.5 flex-wrap">
		{#if cdnInfo}
			<span
				class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium border border-border/60 bg-muted/60 text-foreground/70"
			>
				<ShieldCheck class="h-3 w-3" />
				{cdnInfo.label}
			</span>
		{/if}

		{#if inlineSummary}
			<HoverCard.Root openDelay={250} closeDelay={100}>
				<HoverCard.Trigger>
					{#snippet child({ props })}
						<button
							{...props}
							type="button"
							class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer max-w-full"
							onclick={handleClick}
						>
							<Waypoints class="h-3 w-3 shrink-0" />
							<span class="truncate font-mono">{inlineSummary}</span>
						</button>
					{/snippet}
				</HoverCard.Trigger>
				<HoverCard.Content class="w-72 p-0" align="start" side="bottom">
					<div class="px-4 pt-3.5 pb-3 border-b border-border/50">
						<div class="flex items-center gap-2">
							<div class="flex items-center justify-center h-8 w-8 rounded-lg bg-muted">
								<Waypoints class="h-4 w-4 text-muted-foreground" />
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

					{#if cdnInfo}
						<div class="px-4 py-2.5 border-b border-border/50 bg-muted/20">
							<div class="flex items-center gap-2">
								<ShieldCheck class="h-3.5 w-3.5 text-muted-foreground shrink-0" />
								<span class="text-xs font-medium text-foreground/80">
									Behind {cdnInfo.label}
								</span>
								<span class="text-[11px] text-muted-foreground">— WAF / Proxy detected</span>
							</div>
						</div>
					{/if}

					<div class="px-4 py-3">
						<div class="grid grid-cols-2 gap-x-4 gap-y-2">
							{#each orderedRecords as record (record.type)}
								{@const RecordIcon = record.meta.icon}
								<div class="flex items-center gap-2">
									<RecordIcon class="h-3 w-3 text-muted-foreground shrink-0" />
									<span class="text-xs text-muted-foreground flex-1">{record.meta.label}</span>
									<span class="text-xs font-medium font-mono">{record.count}</span>
								</div>
							{/each}
						</div>
					</div>

					<div class="px-4 py-2.5 border-t border-border/50 bg-muted/30">
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
								<Clock class="h-3 w-3" />
								<span>Queried {dns.queried_at ? formatShortDate(dns.queried_at) : 'Unknown'}</span>
							</div>
							<button
								type="button"
								class="flex items-center gap-1 text-[11px] text-primary/70 hover:text-primary transition-colors"
								onclick={() => goto(ROUTES.target(targetId))}
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
