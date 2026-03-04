<script lang="ts">
	import type { WhoisRecordRead, WhoisEntityRole } from '$lib/types/whois';
	import { ENTITY_ROLE_LABELS, getStatusBadgeColor } from '$lib/types/whois';
	import { TargetType } from '$lib/types/target';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import {
		Shield,
		ShieldOff,
		ChevronRight,
		Clock,
		AlertTriangle,
		CalendarClock
	} from 'lucide-svelte';

	interface Props {
		record: WhoisRecordRead;
		targetType: TargetType;
	}

	let { record, targetType }: Props = $props();

	let parsed = $derived(record.parsed_data);
	let isDomain = $derived(targetType === TargetType.DOMAIN || targetType === TargetType.URL);
	let isIp = $derived(targetType === TargetType.IP || targetType === TargetType.IP_RANGE);
	let isAsn = $derived(targetType === TargetType.ASN);

	let entities = $derived.by(() => {
		if (!parsed?.entities) return [];
		const roles: WhoisEntityRole[] = [
			'registrant',
			'administrative',
			'technical',
			'abuse',
			'registrar'
		];
		return roles
			.filter((r) => parsed!.entities[r]?.length > 0)
			.map((r) => ({ role: r, label: ENTITY_ROLE_LABELS[r], items: parsed!.entities[r] }));
	});

	let entitiesOpen = $state(false);

	function fmtDate(d: string | null): string {
		if (!d) return '—';
		try {
			return new Date(d).toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric'
			});
		} catch {
			return d;
		}
	}

	function daysUntil(d: string | null): number | null {
		if (!d) return null;
		try {
			return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);
		} catch {
			return null;
		}
	}

	let expiryDays = $derived(daysUntil(record.expiration_date));

	// expiry styling
	let expiryColor = $derived.by(() => {
		if (expiryDays == null) return '';
		if (expiryDays < 0) return 'text-red-400';
		if (expiryDays < 30) return 'text-amber-400';
		return 'text-muted-foreground/60';
	});
</script>

