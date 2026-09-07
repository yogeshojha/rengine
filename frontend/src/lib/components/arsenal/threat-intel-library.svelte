<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Biohazard from '@lucide/svelte/icons/biohazard';
	import CalendarX from '@lucide/svelte/icons/calendar-x';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Flame from '@lucide/svelte/icons/flame';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Swords from '@lucide/svelte/icons/swords';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Switch } from '$lib/components/ui/switch';
	import Hint from '$lib/components/hint.svelte';
	import CompositionBar, {
		type Segment
	} from '$lib/components/scans/results/overview/composition-bar.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SignalSheet, { type SheetRow } from '$lib/components/dashboard/signal-sheet.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import FeedCard from '$lib/components/threat-intel/feed-card.svelte';
	import SignalTile from '$lib/components/threat-intel/signal-tile.svelte';
	import { threatIntelApi } from '$lib/api/threat-intel';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import {
		BAND_FILL,
		ExploitSignal,
		BAND_LABELS,
		BAND_ORDER,
		SIGNAL_HELP,
		SIGNAL_ICONS,
		SIGNAL_LABELS
	} from '$lib/config/threat-intel';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import type { SignalFinding, ThreatIntelStatus } from '$lib/types/threat-intel';

	const POLL_MS = 4000;

	let status = $state<ThreatIntelStatus | null>(null);
	let loading = $state(true);
	let syncing = $state(false);
	let fetchedProjectId = $state<string | null>(null);
	let togglingAuto = $state(false);

	let projectId = $derived(projectsStore.activeProject?.id ?? null);

	let coverage = $derived(status?.coverage);
	let feeds = $derived(status?.feeds ?? []);
	let changes = $derived(status?.recent_changes ?? []);

	let bands = $derived<Segment[]>(
		BAND_ORDER.map((key) => ({
			key,
			label: BAND_LABELS[key],
			count: coverage?.bands?.[key] ?? 0,
			color: BAND_FILL[key],
			filter: ''
		})).filter((s) => s.count > 0)
	);

	let scored = $derived(coverage?.scored ?? 0);
	let autoSync = $derived(status?.auto_sync ?? true);

	let tiles = $derived(
		[
			{
				kind: ExploitSignal.KEV,
				icon: Flame,
				count: coverage?.kev ?? 0,
				label: 'Known exploited',
				detail: 'CISA confirms exploitation in the wild',
				tone: 'critical'
			},
			{
				kind: `${ExploitSignal.RANSOM_PATH},${ExploitSignal.RANSOMWARE}`,
				icon: Biohazard,
				count: coverage?.ransomware ?? 0,
				label: 'Used by ransomware',
				detail: 'Recorded in known ransomware campaigns',
				tone: 'critical'
			},
			{
				kind: ExploitSignal.OVERDUE,
				icon: CalendarX,
				count: coverage?.overdue ?? 0,
				label: 'Past the CISA deadline',
				detail: 'The federal remediation date has passed',
				tone: 'warning'
			},
			{
				kind: ExploitSignal.WEAPONISED,
				icon: Swords,
				count: coverage?.weaponised ?? 0,
				label: 'Public exploit available',
				detail: 'Working exploit code is published',
				tone: 'warning'
			},
			{
				kind: ExploitSignal.UNTESTABLE,
				icon: EyeOff,
				count: coverage?.untestable ?? 0,
				label: 'No check exists',
				detail: 'No scanner template covers these, so no scan can clear them',
				tone: 'info'
			}
		].filter((t) => t.count > 0)
	);

	async function load(id: string | null) {
		try {
			status = await threatIntelApi.status(id ?? undefined);
			fetchedProjectId = id;
		} catch {
			status = null;
		} finally {
			loading = false;
		}
	}

	async function toggleAuto(enabled: boolean) {
		togglingAuto = true;
		try {
			status = await threatIntelApi.setAutoSync(enabled, fetchedProjectId ?? undefined);
			toast.success(enabled ? 'Nightly download on' : 'Nightly download off', {
				description: enabled
					? 'Feeds refresh once a day and re-rank every finding.'
					: 'Nothing is downloaded until you press Refresh now.'
			});
		} catch {
			toast.error('Could not change the download setting');
		} finally {
			togglingAuto = false;
		}
	}

	async function sync() {
		syncing = true;
		try {
			const res = await threatIntelApi.sync();
			if (res.queued) {
				toast.success('Refreshing exploitation intelligence', {
					description: 'Every finding is re-scored when the download lands.'
				});
				setTimeout(() => load(fetchedProjectId), 2500);
			} else {
				toast.error(res.detail ?? 'The refresh could not be queued');
			}
		} catch {
			toast.error('The refresh could not be queued');
		} finally {
			syncing = false;
		}
	}

	$effect(() => {
		const id = projectId;
		if (id === fetchedProjectId && status) return;
		untrack(() => void load(id));
	});

	$effect(() => {
		if (!status?.syncing) return;
		const handle = setInterval(() => untrack(() => load(fetchedProjectId)), POLL_MS);
		return () => clearInterval(handle);
	});

	let sheetOpen = $state(false);
	let sheetKind = $state('');
	let sheetRows = $state<SheetRow[]>([]);

	async function openSignal(kind: string) {
		sheetKind = kind;
		sheetRows = [];
		sheetOpen = true;
		let findings: SignalFinding[] = [];
		try {
			findings = await threatIntelApi.signal(kind, fetchedProjectId ?? undefined);
		} catch {
			findings = [];
		}
		sheetRows = findings.map((f) => ({
			key: f.vulnerability_id,
			primary: f.matched_at || f.host || f.template_name,
			secondary: `${f.cve ? f.cve + ' · ' : ''}${f.template_name}`,
			meta: `${f.exploit_score}`,
			href: ROUTES.scanTab(f.scan_id, 'vulnerabilities', { q: `cve:${f.cve}` }),
			tone: f.exploit_score >= 80 ? 'bad' : f.exploit_score >= 50 ? 'warn' : undefined,
			group: f.target_value ?? undefined
		}));
	}
