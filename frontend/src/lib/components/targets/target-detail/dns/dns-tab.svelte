<script lang="ts">
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Search from '@lucide/svelte/icons/search';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import RecordShell from '../record-shell.svelte';
	import RecordGroup from '../record-group.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { mailProvider, nameserverProvider, txtPurpose } from '$lib/config/dns-providers';
	import { DNS_RECORD_DISPLAY_ORDER, DnsRecordType } from '$lib/types/dns';
	import { TaskStatus } from '$lib/types/task-status';
	import type { DnsLookupRead, DnsRecordRead } from '$lib/types/target-detail';
	import { isPrivateIp } from '$lib/utilities/scan-correlation';
	import { filterToken } from '$lib/utilities/scan-insights';

	interface Props {
		host: string;
		lookup: DnsLookupRead | null;
		status: TaskStatus;
		error: string | null;
		loading: boolean;
		refreshing: boolean;
		ipsScanId: string | null;
		onRefresh: () => void;
	}

	let { host, lookup, status, error, loading, refreshing, ipsScanId, onRefresh }: Props = $props();

	const IPS = SURFACE[SurfaceDimension.IPS];
	const ALL = 'all';

	let type = $state<string>(ALL);
	let query = $state('');

	let records = $derived(
		[...(lookup?.records ?? [])]
			.filter((r) => r.record_type !== DnsRecordType.CDN)
			.sort((a, b) => order(a.record_type) - order(b.record_type) || byPriority(a, b))
	);
	let groups = $derived.by(() => {
		const q = query.trim().toLowerCase();
		const byType: Record<string, DnsRecordRead[]> = {};
		for (const r of records) {
			if (type !== ALL && r.record_type !== type) continue;
			if (q && !r.value.toLowerCase().includes(q)) continue;
			(byType[r.record_type] ??= []).push(r);
		}
		return Object.entries(byType).sort((a, b) => order(a[0]) - order(b[0]));
	});
	let typeCounts = $derived.by(() => {
		const counts: Record<string, number> = {};
		for (const r of records) counts[r.record_type] = (counts[r.record_type] ?? 0) + 1;
		return Object.entries(counts).sort((a, b) => order(a[0]) - order(b[0]));
	});
	let cdnName = $derived(lookup?.cdn ? lookup.cdn_name || 'CDN detected' : null);

	$effect(() => {
		if (type !== ALL && !typeCounts.some(([key]) => key === type)) type = ALL;
	});

	function order(t: string): number {
		const i = DNS_RECORD_DISPLAY_ORDER.indexOf(t as DnsRecordType);
		return i === -1 ? 99 : i;
	}
	function byPriority(a: DnsRecordRead, b: DnsRecordRead): number {
		return (a.priority ?? 0) - (b.priority ?? 0) || a.value.localeCompare(b.value);
	}

	interface Note {
		brand?: string | null;
		tag?: string;
		text?: string;
		tone?: 'warn';
	}
	function noteFor(r: DnsRecordRead): Note {
		switch (r.record_type) {
			case DnsRecordType.A:
			case DnsRecordType.AAAA:
				if (isPrivateIp(r.value)) return { text: 'Private address range', tone: 'warn' };
				return cdnName
					? {
							text: lookup?.cdn_name ? `${lookup.cdn_name} edge` : 'CDN edge',
							brand: lookup?.cdn_name || null
						}
					: {};
			case DnsRecordType.NS: {
				const p = nameserverProvider([r.value]);
				return p ? { text: p.name, brand: p.icon } : {};
			}
			case DnsRecordType.MX: {
				const p = mailProvider([r.value]);
				const prio = r.priority != null ? `priority ${r.priority}` : '';
				return p
					? { text: [p.name, prio].filter(Boolean).join(' · '), brand: p.icon }
					: { text: prio };
			}
			case DnsRecordType.TXT: {
				const p = txtPurpose(r.value);
				if (p.kind === 'other') return {};
				if (p.kind === 'verification') return { tag: p.label, text: 'verification', brand: p.icon };
				return { tag: p.label, text: p.detail };
			}
			case DnsRecordType.SOA: {
				const parts: string[] = [];
				if (r.soa_email) parts.push(r.soa_email);
				if (r.soa_serial != null) parts.push(`serial ${r.soa_serial}`);
				return { text: parts.join(' · ') };
			}
			case DnsRecordType.SRV: {
				const parts: string[] = [];
				if (r.priority != null) parts.push(`priority ${r.priority}`);
				if (r.weight != null) parts.push(`weight ${r.weight}`);
				if (r.port != null) parts.push(`port ${r.port}`);
				return { text: parts.join(' · ') };
			}
			case DnsRecordType.CAA:
				return {
					text: r.caa_tag ? `${r.caa_tag}${r.caa_flag ? ` · flag ${r.caa_flag}` : ''}` : undefined
				};
			default:
				return {};
		}
	}
	const isAddress = (r: DnsRecordRead) =>
		r.record_type === DnsRecordType.A || r.record_type === DnsRecordType.AAAA;
	const ipsHref = (ip: string) =>
		ipsScanId
			? ROUTES.scanTab(ipsScanId, IPS.tab, { [IPS.queryParam]: filterToken('ip', ip) })
			: null;
	const plural = (n: number) => `${n} ${n === 1 ? 'record' : 'records'}`;
