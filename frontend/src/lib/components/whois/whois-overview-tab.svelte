<script lang="ts">
	import type { WhoisRecordRead } from '$lib/types/whois';
	import { getStatusBadgeColor } from '$lib/types/whois';
	import {
		formatShortDate,
		getExpirationUrgency,
		formatExpirationLabel,
		getDomainAge,
		type ExpirationUrgency
	} from '$lib/utilities/dates';
	import * as Alert from '$lib/components/ui/alert';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import CopyButton from '@/components/copy-button.svelte';
	import {
		Globe,
		Server,
		Network,
		ShieldCheck,
		ShieldX,
		Building,
		UserRound,
		Mail,
		Hash,
		MonitorCog,
		Flag,
		Cable,
		CalendarDays,
		CalendarClock,
		CalendarCheck,
		TriangleAlert,
		OctagonAlert,
		ExternalLink
	} from 'lucide-svelte';

	interface Props {
		record: WhoisRecordRead;
		onCorrelationClick?: (type: string, value: string) => void;
	}

	let { record, onCorrelationClick }: Props = $props();

	let lookupType = $derived(record.lookup_type as 'DOMAIN' | 'IP' | 'ASN');

	let LookupIcon = $derived.by(() => {
		switch (lookupType) {
			case 'DOMAIN':
				return Globe;
			case 'IP':
				return Server;
			case 'ASN':
				return Network;
			default:
				return Globe;
		}
	});

	let urgency = $derived<ExpirationUrgency>(
		record.expiration_date ? getExpirationUrgency(record.expiration_date) : 'none'
	);

	let expirationLabel = $derived(
		record.expiration_date ? formatExpirationLabel(record.expiration_date) : ''
	);

	let domainAge = $derived(record.registration_date ? getDomainAge(record.registration_date) : '');

	let showAlert = $derived(
		urgency === 'expired' || urgency === 'critical' || urgency === 'warning'
	);

	let alertMessage = $derived.by(() => {
		switch (urgency) {
			case 'expired':
				return 'Expired, high risk of takeover. Verify ownership status immediately.';
			case 'critical':
				return `Expires ${expirationLabel.toLowerCase()}. Verify renewal is scheduled.`;
			case 'warning':
				return `Expires ${expirationLabel.toLowerCase()}. Add to renewal watchlist.`;
			default:
				return '';
		}
	});

	let hasNameservers = $derived(record.nameservers && record.nameservers.length > 0);

	let hasStatuses = $derived(record.domain_status && record.domain_status.length > 0);

	function handleCorrelationClick(type: string, value: string) {
		if (value && onCorrelationClick) {
			onCorrelationClick(type, value);
		}
	}
</script>

