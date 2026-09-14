<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { SvelteSet } from 'svelte/reactivity';
	import Cell from './cell.svelte';
	import SignalSheet, { type SheetRow } from './signal-sheet.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { MS_PER_DAY, relativeTime } from '$lib/utilities/dates';
	import type { DashboardDiscovery, DashboardOverview } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		discovery: DashboardDiscovery | null;
		onSchedule: (ids: string[]) => void;
		class?: string;
	}

	let { overview, discovery, onSchedule, class: className = '' }: Props = $props();

	interface SheetState {
		kind?: 'discovery';
		title: string;
		rows: SheetRow[];
	}
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
	function expiryText(iso: string): string {
		const days = Math.round((new Date(iso).getTime() - Date.now()) / MS_PER_DAY);
		if (days < 0) return `expired ${plural(-days, 'day', 'days')} ago`;
		if (days === 0) return 'expires today';
		return `expires in ${plural(days, 'day', 'days')}`;
	}

	let sheet = $state<SheetState | null>(null);
	let sheetOpen = $state(false);
	function show(state: SheetState) {
		sheet = state;
		sheetOpen = true;
	}

	let added = new SvelteSet<string>();
	let pending = $state<string | null>(null);
	async function addTarget(domain: string) {
		const slug = projectsStore.activeProject?.slug;
		if (!slug) return;
		pending = domain;
		try {
			await targetsApi.create({ target_value: domain, project_slug: slug });
			added.add(domain);
			toast.success(`${domain} added`);
		} catch {
			toast.error(`${domain} not added`);
		} finally {
			pending = null;
		}
	}
	let discoveryRows = $derived.by<SheetRow[]>(() =>
		(discovery?.domains ?? []).map((d) => {
			const source = d.sources[0];
			const on =
				d.sources.length > 1 ? plural(d.sources.length, 'target', 'targets') : source?.target_value;
			return {
				key: d.domain,
				primary: d.domain,
				secondary: `${plural(d.hostname_count, 'hostname', 'hostnames')} on certificates of ${on}`,
				action: {
					label: 'Add target',
					doneLabel: 'Added',
					done: added.has(d.domain),
					pending: pending === d.domain,
					onClick: () => addTarget(d.domain)
				}
			};
		})
	);
	let sheetRows = $derived(sheet?.kind === 'discovery' ? discoveryRows : (sheet?.rows ?? []));

	interface Tile {
		key: string;
		label: string;
		count: number;
		detail: string | null;
		tone: string | null;
		open: () => void;
	}
	let unscheduled = $derived(overview.targets.filter((t) => !t.monitored).map((t) => t.id));
	let tiles = $derived.by<Tile[]>(() => {
		const out: Tile[] = [];
		const takeover = overview.signals.takeover;
		if (takeover.count > 0)
			out.push({
				key: 'takeover',
				label: 'Takeover candidates',
				count: takeover.count,
				detail: 'dangling records',
				tone: 'var(--sev-high)',
				open: () =>
					show({
						title: 'Takeover candidates',
						rows: takeover.items.map((c) => ({
							key: c.name,
							primary: c.name,
							secondary: `${c.cname} · ${c.provider}`,
							meta: relativeTime(c.last_seen),
							href: ROUTES.target(c.target_id, 'web-assets')
						}))
					})
			});
		const spoof = overview.signals.spoofable;
		if (spoof.count > 0)
			out.push({
				key: 'spoofable',
				label: 'Spoofable',
				count: spoof.count,
				detail: 'no SPF or DMARC',
				tone: 'var(--sev-medium)',
				open: () =>
					show({
						title: 'Spoofable domains',
						rows: spoof.items.map((d) => ({
							key: d.target_id,
							primary: d.target_value,
							meta: d.reason,
							href: ROUTES.target(d.target_id, 'dns')
						}))
					})
			});
		if (overview.expiring.length)
			out.push({
				key: 'domains',
				label: 'Domains expiring',
				count: overview.expiring.length,
				detail: 'within 30 days',
				tone: null,
				open: () =>
					show({
						title: 'Domains expiring within 30 days',
						rows: overview.expiring.map((t) => ({
							key: t.target_id,
							primary: t.target_value,
							meta: expiryText(t.expires_at),
							href: ROUTES.target(t.target_id, 'whois')
						}))
					})
			});
		const leads = discovery?.domains.length ?? 0;
		if (leads > 0)
			out.push({
				key: 'leads',
				label: 'Untracked domains',
				count: leads,
				detail: 'named on certificates',
				tone: null,
				open: () => show({ kind: 'discovery', title: 'Untracked domains', rows: [] })
			});
		if (unscheduled.length)
			out.push({
				key: 'unscheduled',
				label: 'Not monitored',
				count: unscheduled.length,
				detail: 'no schedule',
				tone: null,
				open: () => onSchedule(unscheduled)
			});
		if (overview.targets_stale)
			out.push({
				key: 'stale',
				label: 'Stale',
				count: overview.targets_stale,
				detail: 'no run in 30 days',
				tone: null,
				open: () =>
					show({
						title: 'Targets older than 30 days',
						rows: overview.stale.map((t) => ({
							key: t.target_id,
							primary: t.target_value,
							meta: t.last_scanned_at ? relativeTime(t.last_scanned_at) : undefined,
							href: ROUTES.target(t.target_id)
						}))
					})
			});
		return out;
	});
</script>

<Cell id="ownership" title="Ownership" class={className}>
	{#if tiles.length}
		<div class="grid grid-cols-2 gap-2">
			{#each tiles as t (t.key)}
				<button
					type="button"
					class="flex flex-col gap-0.5 rounded-lg border bg-muted/20 px-2.5 py-2 text-left transition-colors hover:bg-muted/50"
					onclick={t.open}
				>
					<span class="flex items-center gap-1.5 text-2xs text-muted-foreground">
						{#if t.tone}<span class="size-1.5 rounded-full" style="background:{t.tone}"></span>{/if}
						{t.label}
					</span>
					<span class="text-lg leading-none font-semibold tracking-tight tabular-nums">
						{t.count.toLocaleString()}
					</span>
					{#if t.detail}<span class="text-2xs text-muted-foreground">{t.detail}</span>{/if}
				</button>
			{/each}
		</div>
	{:else}
		<span class="text-sm text-muted-foreground">No signals</span>
	{/if}
</Cell>

<SignalSheet
	open={sheetOpen}
	onOpenChange={(o) => (sheetOpen = o)}
	title={sheet?.title ?? ''}
	rows={sheetRows}
/>