</script>

<RecordShell
	name="DNS"
	{status}
	{error}
	queriedAt={lookup?.queried_at}
	{refreshing}
	{loading}
	empty={records.length === 0}
	emptyText="The lookup returned no records for {host}."
	{onRefresh}
>
	{#snippet bar()}
		<div class="flex flex-wrap items-center gap-0.5">
			<button
				type="button"
				class="rounded-md px-2 py-1 text-[13px] {type === ALL
					? 'bg-muted font-medium'
					: 'text-muted-foreground hover:text-foreground'}"
				onclick={() => (type = ALL)}
			>
				All <span class="ml-1 text-[11px] tabular-nums">{records.length}</span>
			</button>
			{#each typeCounts as [key, n] (key)}
				<button
					type="button"
					class="rounded-md px-2 py-1 font-mono text-[12px] {type === key
						? 'bg-muted font-medium'
						: 'text-muted-foreground hover:text-foreground'}"
					onclick={() => (type = key)}
				>
					{key} <span class="ml-1 font-sans text-[11px] tabular-nums">{n}</span>
				</button>
			{/each}
		</div>
		<span class="text-xs text-muted-foreground">
			{#if lookup?.status_code}<span class="font-mono">{lookup.status_code}</span>{/if}
			{#if cdnName}
				· {cdnName}{/if}
		</span>
		<div class="relative">
			<Search
				class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:value={query}
				placeholder="Filter records"
				aria-label="Filter records"
				class="h-8 w-52 pl-8 text-[13px]"
			/>
		</div>
	{/snippet}

	{#if groups.length === 0}
		<p class="border-t py-8 text-center text-sm text-muted-foreground">No record matches.</p>
	{:else}
		<div class="flex flex-col">
			{#each groups as [key, rows] (key)}
				<RecordGroup label={key} sub={plural(rows.length)}>
					{#each rows as r (r.id)}
						{@const note = noteFor(r)}
						{@const href = isAddress(r) ? ipsHref(r.value) : null}
						<div
							class="group grid min-h-8 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 py-1.5 sm:grid-cols-[minmax(0,1fr)_16rem_auto]"
						>
							<span class="font-mono text-[12.5px] leading-5 wrap-anywhere">{r.value}</span>
							<span
								class="hidden min-w-0 items-center gap-1.5 text-xs text-muted-foreground sm:flex {note.tone ===
								'warn'
									? 'text-warning'
									: ''}"
							>
								{#if note.brand}<TechIcon name={note.brand} class="size-3.5 rounded-[3px]" />{/if}
								{#if note.tag}
									<span
										class="rounded-[5px] bg-muted px-1.5 text-[11px] font-semibold text-foreground"
									>
										{note.tag}
									</span>
								{/if}
								{#if note.text}<span class="truncate">{note.text}</span>{/if}
								{#if href}
									<a {href} class="font-medium text-primary hover:underline">open in {IPS.label}</a>
								{/if}
							</span>
							<span
								class="flex items-center gap-0.5 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
							>
								{#if href}
									<Hint text="Open in {IPS.label}">
										{#snippet child(props)}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-6 text-muted-foreground sm:hidden"
												{href}
												aria-label="Open {r.value} in {IPS.label}"
											>
												<ExternalLink class="size-3.5" />
											</Button>
										{/snippet}
									</Hint>
								{/if}
								<CopyButton value={r.value} class="size-6" />
							</span>
						</div>
					{/each}
				</RecordGroup>
			{/each}
		</div>
	{/if}
</RecordShell>
