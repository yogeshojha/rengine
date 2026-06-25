<script lang="ts">
	import type { WhoisRecordRead, WhoisEntityRole } from '$lib/types/whois';
	import { ENTITY_ROLE_LABELS } from '$lib/types/whois';
	import { TargetType } from '$lib/types/target';
	import { MS_PER_DAY, formatShortDate } from '$lib/utilities/dates';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Shield from '@lucide/svelte/icons/shield';
	import ShieldOff from '@lucide/svelte/icons/shield-off';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';

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

	let detailOpen = $state(false);

	let registryCount = $derived(
		(isDomain ? (record.nameservers?.length ?? 0) + (record.domain_status?.length ?? 0) : 0) +
			entities.reduce((a, e) => a + e.items.length, 0)
	);
	let hasRegistryDetail = $derived(registryCount > 0 || (isDomain && record.dnssec != null));

	function fmtDate(d: string | null): string {
		if (!d) return '—';
		try {
			return formatShortDate(d);
		} catch {
			return d;
		}
	}

	function daysUntil(d: string | null): number | null {
		if (!d) return null;
		try {
			return Math.ceil((new Date(d).getTime() - Date.now()) / MS_PER_DAY);
		} catch {
			return null;
		}
	}

	let expiryDays = $derived(daysUntil(record.expiration_date));

	let expiryColor = $derived.by(() => {
		if (expiryDays == null) return '';
		if (expiryDays < 0) return 'text-destructive';
		if (expiryDays < 30) return 'text-warning';
		return 'text-muted-foreground';
	});
</script>

{#snippet kv(
	label: string,
	value: string | null | undefined,
	opts?: { mono?: boolean; copy?: boolean }
)}
	{#if value && value.trim() && value !== '—'}
		<dt class="text-[11px] leading-relaxed text-muted-foreground/55">{label}</dt>
		<dd class="flex min-w-0 items-baseline gap-1 group/kv">
			<span
				class="text-[11px] leading-relaxed text-foreground/80 break-all {opts?.mono
					? 'font-mono text-[10px]'
					: ''}">{value}</span
			>
			{#if opts?.copy}
				<div class="self-center opacity-0 group-hover/kv:opacity-100 transition-opacity shrink-0">
					<CopyButton {value} />
				</div>
			{/if}
		</dd>
	{/if}
{/snippet}

<div class="p-3 space-y-3">
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

	<dl class="grid grid-cols-[minmax(84px,max-content)_1fr] gap-x-4 gap-y-1">
		{#if isIp || isAsn}
			{@render kv('Name', record.name)}
		{/if}
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
			{@render kv('Description', record.description)}
		{/if}
		{#if isAsn && record.asn_range_start != null}
			{@render kv('ASN Range', `${record.asn_range_start} – ${record.asn_range_end}`)}
		{/if}
	</dl>

	{#if hasRegistryDetail}
		<Collapsible.Root bind:open={detailOpen}>
			<Collapsible.Trigger
				class="flex items-center gap-1.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
			>
				<ChevronRight
					class="h-3 w-3 transition-transform duration-150 {detailOpen ? 'rotate-90' : ''}"
				/>
				<span>Registry detail</span>
			</Collapsible.Trigger>

			<Collapsible.Content>
				<div class="mt-2 space-y-3">
					{#if isDomain}
						<div class="flex items-center gap-1.5 text-[11px]">
							{#if record.dnssec}
								<Shield class="h-3 w-3 text-muted-foreground/60" />
								<span class="text-muted-foreground">DNSSEC enabled</span>
							{:else}
								<ShieldOff class="h-3 w-3 text-muted-foreground/40" />
								<span class="text-muted-foreground/60">No DNSSEC</span>
							{/if}
						</div>
					{/if}

					{#if isDomain && record.nameservers?.length}
						<div class="space-y-1">
							<p
								class="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70"
							>
								Nameservers
							</p>
							<div class="flex flex-wrap gap-1">
								{#each record.nameservers as ns (ns)}
									<Badge
										variant="outline"
										class="text-[10px] font-mono text-muted-foreground rounded-md border-border/60 px-1.5 py-0.5"
										>{ns}</Badge
									>
								{/each}
							</div>
						</div>
					{/if}

					{#if isDomain && record.domain_status?.length}
						<div class="space-y-1">
							<p
								class="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70"
							>
								Status locks
							</p>
							<div class="flex flex-wrap gap-1">
								{#each record.domain_status as s (s)}
									<Badge
										variant="outline"
										class="text-[10px] h-[18px] px-1.5 text-muted-foreground border-border/60"
										>{s}</Badge
									>
								{/each}
							</div>
						</div>
					{/if}

					{#if entities.length > 0}
						<div class="space-y-1">
							<p
								class="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70"
							>
								Entities ({entities.reduce((a, e) => a + e.items.length, 0)})
							</p>
							<div class="space-y-1">
								{#each entities as ent (ent.role)}
									{#each ent.items as entity (entity.handle || entity.email || entity.name)}
										<div
											class="rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 space-y-0.5"
										>
											<span
												class="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50"
												>{ent.label}</span
											>
											{#if entity.name}<p class="text-[11px] font-medium text-foreground/80">
													{entity.name}
												</p>{/if}
											{#if entity.email}<p class="text-[10px] font-mono text-muted-foreground/60">
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
													<p class="text-[10px] text-muted-foreground/60">{parts.join(', ')}</p>
												{/if}
											{/if}
										</div>
									{/each}
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</Collapsible.Content>
		</Collapsible.Root>
	{/if}
</div>