{#snippet kv(
	label: string,
	value: string | null | undefined,
	opts?: { mono?: boolean; copy?: boolean }
)}
	{#if value && value.trim() && value !== '—'}
		<div class="flex items-start justify-between gap-3 py-[3px] group/kv">
			<span class="text-[10px] text-muted-foreground/50 shrink-0">{label}</span>
			<div class="flex items-center gap-1 min-w-0 justify-end">
				<span
					class="text-[11px] text-right text-foreground/75 break-all {opts?.mono
						? 'font-mono text-[10px]'
						: ''}">{value}</span
				>
				{#if opts?.copy}
					<div class="opacity-0 group-hover/kv:opacity-100 transition-opacity shrink-0">
						<CopyButton {value} />
					</div>
				{/if}
			</div>
		</div>
	{/if}
{/snippet}

<div class="p-3 space-y-3">
	<!-- expiry as inline indicator, not a banner -->
	{#if isDomain && expiryDays != null}
		<div class="flex items-center gap-1.5 text-[10px] {expiryColor}">
			{#if expiryDays < 0}
				<AlertTriangle class="h-3 w-3 shrink-0" />
				<span class="font-medium">Expired {Math.abs(expiryDays)}d ago</span>
			{:else if expiryDays < 30}
				<AlertTriangle class="h-3 w-3 shrink-0" />
				<span class="font-medium">Expires in {expiryDays}d</span>
			{:else}
				<CalendarClock class="h-3 w-3 shrink-0" />
				<span>Expires in {expiryDays}d</span>
			{/if}
			<span class="ml-auto font-mono text-[9px] opacity-40">{fmtDate(record.expiration_date)}</span>
		</div>
	{/if}

	<!-- key-value pairs -->
	<div class="space-y-px">
		{@render kv('Registrar', record.registrar_name)}
		{@render kv('Registrant', record.registrant_name)}
		{@render kv('Registered', fmtDate(record.registration_date))}
		{@render kv('Updated', fmtDate(record.last_changed_date))}
		{#if !isDomain || expiryDays == null}
			{@render kv('Expires', fmtDate(record.expiration_date))}
		{/if}
		{@render kv('WHOIS Server', record.whois_server, { mono: true })}
		{@render kv('Abuse Email', record.abuse_email, { mono: true, copy: true })}
		{@render kv('Registrant Email', record.registrant_email, { mono: true, copy: true })}
		{@render kv('Country', record.country)}
		{@render kv('RIR', record.rir)}
		{#if isIp || isAsn}
			{@render kv('Network CIDR', record.network_cidr, { mono: true, copy: true })}
			{@render kv('Assignment', record.assignment_type)}
		{/if}
		{#if isAsn && record.asn_range_start != null}
			{@render kv('ASN Range', `${record.asn_range_start} – ${record.asn_range_end}`)}
		{/if}
	</div>

	<!-- nameservers as chips -->
	{#if isDomain && record.nameservers?.length}
		<div class="space-y-1">
			<p class="text-[9px] font-bold uppercase tracking-[0.08em] text-muted-foreground/35">
				Nameservers
			</p>
			<div class="flex flex-wrap gap-1">
				{#each record.nameservers as ns}
					<span
						class="text-[9px] font-mono text-foreground/60 rounded border border-border/30 bg-muted/10 px-1.5 py-0.5"
						>{ns}</span
					>
				{/each}
			</div>
		</div>
	{/if}

	<!-- domain status pills -->
	{#if isDomain && record.domain_status?.length}
		<div class="space-y-1">
			<p class="text-[9px] font-bold uppercase tracking-[0.08em] text-muted-foreground/35">
				Status
			</p>
			<div class="flex flex-wrap gap-1">
				{#each record.domain_status as s}
					<Badge variant="outline" class="text-[8px] h-[16px] px-1 {getStatusBadgeColor(s)}"
						>{s}</Badge
					>
				{/each}
			</div>
		</div>
	{/if}

	<!-- DNSSEC — icon only, no badge -->
	{#if isDomain}
		<div class="flex items-center gap-1.5 text-[10px]">
			{#if record.dnssec}
				<Shield class="h-3 w-3 text-emerald-400/70" />
				<span class="text-emerald-400/70">DNSSEC</span>
			{:else}
				<ShieldOff class="h-3 w-3 text-muted-foreground/20" />
				<span class="text-muted-foreground/30">No DNSSEC</span>
			{/if}
		</div>
	{/if}

	<!-- entities — collapsible -->
	{#if entities.length > 0}
		<div>
			<button
				class="flex items-center gap-1.5 text-[10px] text-muted-foreground/40 transition-colors hover:text-foreground/60"
				onclick={() => (entitiesOpen = !entitiesOpen)}
			>
				<ChevronRight
					class="h-2.5 w-2.5 transition-transform duration-150 {entitiesOpen ? 'rotate-90' : ''}"
				/>
				<span>Entities ({entities.reduce((a, e) => a + e.items.length, 0)})</span>
			</button>

			{#if entitiesOpen}
				<div class="mt-1.5 space-y-1">
					{#each entities as ent (ent.role)}
						{#each ent.items as entity}
							<div class="rounded border border-border/20 bg-muted/5 px-2.5 py-1.5 space-y-0.5">
								<span class="text-[7px] font-bold uppercase tracking-wider text-muted-foreground/30"
									>{ent.label}</span
								>
								{#if entity.name}<p class="text-[10px] font-medium text-foreground/75">
										{entity.name}
									</p>{/if}
								{#if entity.email}<p class="text-[9px] font-mono text-muted-foreground/50">
										{entity.email}
									</p>{/if}
								{#if entity.address}
									{@const parts = [
										entity.address.street_address,
										entity.address.locality,
										entity.address.region,
										entity.address.postal_code
									].filter(Boolean)}
									{#if parts.length}
										<p class="text-[9px] text-muted-foreground/35">{parts.join(', ')}</p>
									{/if}
								{/if}
							</div>
						{/each}
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
