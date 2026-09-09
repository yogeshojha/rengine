<script lang="ts">
	import Lock from '@lucide/svelte/icons/lock';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import CalendarX from '@lucide/svelte/icons/calendar-x';
	import Mail from '@lucide/svelte/icons/mail';
	import Link2Off from '@lucide/svelte/icons/link-2-off';
	import Compass from '@lucide/svelte/icons/compass';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { toast } from 'svelte-sonner';
	import { SvelteSet } from 'svelte/reactivity';
	import Widget from './widget.svelte';
	import SignalSheet, { type SheetRow } from './signal-sheet.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { IconComponent } from '$lib/config/icons';
	import { MS_PER_DAY, relativeTime } from '$lib/utilities/dates';
	import type {
		DashboardCertSignal,
		DashboardDiscovery,
		DashboardOverview
	} from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		discovery: DashboardDiscovery | null;
		class?: string;
	}

	let { overview, discovery, class: className = '' }: Props = $props();

	type Tone = 'bad' | 'warn' | 'lead';
	interface Item {
		key: string;
		icon: IconComponent;
		tone: Tone;
		label: string;
		count: number;
		detail: string;
		open: () => void;
	}
	interface SheetState {
		kind?: 'discovery';
		title: string;
		description?: string;
		rows: SheetRow[];
	}

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const TONE: Record<Tone, string> = {
		bad: 'text-destructive',
		warn: 'text-warning',
		lead: 'text-info'
	};
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

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
	function certRows(signal: DashboardCertSignal): SheetRow[] {
		return signal.targets.map((t) => ({
			key: t.target_id,
			primary: t.target_value,
			meta: plural(t.count, 'host', 'hosts'),
			href: ROUTES.scanTab(t.scan_id, WEB.tab, { [WEB.queryParam]: signal.query })
		}));
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
			const on =
				d.sources.length > 1 ? plural(d.sources.length, 'target', 'targets') : source?.target_value;
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

	let items = $derived.by<Item[]>(() => {
		const out: Item[] = [];
		const certs = overview.certs;
		if (certs.expired.count > 0)
			out.push({
				key: 'cert-expired',
				icon: Lock,
				tone: 'bad',
				label: 'Expired certificates on live hosts',
				count: certs.expired.count,
				detail: `on ${plural(certs.expired.targets.length, 'target', 'targets')}`,
				open: () =>
					show({
						title: 'Expired certificates',
						description: 'Live hosts answering with a certificate past its expiry.',
						rows: certRows(certs.expired)
					})
			});
		if (certs.expiring.count > 0)
			out.push({
				key: 'cert-expiring',
				icon: CalendarClock,
				tone: 'warn',
				label: 'Certificates expiring within 30 days',
				count: certs.expiring.count,
				detail: `on ${plural(certs.expiring.targets.length, 'target', 'targets')}`,
				open: () =>
					show({
						title: 'Certificates expiring soon',
						description: 'Hosts whose certificate expires in the next 30 days.',
						rows: certRows(certs.expiring)
					})
			});
		if (overview.expiring.length)
			out.push({
				key: 'domains',
				icon: CalendarX,
				tone: 'warn',
				label: 'Domains expiring within 30 days',
				count: overview.expiring.length,
				detail: expiryText(overview.expiring[0].expires_at),
				open: () =>
					show({
						title: 'Domains expiring soon',
						description: 'Registrations reNgine saw an expiry date for in WHOIS.',
						rows: overview.expiring.map((t) => ({
							key: t.target_id,
							primary: t.target_value,
							meta: expiryText(t.expires_at),
							href: ROUTES.target(t.target_id, 'whois')
						}))
					})
			});
		const spoof = overview.signals.spoofable;
		if (spoof.count > 0)
			out.push({
				key: 'spoofable',
				icon: Mail,
				tone: 'warn',
				label: 'Domains that can be spoofed',
				count: spoof.count,
				detail: 'no SPF or DMARC policy',
				open: () =>
					show({
						title: 'Spoofable domains',
						description:
							'No SPF or DMARC record was found, so mail from the domain cannot be rejected.',
						rows: spoof.items.map((d) => ({
							key: d.target_id,
							primary: d.target_value,
							meta: d.reason,
							href: ROUTES.target(d.target_id, 'dns')
						}))
					})
			});
		const takeover = overview.signals.takeover;
		if (takeover.count > 0)
			out.push({
				key: 'takeover',
				icon: Link2Off,
				tone: 'bad',
				label: 'Takeover candidates',
				count: takeover.count,
				detail: 'dangling records on a provider',
				open: () =>
					show({
						title: 'Takeover candidates',
						description: 'Hostnames whose record points at a provider that no longer serves them.',
						rows: takeover.items.map((c) => ({
							key: c.name,
							primary: c.name,
							secondary: `${c.cname} · ${c.provider}`,
							meta: relativeTime(c.last_seen),
							href: ROUTES.target(c.target_id, 'web-assets')
						}))
					})
			});
		const leads = discovery?.domains.length ?? 0;
		if (leads > 0)
			out.push({
				key: 'leads',
				icon: Compass,
				tone: 'lead',
				label: 'Domains the estate vouches for',
				count: leads,
				detail: 'on your certificates, not yet targets',
				open: () =>
					show({
						kind: 'discovery',
						title: 'Untracked domains',
						description:
							'Registrable domains named on certificates the estate presents. Adding one starts tracking it.',
						rows: []
					})
			});
		return out;
	});
</script>

{#if items.length}
	<Widget
		title="Hygiene"
		description="Certificates, registrations, mail policy and dangling records"
		class={className}
	>
		<ul class="divide-y divide-border/60">
			{#each items as it (it.key)}
				<li>
					<button
						type="button"
						class="flex w-full items-center gap-3 px-5 py-2.5 text-left transition-colors hover:bg-muted/40"
						onclick={it.open}
					>
						<span class="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted/60">
							<it.icon class="size-3.5 {TONE[it.tone]}" />
						</span>
						<span class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-sm">{it.label}</span>
							<span class="truncate text-xs text-muted-foreground">{it.detail}</span>
						</span>
						<span class="text-base font-semibold tabular-nums {TONE[it.tone]}">
							{it.count.toLocaleString()}
						</span>
						<ChevronRight class="size-3.5 shrink-0 text-muted-foreground" />
					</button>
				</li>
			{/each}
		</ul>
	</Widget>

	<SignalSheet
		open={sheetOpen}
		onOpenChange={(o) => (sheetOpen = o)}
		title={sheet?.title ?? ''}
		description={sheet?.description}
		rows={sheetRows}
	/>
{/if}