<div class="space-y-5 py-1">
	<!-- Expiration alert show only when about to expire  -->
	{#if showAlert}
		<Alert.Root
			variant={urgency === 'expired' || urgency === 'critical' ? 'destructive' : 'default'}
		>
			{#if urgency === 'expired' || urgency === 'critical'}
				<OctagonAlert class="h-4 w-4" />
			{:else}
				<TriangleAlert class="h-4 w-4" />
			{/if}
			<Alert.Title>
				{#if urgency === 'expired'}
					Domain Expired
				{:else if urgency === 'critical'}
					Expiration Imminent
				{:else}
					Expiration Approaching
				{/if}
			</Alert.Title>
			<Alert.Description>{alertMessage}</Alert.Description>
		</Alert.Root>
	{/if}

	<!-- Identity -->
	<div class="flex items-start gap-3">
		<div class="flex items-center justify-center h-10 w-10 rounded-xl bg-primary/10 shrink-0">
			<LookupIcon class="h-5 w-5 text-primary" />
		</div>
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2">
				<h3 class="text-lg font-semibold truncate">{record.name || record.query_value}</h3>
				<CopyButton value={record.query_value} />
			</div>
			<div class="flex items-center gap-2 mt-0.5">
				<Badge variant="outline" class="text-xs">{record.lookup_type}</Badge>
				{#if record.handle}
					<span class="text-xs text-muted-foreground font-mono">{record.handle}</span>
				{/if}
			</div>
		</div>
	</div>

	<Separator />

	<div class="grid grid-cols-2 gap-4">
		{#if record.registrant_name}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<UserRound class="h-3 w-3" />
					Registrant
				</div>
				<Tooltip.Root>
					<Tooltip.Trigger>
						<button
							class="text-sm font-medium text-left hover:text-primary transition-colors cursor-pointer inline-flex items-center gap-1 group"
							onclick={() => handleCorrelationClick('registrant_name', record.registrant_name)}
						>
							{record.registrant_name}
							<ExternalLink class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
						</button>
					</Tooltip.Trigger>
					<Tooltip.Content>
						<p>Find targets with same registrant</p>
					</Tooltip.Content>
				</Tooltip.Root>
				{#if record.registrant_email}
					<p class="text-xs text-muted-foreground">{record.registrant_email}</p>
				{/if}
			</div>
		{/if}

		{#if record.registrar_name}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<Building class="h-3 w-3" />
					Registrar
				</div>
				<Tooltip.Root>
					<Tooltip.Trigger>
						<button
							class="text-sm font-medium text-left hover:text-primary transition-colors cursor-pointer inline-flex items-center gap-1 group"
							onclick={() => handleCorrelationClick('registrar_name', record.registrar_name)}
						>
							{record.registrar_name}
							<ExternalLink class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
						</button>
					</Tooltip.Trigger>
					<Tooltip.Content>
						<p>Find targets with same registrar</p>
					</Tooltip.Content>
				</Tooltip.Root>
				{#if record.abuse_email}
					<div class="flex items-center gap-1 mt-0.5">
						<Mail class="h-3 w-3 text-muted-foreground" />
						<a
							href="mailto:{record.abuse_email}"
							class="text-xs text-muted-foreground hover:text-foreground transition-colors"
						>
							{record.abuse_email}
						</a>
					</div>
				{/if}
			</div>
		{/if}

		{#if record.network_cidr}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<Cable class="h-3 w-3" />
					Network
				</div>
				<Tooltip.Root>
					<Tooltip.Trigger>
						<button
							class="text-sm font-medium font-mono text-left hover:text-primary transition-colors cursor-pointer inline-flex items-center gap-1 group"
							onclick={() => handleCorrelationClick('network_cidr', record.network_cidr)}
						>
							{record.network_cidr}
							<ExternalLink class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
						</button>
					</Tooltip.Trigger>
					<Tooltip.Content>
						<p>Find targets in same network</p>
					</Tooltip.Content>
				</Tooltip.Root>
				{#if record.ip_version}
					<p class="text-xs text-muted-foreground">IPv{record.ip_version}</p>
				{/if}
			</div>
		{/if}

		{#if record.country}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<Flag class="h-3 w-3" />
					Country
				</div>
				<Tooltip.Root>
					<Tooltip.Trigger>
						<button
							class="text-sm font-medium text-left hover:text-primary transition-colors cursor-pointer inline-flex items-center gap-1 group"
							onclick={() => handleCorrelationClick('country', record.country)}
						>
							{record.country}
							<ExternalLink class="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
						</button>
					</Tooltip.Trigger>
					<Tooltip.Content>
						<p>Find targets in same country</p>
					</Tooltip.Content>
				</Tooltip.Root>
			</div>
		{/if}

		{#if record.registration_date}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<CalendarDays class="h-3 w-3" />
					Registered
				</div>
				<p class="text-sm font-medium">{formatShortDate(record.registration_date)}</p>
				{#if domainAge}
					<p class="text-xs text-muted-foreground">{domainAge}</p>
				{/if}
			</div>
		{/if}

		{#if record.last_changed_date}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<CalendarCheck class="h-3 w-3" />
					Last Updated
				</div>
				<p class="text-sm font-medium">{formatShortDate(record.last_changed_date)}</p>
			</div>
		{/if}

		{#if record.expiration_date}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider {urgency ===
						'expired' || urgency === 'critical'
						? 'text-red-500 dark:text-red-400'
						: urgency === 'warning'
							? 'text-amber-500 dark:text-amber-400'
							: ''}"
				>
					<CalendarClock class="h-3 w-3" />
					Expires
				</div>
				<p class="text-sm font-medium">{formatShortDate(record.expiration_date)}</p>
				{#if expirationLabel}
					<p
						class="text-xs font-medium {urgency === 'expired' || urgency === 'critical'
							? 'text-red-500 dark:text-red-400'
							: urgency === 'warning'
								? 'text-amber-500 dark:text-amber-400'
								: 'text-emerald-600 dark:text-emerald-400'}"
					>
						{expirationLabel}
					</p>
				{/if}
			</div>
		{/if}

		{#if record.whois_server}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<MonitorCog class="h-3 w-3" />
					WHOIS Server
				</div>
				<p class="text-sm font-mono text-muted-foreground">{record.whois_server}</p>
			</div>
		{/if}

		{#if record.rir}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<Hash class="h-3 w-3" />
					RIR
				</div>
				<p class="text-sm font-medium">{record.rir}</p>
			</div>
		{/if}

		{#if record.asn_range_start != null && record.asn_range_end != null}
			<div class="space-y-1">
				<div
					class="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider"
				>
					<Network class="h-3 w-3" />
					ASN Range
				</div>
				<p class="text-sm font-mono">{record.asn_range_start} – {record.asn_range_end}</p>
			</div>
		{/if}
	</div>

	<!-- DNSSEC -->
	{#if record.dnssec != null}
		<Separator />
		<div class="flex items-center gap-2">
			{#if record.dnssec}
				<ShieldCheck class="h-4 w-4 text-emerald-500" />
				<span class="text-sm font-medium text-emerald-600 dark:text-emerald-400"
					>DNSSEC Enabled</span
				>
			{:else}
				<ShieldX class="h-4 w-4 text-muted-foreground" />
				<span class="text-sm text-muted-foreground">DNSSEC Not Enabled</span>
			{/if}
		</div>
	{/if}

	<!-- Domain statuses -->
	{#if hasStatuses}
		<Separator />
		<div>
			<p class="text-[11px] text-muted-foreground uppercase tracking-wider mb-2">Domain Status</p>
			<div class="flex flex-wrap gap-1.5">
				{#each record.domain_status as status}
					<Badge class="text-xs font-normal border {getStatusBadgeColor(status)}">
						{status}
					</Badge>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Nameservers -->
	{#if hasNameservers}
		<Separator />
		<div>
			<p class="text-[11px] text-muted-foreground uppercase tracking-wider mb-2">Nameservers</p>
			<div class="flex flex-wrap gap-1.5">
				{#each record.nameservers as ns}
					<Tooltip.Root>
						<Tooltip.Trigger>
							<button
								class="cursor-pointer"
								onclick={() => handleCorrelationClick('nameserver', ns)}
							>
								<Badge
									variant="outline"
									class="text-xs font-mono font-normal gap-1.5 hover:bg-accent hover:border-primary/30 transition-colors"
								>
									<Server class="h-3 w-3 text-muted-foreground" />
									{ns}
								</Badge>
							</button>
						</Tooltip.Trigger>
						<Tooltip.Content>
							<p>Find targets on this nameserver</p>
						</Tooltip.Content>
					</Tooltip.Root>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Footer -->
	<Separator />
	<p class="text-xs text-muted-foreground">
		Last queried {formatShortDate(record.queried_at)}
	</p>
</div>
