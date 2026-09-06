<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Info from '@lucide/svelte/icons/info';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import CopyButton from '$lib/components/copy-button.svelte';
	import CodeBlock from '$lib/components/code-block.svelte';
	import CountryFlag from '$lib/components/scans/results/country-flag.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import RecordShell from '../record-shell.svelte';
	import RecordGroup from '../record-group.svelte';
	import { nameserverProvider, registrarIcon } from '$lib/config/dns-providers';
	import { countryName } from '$lib/config/country-geo';
	import type { IconComponent } from '$lib/config/icons';
	import { TargetType } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import {
		ENTITY_ROLE_LABELS,
		describeDomainStatus,
		isRedactedName,
		type DomainStatusTone,
		type WhoisEntity,
		type WhoisEntityRole,
		type WhoisRecordRead
	} from '$lib/types/whois';
	import {
		formatExpirationLabel,
		formatShortDate,
		getDomainAge,
		getExpirationUrgency
	} from '$lib/utilities/dates';

	interface Props {
		targetValue: string;
		targetType: TargetType;
		record: WhoisRecordRead | null;
		status: TaskStatus;
		error: string | null;
		loading: boolean;
		refreshing: boolean;
		onRefresh: () => void;
	}

	let { targetValue, targetType, record, status, error, loading, refreshing, onRefresh }: Props =
		$props();

	const ROLES: WhoisEntityRole[] = [
		'registrant',
		'administrative',
		'technical',
		'abuse',
		'registrar',
		'billing',
		'noc',
		'routing',
		'sponsor'
	];
	const STATUS_ICON: Record<DomainStatusTone, IconComponent> = {
		pass: CircleCheck,
		warn: TriangleAlert,
		fail: CircleX,
		info: Info
	};
	const STATUS_COLOR: Record<DomainStatusTone, string> = {
		pass: 'text-success',
		warn: 'text-warning',
		fail: 'text-destructive',
		info: 'text-muted-foreground'
	};
	const ROW =
		'grid grid-cols-[7rem_minmax(0,1fr)] items-start gap-x-3 py-1.5 sm:grid-cols-[9rem_minmax(0,1fr)]';

	let isDomain = $derived(targetType === TargetType.DOMAIN || targetType === TargetType.URL);
	let isAsn = $derived(targetType === TargetType.ASN);
	let title = $derived(isDomain ? 'Registration' : isAsn ? 'AS registration' : 'Allocation');

	interface Fact {
		key: string;
		label: string;
		value: string;
		sub?: string;
		mono?: boolean;
		copy?: string;
		tone?: 'warn' | 'bad';
		flag?: string;
		brand?: string | null;
	}

	let facts = $derived.by<Fact[]>(() => {
		if (!record) return [];
		const out: Fact[] = [];
		const push = (f: Fact) => {
			if (f.value && f.value.trim()) out.push(f);
		};
		if (isDomain) {
			push({
				key: 'registrar',
				label: 'Registrar',
				value: record.registrar_name,
				brand: registrarIcon(record.registrar_name)
			});
			push({
				key: 'registrant',
				label: 'Registrant',
				value: record.registrant_name,
				sub: isRedactedName(record.registrant_name) ? 'identity redacted' : undefined
			});
		} else {
			push({ key: 'name', label: isAsn ? 'AS name' : 'Network name', value: record.name });
			push({ key: 'registrant', label: 'Registrant', value: record.registrant_name });
			if (record.network_cidr)
				push({
					key: 'cidr',
					label: 'Network',
					value: record.network_cidr,
					mono: true,
					copy: record.network_cidr,
					sub: record.ip_version ? `IPv${record.ip_version}` : undefined
				});
			if (isAsn && record.asn_range_start != null)
				push({
					key: 'range',
					label: 'AS range',
					value:
						record.asn_range_end != null && record.asn_range_end !== record.asn_range_start
							? `AS${record.asn_range_start} – AS${record.asn_range_end}`
							: `AS${record.asn_range_start}`,
					mono: true
				});
			push({ key: 'assignment', label: 'Assignment', value: record.assignment_type });
		}
		if (record.rir) push({ key: 'rir', label: 'Registry', value: record.rir.toUpperCase() });
		if (record.country)
			push({
				key: 'country',
				label: 'Country',
				value: countryName(record.country),
				sub: record.country.toUpperCase(),
				flag: record.country
			});
		if (record.registration_date)
			push({
				key: 'registered',
				label: 'Registered',
				value: formatShortDate(record.registration_date),
				sub: getDomainAge(record.registration_date)
			});
		if (record.last_changed_date)
			push({
				key: 'updated',
				label: 'Last changed',
				value: formatShortDate(record.last_changed_date)
			});
		if (record.expiration_date) {
			const urgency = getExpirationUrgency(record.expiration_date);
			push({
				key: 'expires',
				label: 'Expires',
				value: formatShortDate(record.expiration_date),
				sub: formatExpirationLabel(record.expiration_date),
				tone:
					urgency === 'expired'
						? 'bad'
						: urgency === 'critical' || urgency === 'warning'
							? 'warn'
							: undefined
			});
		}
		if (isDomain && record.dnssec != null)
			push({
				key: 'dnssec',
				label: 'DNSSEC',
				value: record.dnssec ? 'Enabled' : 'Not enabled',
				tone: record.dnssec ? undefined : 'warn'
			});
		push({
			key: 'abuse',
			label: 'Abuse contact',
			value: record.abuse_email,
			mono: true,
			copy: record.abuse_email
		});
		push({
			key: 'registrant_email',
			label: 'Registrant email',
			value: record.registrant_email,
			mono: true,
			copy: record.registrant_email
		});
		push({ key: 'server', label: 'WHOIS server', value: record.whois_server, mono: true });
		push({ key: 'handle', label: 'Handle', value: record.handle, mono: true, copy: record.handle });
		return out;
	});

	let descriptionLines = $derived(
		(record?.parsed_data?.description ?? []).map((l) => l.trim()).filter(Boolean)
	);
	let statuses = $derived(
		(record?.domain_status ?? []).map((code) => ({ code, ...describeDomainStatus(code) }))
	);
	let nameservers = $derived(record?.nameservers ?? []);
	let entities = $derived.by(() => {
		const parsed = record?.parsed_data;
		if (!parsed?.entities) return [] as { role: WhoisEntityRole; entity: WhoisEntity }[];
		return ROLES.flatMap((role) =>
			(parsed.entities[role] ?? []).map((entity) => ({ role, entity }))
		);
	});
	let recordJson = $derived(record?.parsed_data ? JSON.stringify(record.parsed_data, null, 2) : '');
	let rawOpen = $state(false);

	function addressLines(entity: WhoisEntity): string[] {
		const a = entity.address;
		if (!a) return [];
		return [
			[a.street_address, a.ext_address].filter(Boolean).join(', '),
			[a.locality, a.region, a.postal_code].filter(Boolean).join(', '),
			a.country
		].filter((l) => l && l.trim());
	}
