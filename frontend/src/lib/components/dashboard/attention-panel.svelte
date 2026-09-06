<script lang="ts" module>
	export type QueueFilter = 'all' | 'kev' | 'critical' | 'high' | 'new';
</script>

<script lang="ts">
	import Flame from '@lucide/svelte/icons/flame';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Plug from '@lucide/svelte/icons/plug';
	import Link2Off from '@lucide/svelte/icons/link-2-off';
	import Lock from '@lucide/svelte/icons/lock';
	import Mail from '@lucide/svelte/icons/mail';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Radar from '@lucide/svelte/icons/radar';
	import Clock from '@lucide/svelte/icons/clock';
	import Compass from '@lucide/svelte/icons/compass';
	import RadioTower from '@lucide/svelte/icons/radio-tower';
	import { toast } from 'svelte-sonner';
	import { SvelteSet } from 'svelte/reactivity';
	import * as Card from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import PanelHead from '$lib/components/panel-head.svelte';
	import SignalSheet, { type SheetAction, type SheetRow } from './signal-sheet.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { IconComponent } from '$lib/config/icons';
	import { formatShortDate, MS_PER_DAY, relativeTime } from '$lib/utilities/dates';
	import type {
		DashboardCertSignal,
		DashboardDiscovery,
		DashboardOverview,
		DashboardTargetCount
	} from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview | null;
		discovery: DashboardDiscovery | null;
		loading: boolean;
		onQueue: (filter: QueueFilter) => void;
		onScanTargets: (ids: string[]) => void;
		onSchedule: (ids: string[]) => void;
		onExposure: () => void;
	}

	let { overview, discovery, loading, onQueue, onScanTargets, onSchedule, onExposure }: Props =
		$props();

	type Tone = 'critical' | 'warning' | 'lead';
	interface Tile {
		key: string;
		tone: Tone;
		icon: IconComponent;
		count: number;
		label: string;
		detail?: string;
		open: () => void;
	}
	interface SheetState {
		kind?: 'discovery';
		title: string;
		description?: string;
		rows: SheetRow[];
		action?: SheetAction | null;
	}

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const TONE: Record<Tone, { label: string; rank: number; dot: string }> = {
		critical: { label: 'High', rank: 0, dot: 'bg-destructive' },
		warning: { label: 'Medium', rank: 1, dot: 'bg-warning' },
		lead: { label: 'Lead', rank: 2, dot: 'bg-info' }
	};
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
	const targets = (n: number) => plural(n, 'target', 'targets');

	let sheet = $state<SheetState | null>(null);
	let sheetOpen = $state(false);
	function show(state: SheetState) {
		sheet = state;
		sheetOpen = true;
	}

	function daysUntil(iso: string): number {
		return Math.round((new Date(iso).getTime() - Date.now()) / MS_PER_DAY);
	}
	function expiryText(iso: string): string {
		const days = daysUntil(iso);
		if (days < 0) return `expired ${plural(-days, 'day', 'days')} ago`;
		if (days === 0) return 'expires today';
		return `expires in ${plural(days, 'day', 'days')}`;
	}
	function countRows(
		items: DashboardTargetCount[],
		noun: [string, string],
		href: (t: DashboardTargetCount) => string
	): SheetRow[] {
		return items.map((t) => ({
			key: t.target_id,
			primary: t.target_value,
			meta: plural(t.count, noun[0], noun[1]),
			href: href(t)
		}));
	}
	function certRows(signal: DashboardCertSignal): SheetRow[] {
		return countRows(signal.targets, ['host', 'hosts'], (t) =>
			ROUTES.scanTab(t.scan_id, WEB.tab, { [WEB.queryParam]: signal.query })
		);
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
			toast.success(`${domain} added as a target`);
		} catch {
			toast.error(`${domain} could not be added`);
		} finally {
			pending = null;
		}
	}
	let discoveryRows = $derived.by<SheetRow[]>(() =>
		(discovery?.domains ?? []).map((d) => {
			const source = d.sources[0];
			const on = d.sources.length > 1 ? targets(d.sources.length) : source?.target_value;
			return {
				key: d.domain,
				primary: d.domain,
				secondary: `${plural(d.hostname_count, 'hostname', 'hostnames')} on certificates of ${on}${source?.seen_on ? ` · seen on ${source.seen_on}` : ''}`,
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

	let tiles = $derived.by<Tile[]>(() => {
		if (!overview) return [];
		const out: Tile[] = [];
		const risk = overview.risk;
		const sev = (key: string) => risk.by_severity.find((s) => s.severity === key)?.count ?? 0;
		const kevTargets = overview.targets.filter((t) => t.kev > 0).length;
		if (risk.kev > 0)
			out.push({
				key: 'kev',
				tone: 'critical',
				icon: Flame,
				count: risk.kev,
				label: 'Known exploited',
				detail: `Listed in CISA KEV on ${targets(kevTargets)}, fix first`,
				open: () => onQueue('kev')
			});
		const critical = sev('critical');
		const high = sev('high');
		if (critical > 0)
			out.push({
				key: 'critical',
				tone: 'critical',
				icon: ShieldAlert,
				count: critical,
				label: critical === 1 ? 'Critical finding' : 'Critical findings',
				detail: high ? `${high.toLocaleString()} high beside them` : undefined,
				open: () => onQueue('critical')
			});
		else if (high > 0)
			out.push({
				key: 'high',
				tone: 'critical',
				icon: ShieldAlert,
				count: high,
				label: high === 1 ? 'High finding' : 'High findings',
				open: () => onQueue('high')
			});

		const takeover = overview.signals.takeover;
		if (takeover.count > 0)
			out.push({
				key: 'takeover',
				tone: 'critical',
				icon: Link2Off,
				count: takeover.count,
				label: takeover.count === 1 ? 'Takeover candidate' : 'Takeover candidates',
				detail: 'Dangling CNAMEs pointing at unclaimed providers',
				open: () =>
					show({
						title: 'Takeover candidates',
						description: 'Hostnames whose CNAME points at a provider nothing answers from',
						rows: takeover.items.map((c) => ({
							key: c.name,
							primary: c.name,
							secondary: `${c.cname} · ${c.provider}`,
							meta: relativeTime(c.last_seen),
							href: ROUTES.target(c.target_id)
						}))
					})
			});

		const expired = overview.certs.expired;
		if (expired.count > 0)
			out.push({
				key: 'cert-expired',
				tone: 'critical',
				icon: Lock,
				count: expired.count,
				label: expired.count === 1 ? 'Expired certificate' : 'Expired certificates',
				detail: `Live hosts still serving them on ${targets(expired.targets.length)}`,
				open: () =>
					show({
						title: 'Expired certificates',
						description: 'Live hosts whose certificate has passed its expiry date',
						rows: certRows(expired)
					})
			});

		const sensitiveTotal = overview.sensitive.reduce((n, s) => n + s.count, 0);
		if (sensitiveTotal > 0)
			out.push({
				key: 'sensitive',
				tone: 'warning',
				icon: Plug,
				count: sensitiveTotal,
				label: sensitiveTotal === 1 ? 'Sensitive service' : 'Sensitive services',
				detail: `Databases, remote access and admin ports on ${targets(overview.sensitive.length)}`,
				open: onExposure
			});

		const expiringCerts = overview.certs.expiring;
		if (expiringCerts.count > 0)
			out.push({
				key: 'cert-expiring',
				tone: 'warning',
				icon: Lock,
				count: expiringCerts.count,
				label: expiringCerts.count === 1 ? 'Certificate expiring' : 'Certificates expiring',
				detail: `Within 30 days on ${targets(expiringCerts.targets.length)}`,
				open: () =>
					show({
						title: 'Certificates expiring',
						description: 'Hosts whose certificate expires within the next 30 days',
						rows: certRows(expiringCerts)
					})
			});

		const spoofable = overview.signals.spoofable;
		if (spoofable.count > 0)
			out.push({
				key: 'spoofable',
				tone: 'warning',
				icon: Mail,
				count: spoofable.count,
				label: spoofable.count === 1 ? 'Spoofable mail domain' : 'Spoofable mail domains',
				detail: 'Mail configured without an effective sender policy',
				open: () =>
					show({
						title: 'Spoofable mail domains',
						description: 'Domains with MX records but no effective SPF policy',
						rows: spoofable.items.map((d) => ({
							key: d.target_id,
							primary: d.target_value,
							secondary: d.reason,
							href: ROUTES.target(d.target_id)
						}))
					})
			});

		if (overview.expiring.length > 0)
			out.push({
				key: 'expiring',
				tone: 'warning',
				icon: CalendarClock,
				count: overview.expiring.length,
				label: overview.expiring.length === 1 ? 'Domain expiring' : 'Domains expiring',
				detail: 'Registration ends within 30 days',
				open: () =>
					show({
						title: 'Domains expiring',
						description: 'Registrations that end within the next 30 days',
						rows: overview.expiring.map((d) => ({
							key: d.target_id,
							primary: d.target_value,
							secondary: `Registered until ${formatShortDate(d.expires_at)}`,
							meta: expiryText(d.expires_at),
							tone: daysUntil(d.expires_at) <= 7 ? 'bad' : 'warn',
							href: ROUTES.target(d.target_id)
						}))
					})
			});

		if (overview.failed_runs.length > 0)
			out.push({
				key: 'failed',
				tone: 'warning',
				icon: CircleX,
				count: overview.failed_runs.length,
				label: overview.failed_runs.length === 1 ? 'Failed run' : 'Failed runs',
				detail: `The latest run failed on ${targets(overview.failed_runs.length)}`,
				open: () =>
					show({
						title: 'Failed runs',
						description: 'Targets whose most recent run did not finish',
						rows: overview.failed_runs.map((r) => ({
							key: r.scan_id,
							primary: r.target_value,
							secondary: `${r.engine_name}${r.error ? ` · ${r.error}` : ''}`,
							meta: relativeTime(r.at),
							href: ROUTES.scan(r.scan_id)
						}))
					})
			});

		if (overview.never_scanned.length > 0)
			out.push({
				key: 'never',
				tone: 'warning',
				icon: Radar,
				count: overview.never_scanned.length,
				label: 'Never scanned',
				detail: 'No run has covered these targets',
				open: () =>
					show({
						title: 'Never scanned',
						description: 'Targets without a single run',
						rows: overview.never_scanned.map((t) => ({
							key: t.target_id,
							primary: t.target_value,
							secondary: t.target_type.replace('_', ' ').toUpperCase(),
							href: ROUTES.target(t.target_id)
						})),
						action: {
							label: 'Scan these targets',
							onClick: () => {
								sheetOpen = false;
								onScanTargets(overview.never_scanned.map((t) => t.target_id));
							}
						}
					})
			});

		if (overview.stale.length > 0)
			out.push({
				key: 'stale',
				tone: 'warning',
				icon: Clock,
				count: overview.stale.length,
				label: 'Not scanned in 30 days',
				detail: 'The last run is older than a month',
				open: () =>
					show({
						title: 'Not scanned in 30 days',
						description: 'Targets whose most recent run is older than a month',
						rows: overview.stale.map((t) => ({
							key: t.target_id,
							primary: t.target_value,
							meta: t.last_scanned_at ? `last run ${relativeTime(t.last_scanned_at)}` : undefined,
							href: ROUTES.target(t.target_id)
						})),
						action: {
							label: 'Scan these targets',
							onClick: () => {
								sheetOpen = false;
								onScanTargets(overview.stale.map((t) => t.target_id));
							}
						}
					})
			});

		const unmonitored = overview.targets.filter((t) => !t.monitored);
		if (unmonitored.length > 0 && overview.targets_scanned > 0)
			out.push({
				key: 'unmonitored',
				tone: 'warning',
				icon: RadioTower,
				count: unmonitored.length,
				label: 'Not monitored',
				detail: 'No schedule re-scans these targets',
				open: () =>
					show({
						title: 'Not monitored',
						description: 'Targets that only change when someone starts a scan by hand',
						rows: unmonitored.map((t) => ({
							key: t.id,
							primary: t.value,
							secondary: t.last_scan_at
								? `last run ${relativeTime(t.last_scan_at)}`
								: 'never scanned',
							href: ROUTES.target(t.id)
						})),
						action: {
							label: 'Schedule scans',
							onClick: () => {
								sheetOpen = false;
								onSchedule(unmonitored.map((t) => t.id));
							}
						}
					})
			});

		const leads = discovery?.domains.length ?? 0;
		if (leads > 0)
			out.push({
				key: 'discovery',
				tone: 'lead',
				icon: Compass,
				count: leads,
				label: leads === 1 ? 'Untracked domain' : 'Untracked domains',
				detail: 'Named on certificates this estate serves, not yet a target',
				open: () =>
					show({
						kind: 'discovery',
						title: 'Untracked domains',
						description:
							"Registrable domains the estate's own certificates vouch for that no target covers",
						rows: []
					})
			});

		return out.sort((a, b) => TONE[a.tone].rank - TONE[b.tone].rank || b.count - a.count);
	});
	let high = $derived(tiles.filter((t) => t.tone === 'critical').length);
	let medium = $derived(tiles.filter((t) => t.tone === 'warning').length);
	let leads = $derived(tiles.filter((t) => t.tone === 'lead').length);
</script>

{#if tiles.length || (loading && !overview)}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Needs attention">
			{#if high > 0}
				<span class="flex items-center gap-1.5 tabular-nums">
					<span class="size-1.5 rounded-full bg-destructive" aria-hidden="true"></span>
					{high} high
				</span>
			{/if}
			{#if medium > 0}
				<span class="flex items-center gap-1.5 tabular-nums">
					<span class="size-1.5 rounded-full bg-warning" aria-hidden="true"></span>
					{medium} medium
				</span>
			{/if}
			{#if leads > 0}
				<span class="flex items-center gap-1.5 tabular-nums">
					<span class="size-1.5 rounded-full bg-info" aria-hidden="true"></span>
					{leads === 1 ? '1 lead' : `${leads} leads`}
				</span>
			{/if}
		</PanelHead>

		<div class="p-5">
			{#if !tiles.length}
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{#each Array(4) as _, i (i)}
						<Skeleton class="h-28 w-full rounded-lg" />
					{/each}
				</div>
			{:else}
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{#each tiles as t (t.key)}
						{@const Icon = t.icon}
						{@const tone = TONE[t.tone]}
						<button
							type="button"
							class="group flex cursor-pointer flex-col gap-3 rounded-lg border border-border/70 p-4 text-left transition-colors hover:border-primary/40 hover:bg-accent/40"
							onclick={t.open}
						>
							<span class="flex h-6 items-center justify-between gap-2 text-[11px]">
								<span class="flex items-center gap-1.5 text-muted-foreground">
									<span class="size-1.5 rounded-full {tone.dot}" aria-hidden="true"></span>
									{tone.label}
								</span>
								<Icon class="size-3.5 text-muted-foreground/70" />
							</span>
							<span class="text-2xl leading-none font-semibold tracking-tight tabular-nums">
								{t.count.toLocaleString()}
							</span>
							<span class="flex flex-col gap-0.5">
								<span
									class="text-sm leading-5 font-medium transition-colors group-hover:text-foreground"
								>
									{t.label}
								</span>
								{#if t.detail}
									<span class="line-clamp-2 text-xs leading-4 text-muted-foreground">
										{t.detail}
									</span>
								{/if}
							</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</Card.Root>
{/if}

{#if sheet}
	<SignalSheet
		open={sheetOpen}
		onOpenChange={(v) => (sheetOpen = v)}
		title={sheet.title}
		description={sheet.description}
		rows={sheetRows}
		action={sheet.action ?? null}
	/>
{/if}