</script>

{#if loading}
	<div class="grid gap-4 sm:grid-cols-2">
		<Skeleton class="h-56" />
		<Skeleton class="h-56" />
	</div>
{:else if !status}
	<EmptyState
		icon={Flame}
		title="Exploitation intelligence is unavailable"
		description="The API did not answer. Check that the api service is running."
	/>
{:else}
	<div class="flex flex-col gap-6">
		<!-- the two feeds -->
		<Card.Root class="gap-0 py-0">
			<PanelHead
				title="Exploitation feeds"
				description={status.auto_sync
					? 'Downloaded nightly. No account, no API key, and they keep working offline.'
					: 'Automatic download is off. Nothing leaves this instance until you press Refresh now.'}
			>
				{#if status.last_applied_at}
					<span>Last applied {relativeTime(status.last_applied_at)}</span>
				{/if}
				<Hint
					text={status.auto_sync
						? 'reNgine downloads EPSS and the KEV catalog once a day'
						: 'No outbound request is made on a schedule'}
				>
					{#snippet child(props)}
						<label {...props} class="flex cursor-pointer items-center gap-2">
							<Switch
								checked={autoSync}
								disabled={togglingAuto}
								onCheckedChange={toggleAuto}
								aria-label="Download feeds automatically"
							/>
							<span class="whitespace-nowrap">Nightly download</span>
						</label>
					{/snippet}
				</Hint>
				<LoadingButton
					loading={syncing || status.syncing}
					loadingLabel="Refreshing"
					variant="outline"
					size="sm"
					onclick={sync}
				>
					<RefreshCw class="mr-1.5 size-3.5" />
					Refresh now
				</LoadingButton>
			</PanelHead>
			<div class="grid sm:grid-cols-2 sm:divide-x">
				{#each feeds as feed (feed.kind)}
					<div class="border-b last:border-b-0 sm:border-b-0">
						<FeedCard {feed} />
					</div>
				{/each}
			</div>
		</Card.Root>

		<!-- what the feeds bought you -->
		{#if coverage && coverage.findings > 0}
			<Card.Root class="gap-0 py-0">
				<PanelHead
					title="Your findings"
					description="Every finding you already hold, re-scored from the feeds. Nothing was rescanned."
				/>

				{#if scored > 0}
					<div class="flex flex-col gap-3 border-b px-5 py-4">
						<SectionHead
							title="Likelihood of exploitation"
							count="{scored} of {coverage.with_cve} scored"
						/>
						<CompositionBar
							segments={bands}
							total={scored}
							label="Findings by exploitation likelihood"
						/>
					</div>
				{/if}

				<div class="grid sm:grid-cols-2 sm:divide-x [&>*]:border-b [&>*:last-child]:border-b-0">
					{#each tiles as tile (tile.kind)}
						<SignalTile
							icon={tile.icon}
							count={tile.count}
							label={tile.label}
							detail={tile.detail}
							tone={tile.tone}
							onSelect={tile.count > 0 ? () => openSignal(tile.kind) : undefined}
						/>
					{/each}
				</div>
			</Card.Root>
		{/if}

		<!-- the change feed -->
		{#if changes.length}
			<Card.Root class="gap-0 py-0">
				<PanelHead
					title="Recent changes"
					description="Findings that earned a new exploitation signal, without a new scan."
				/>
				<ul class="divide-y">
					{#each changes.slice(0, 10) as change (change.vulnerability_id + change.change)}
						{@const Icon = SIGNAL_ICONS[change.change]}
						<li>
							<a
								class="flex items-start gap-3 px-5 py-3 transition-colors hover:bg-accent/40"
								href={ROUTES.scanTab(change.scan_id, 'vulnerabilities', {
									q: `cve:${change.cve}`
								})}
							>
								<span class="flex h-5 shrink-0 items-center text-muted-foreground">
									{#if Icon}<Icon class="size-3.5" />{/if}
								</span>
								<span class="flex min-w-0 flex-1 flex-col gap-0.5">
									<span class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
										<span class="text-sm leading-5 font-medium">
											{SIGNAL_LABELS[change.change] ?? change.change}
										</span>
										<Badge variant="outline" class="px-1 font-mono text-[10px] font-normal">
											{change.cve}
										</Badge>
									</span>
									<span class="truncate text-xs text-muted-foreground">
										{change.template_name}
										{#if change.target_value}· {change.target_value}{/if}
									</span>
								</span>
								<span class="flex h-5 shrink-0 items-center gap-2 text-xs text-muted-foreground">
									{#if change.changed_at}{relativeTime(change.changed_at)}{/if}
									<ArrowUpRight class="size-3.5" />
								</span>
							</a>
						</li>
					{/each}
				</ul>
			</Card.Root>
		{/if}

		<!-- the provider -->
		<Card.Root class="gap-0 py-0">
			<PanelHead
				title="vulnx"
				description="ProjectDiscovery's vulnerability index. Optional, cached, and rate-limit aware."
			>
				<span class="tabular-nums">{status.provider_cached} CVEs cached</span>
			</PanelHead>
			<div class="px-5 py-4 text-xs leading-relaxed text-muted-foreground">
				<p>
					The feeds above give every CVE a score. vulnx adds the story behind it: published exploits
					and their links, whether a scanner template exists at all, how many hosts on the internet
					run the affected software, and HackerOne activity.
				</p>
				<p class="mt-2">
					It is fetched on demand, once per CVE, and cached. Keyless works at 10 requests a minute;
					a free key raises that. Add one under
					<a class="underline hover:text-foreground" href={ROUTES.settings('api-keys')}>
						Settings → API keys
					</a>.
				</p>
			</div>
		</Card.Root>
	</div>
	<SignalSheet
		open={sheetOpen}
		onOpenChange={(v) => (sheetOpen = v)}
		title={SIGNAL_LABELS[sheetKind.split(',')[0]] ?? 'Findings'}
		description={SIGNAL_HELP[sheetKind.split(',')[0]] ?? ''}
		rows={sheetRows}
	/>
{/if}