</script>

<RecordShell
	name="WHOIS"
	{status}
	{error}
	queriedAt={record?.queried_at}
	{refreshing}
	{loading}
	empty={!record}
	emptyText="No registration record is stored for {targetValue}."
	{onRefresh}
>
	{#snippet bar()}
		<span class="text-[13px]">
			<span class="font-medium">{title}</span>
			<span class="text-muted-foreground">
				· {record?.query_value || targetValue}{record?.whois_server
					? ` · ${record.whois_server}`
					: ''}
			</span>
		</span>
	{/snippet}

	<div class="flex flex-col">
		<RecordGroup label={title} mono={false} sub={record?.object_class || undefined}>
			{#each facts as f (f.key)}
				<div class="group {ROW}">
					<span class="pt-px text-xs text-muted-foreground">{f.label}</span>
					<span
						class="flex min-w-0 flex-col text-[13px] leading-5 {f.tone === 'bad'
							? 'text-destructive'
							: f.tone === 'warn'
								? 'text-warning'
								: ''}"
					>
						<span class="flex min-w-0 items-center gap-1.5">
							{#if f.brand}<TechIcon name={f.brand} class="size-4 rounded-[4px]" />{/if}
							{#if f.flag}<CountryFlag code={f.flag} showCode={false} />{/if}
							<span class="min-w-0 wrap-anywhere {f.mono ? 'font-mono text-[12.5px]' : ''}">
								{f.value}
							</span>
							{#if f.copy}
								<span
									class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
								>
									<CopyButton value={f.copy} class="size-5" />
								</span>
							{/if}
						</span>
						{#if f.sub}<span class="text-xs text-muted-foreground">{f.sub}</span>{/if}
					</span>
				</div>
			{/each}
			{#if descriptionLines.length}
				<div class={ROW}>
					<span class="pt-px text-xs text-muted-foreground">Description</span>
					<span class="flex flex-col text-[13px] leading-5">
						{#each descriptionLines as line, i (i)}<span class="wrap-anywhere">{line}</span>{/each}
					</span>
				</div>
			{/if}
		</RecordGroup>

		{#if statuses.length}
			<RecordGroup
				label="Status"
				mono={false}
				sub="{statuses.length} EPP {statuses.length === 1 ? 'code' : 'codes'}"
			>
				{#each statuses as s (s.code)}
					{@const Icon = STATUS_ICON[s.tone]}
					<div class="flex items-center gap-2.5 py-1.5 text-[13px]">
						<Icon class="size-3.5 shrink-0 {STATUS_COLOR[s.tone]}" />
						<span class="min-w-0 flex-1">{s.label}</span>
						<span class="truncate font-mono text-xs text-muted-foreground">{s.code}</span>
					</div>
				{/each}
			</RecordGroup>
		{/if}

		{#if nameservers.length}
			<RecordGroup label="Nameservers" mono={false} sub="{nameservers.length} at the registry">
				{#each nameservers as ns (ns)}
					{@const p = nameserverProvider([ns])}
					<div class="group flex items-center gap-3 py-1.5 text-[13px]">
						<code class="min-w-0 flex-1 font-mono text-[12.5px] wrap-anywhere">{ns}</code>
						{#if p}
							<span class="flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground">
								<TechIcon name={p.icon ?? p.name} class="size-3.5 rounded-[3px]" />{p.name}
							</span>
						{/if}
						<span
							class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
						>
							<CopyButton value={ns} class="size-5" />
						</span>
					</div>
				{/each}
			</RecordGroup>
		{/if}

		{#if entities.length}
			<RecordGroup label="Contacts" mono={false} sub="{entities.length} in the record">
				{#each entities as { role, entity }, i (`${role}-${i}`)}
					{@const lines = addressLines(entity)}
					<div
						class="group grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 py-2 sm:grid-cols-[9rem_minmax(0,1fr)]"
					>
						<span class="pt-px text-xs text-muted-foreground">{ENTITY_ROLE_LABELS[role]}</span>
						<span class="flex min-w-0 flex-col gap-0.5 text-[13px] leading-5">
							{#if entity.name || entity.handle}
								<span class="font-medium wrap-anywhere">{entity.name || entity.handle}</span>
							{/if}
							{#if entity.email}
								<span class="flex min-w-0 items-center gap-1">
									<code class="font-mono text-xs text-muted-foreground wrap-anywhere">
										{entity.email}
									</code>
									<span
										class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
									>
										<CopyButton value={entity.email} class="size-5" />
									</span>
								</span>
							{/if}
							{#if entity.tel}
								<span class="font-mono text-xs text-muted-foreground">{entity.tel}</span>
							{/if}
							{#each lines as line, j (j)}
								<span class="text-xs text-muted-foreground wrap-anywhere">{line}</span>
							{/each}
							{#if entity.handle && entity.handle !== entity.name}
								<span class="font-mono text-[11px] text-muted-foreground/70">{entity.handle}</span>
							{/if}
						</span>
					</div>
				{/each}
			</RecordGroup>
		{/if}

		{#if recordJson}
			<Collapsible.Root bind:open={rawOpen} class="border-b">
				<Collapsible.Trigger
					class="group flex w-full items-center gap-2 py-2.5 text-left text-[13px] text-muted-foreground hover:text-foreground"
				>
					<ChevronRight class="size-3.5 transition-transform group-data-[state=open]:rotate-90" />
					Parsed record
				</Collapsible.Trigger>
				<Collapsible.Content>
					<CodeBlock
						code={recordJson}
						lang="json"
						label="whois.json"
						download="whois.json"
						maxHeight="32rem"
						maxLines={0}
						class="mb-3"
					/>
				</Collapsible.Content>
			</Collapsible.Root>
		{/if}
	</div>
</RecordShell>
