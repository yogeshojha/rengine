<script lang="ts">
	import { REVEAL_SM, REVEAL, rowPadding } from '$lib/components/scans/results/table/columns';
	import { toast } from 'svelte-sonner';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Copy from '@lucide/svelte/icons/copy';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Filter from '@lucide/svelte/icons/filter';
	import Flame from '@lucide/svelte/icons/flame';
	import Globe from '@lucide/svelte/icons/globe';
	import SquareKanban from '@lucide/svelte/icons/square-kanban';
	import Terminal from '@lucide/svelte/icons/terminal';
	import TicketChip from '$lib/components/issue-trackers/ticket-chip.svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import SignalChip from '$lib/components/threat-intel/signal-chip.svelte';
	import HighlightText from '../../table/highlight-text.svelte';
	import TargetCell from '../../table/target-cell.svelte';
	import CountryFlag from '../../country-flag.svelte';
	import CorroborationBadge from '../corroboration-badge.svelte';
	import PeekCard from './peek-card.svelte';
	import FindingBrief from './finding-brief.svelte';
	import { FCOL, NARROW } from './columns';
	import { findingPrefs } from './prefs.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { EVIDENCE_HELP, EVIDENCE_LABELS, Evidence, evidenceToken } from '$lib/config/evidence';
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import { ExploitSignal, exploitTone } from '$lib/config/threat-intel';
	import {
		EPSS_HIGH,
		SEVERITY_CHIP,
		SEVERITY_LABELS,
		SEVERITY_ORDER,
		SUPPRESSED_STATES,
		VULN_STATE_KEYS,
		VULN_STATE_LABELS,
		VulnState
	} from '$lib/config/vulnerabilities';
	import { stopProp } from '$lib/utilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import { exactToken, excludeToken, filterToken } from '$lib/utilities/scan-insights';
	import { openExternal } from '$lib/utilities/links';
	import {
		epssPercent,
		locationLabel,
		originLabel,
		type VulnerabilityRead
	} from '$lib/utilities/vulns';

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const ROW_SIGNALS: string[] = [
		ExploitSignal.RANSOM_PATH,
		ExploitSignal.FRESH_EXPLOIT,
		ExploitSignal.RANSOMWARE,
		ExploitSignal.OVERDUE
	];

	interface Props {
		v: VulnerabilityRead;
		index: number;
		projectId: string;
		scanId: string;
		projectWide: boolean;
		term: string;
		compact: boolean;
		expanded: boolean;
		focused: boolean;
		selected: boolean;
		checked: boolean;
		onToggle: () => void;
		onCheck: () => void;
		onFocus: () => void;
		onOpen: (v: VulnerabilityRead) => void;
		onFilter: (token: string) => void;
		onTab: (tab: ResultTab, filter: string) => void;
		onTriage: (v: VulnerabilityRead, state: string) => void;
		onRescan: (v: VulnerabilityRead) => void;
		onFileIssue?: (v: VulnerabilityRead) => void;
		showIssue?: boolean;
	}

	let {
		v,
		index,
		projectId,
		scanId,
		projectWide,
		term,
		compact,
		expanded,
		focused,
		selected,
		checked,
		onToggle,
		onCheck,
		onFocus,
		onOpen,
		onFilter,
		onTab,
		onTriage,
		onRescan,
		onFileIssue,
		showIssue = false
	}: Props = $props();

	let chip = $derived(SEVERITY_CHIP[v.severity] ?? SEVERITY_CHIP.unknown);
	let suppressed = $derived(SUPPRESSED_STATES.includes(v.state));
	let asset = $derived(v.asset);
	let path = $derived(locationLabel(v));
	let origin = $derived(originLabel(v));
	let prefix = $derived(path.startsWith('/') ? origin : '');
	let signals = $derived((v.intel_kinds ?? []).filter((k) => ROW_SIGNALS.includes(k)).slice(0, 2));
	let onHost = $derived(
		SEVERITY_ORDER.map((s) => ({ sev: s, n: v.host_findings?.[s] ?? 0 })).filter((c) => c.n > 0)
	);
	let hostTotal = $derived(onHost.reduce((a, c) => a + c.n, 0));
	let others = $derived(Math.max(0, v.host_count - 1));
	let likely = $derived((v.epss_score ?? 0) >= EPSS_HIGH);
	let hostToken = $derived(v.host ? exactToken('host', v.host) : '');
	let templateToken = $derived(exactToken('template', v.template_id));

	function pivot(e: Event, token: string) {
		stopProp(e);
		onFilter(token);
	}

	async function copy(text: string) {
		if (await writeClipboard(text)) toast.success('Copied');
	}
</script>

<div
	class="group relative border-b border-border/60 transition-colors
		{checked || selected ? 'bg-primary/5' : focused || expanded ? 'bg-muted/30' : ''}"
	role="none"
>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="flex cursor-pointer items-center gap-3 px-4 hover:bg-muted/30 {rowPadding(
			compact ? 'compact' : 'cozy'
		)}"
		role="row"
		tabindex="-1"
		data-vuln-row-index={index}
		onclick={onToggle}
		onmouseenter={onFocus}
	>
		<!-- svelte-ignore a11y_interactive_supports_focus -->
		<div class="{FCOL.select} h-6" role="cell" onclick={stopProp}>
			<Checkbox
				{checked}
				onCheckedChange={onCheck}
				aria-label="Select {v.template_name}"
				class="transition-opacity {checked ? '' : REVEAL_SM}"
			/>
		</div>

		<div class="{FCOL.severity} flex flex-col items-start gap-1" role="cell">
			<button
				type="button"
				class="inline-flex h-6 w-full items-center justify-center rounded-md px-1.5 text-2xs font-semibold tracking-wide uppercase focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {chip.chip} {suppressed
					? 'opacity-50'
					: ''}"
				aria-label="Filter to {SEVERITY_LABELS[v.severity] ?? v.severity}"
				onclick={(e) => pivot(e, exactToken('severity', v.severity))}
			>
				{SEVERITY_LABELS[v.severity] ?? v.severity}
			</button>
			{#if v.cvss_score != null}
				<Hint text="CVSS base score">
					{#snippet child(props)}
						<span
							{...props}
							class="w-full text-center font-mono text-2xs text-muted-foreground tabular-nums"
						>
							{v.cvss_score?.toFixed(1)}
						</span>
					{/snippet}
				</Hint>
			{/if}
		</div>

		<div class="{FCOL.finding} flex flex-col gap-0.5" role="cell">
			<div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
				<button
					type="button"
					class="min-w-0 text-left text-sm leading-6 font-medium wrap-anywhere hover:text-primary {suppressed
						? 'text-muted-foreground line-through decoration-muted-foreground/40'
						: ''}"
					onclick={(e) => {
						stopProp(e);
						onOpen(v);
					}}
				>
					<HighlightText text={v.template_name} {term} />
				</button>
				{#if v.is_new}
					<button
						type="button"
						class="rounded bg-foreground px-1 text-2xs font-semibold text-background"
						onclick={(e) => pivot(e, 'is:new')}>New</button
					>
				{/if}
				{#if v.is_kev}
					<Hint text="Listed in CISA KEV">
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="inline-flex items-center gap-0.5 rounded bg-destructive/10 px-1 text-2xs font-semibold text-destructive"
								onclick={(e) => pivot(e, 'is:kev')}
							>
								<Flame class="size-2.5" /> KEV
							</button>
						{/snippet}
					</Hint>
				{/if}
				{#if v.evidence === Evidence.PROVEN}
					<Hint text={EVIDENCE_HELP[Evidence.PROVEN]}>
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="rounded px-1 text-2xs font-semibold ring-1 ring-foreground/40 ring-inset {findingPrefs.shows(
									'evidence'
								)
									? NARROW.evidence
									: ''}"
								onclick={(e) => pivot(e, evidenceToken(Evidence.PROVEN))}
								>{EVIDENCE_LABELS[Evidence.PROVEN]}</button
							>
						{/snippet}
					</Hint>
				{/if}
				{#each signals as kind (kind)}
					<SignalChip {kind} onFilter={(t) => onFilter(t)} />
				{/each}
				<CorroborationBadge
					peers={v.corroborated_by}
					scanner={v.scanner}
					onFilter={(t) => onFilter(t)}
				/>
			</div>
			<div class="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-2xs">
				{#if projectWide && v.target_value}
					<button
						type="button"
						class="font-medium text-foreground/80 hover:text-primary {NARROW.target}"
						onclick={(e) => pivot(e, exactToken('target', v.target_value ?? ''))}
						>{v.target_value}</button
					>
					<span class="text-muted-foreground/50 {NARROW.target}">·</span>
				{/if}
				<button
					type="button"
					class="font-mono text-muted-foreground hover:text-foreground"
					onclick={(e) => pivot(e, templateToken)}
				>
					<HighlightText text={v.template_id} {term} />
				</button>
				<span class="text-muted-foreground/50">·</span>
				<Hint text={v.matched_at}>
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="min-w-0 truncate text-left font-mono text-foreground/80 hover:text-primary"
							onclick={(e) => pivot(e, filterToken('location', path))}
						>
							<span class={NARROW.origin}>{prefix}</span><HighlightText text={path} {term} />
						</button>
					{/snippet}
				</Hint>
				<span class="flex h-5 shrink-0 items-center">
					<CopyButton value={v.matched_at} class="shrink-0 transition-opacity {REVEAL}" />
				</span>
			</div>
			{#if hostTotal > 1}
				<div class="flex items-center gap-1 text-2xs text-muted-foreground {NARROW.related}">
					{hostTotal} on this {WEB.noun}{others ? ` · same check on ${others} more` : ''}
				</div>
			{/if}
			{#if v.state !== VulnState.OPEN}
				<div class="text-2xs text-muted-foreground {NARROW.review}">
					{VULN_STATE_LABELS[v.state] ?? v.state}
				</div>
			{/if}
		</div>

		{#if projectWide}
			<div class="{FCOL.target} h-6 items-center" role="cell">
				<TargetCell value={v.target_value} {onFilter} />
			</div>
		{/if}

		{#if findingPrefs.shows('asset')}
			<div class="{FCOL.asset} min-w-0 flex-col gap-0.5" role="cell">
				{#if v.host}
					<div class="flex h-6 min-w-0 items-center gap-1.5">
						{#if asset?.status_code != null}
							<span
								class="shrink-0 font-mono text-xs tabular-nums {httpStatusTextClass(
									asset.status_code
								)}">{asset.status_code}</span
							>
						{/if}
						<PeekCard
							{projectId}
							{scanId}
							q={hostToken}
							title="{hostTotal} open on {v.host}"
							total={hostTotal}
							line={(f) => ({ main: f.template_name, sub: locationLabel(f) })}
							onPick={onOpen}
						>
							{#snippet trigger(props)}
								<button
									{...props}
									type="button"
									class="min-w-0 truncate font-mono text-xs hover:text-primary"
									onclick={(e) => pivot(e, hostToken)}
								>
									<HighlightText text={v.host ?? ''} {term} />
								</button>
							{/snippet}
							{#snippet footer()}
								<button
									type="button"
									class="text-primary hover:text-primary/80"
									onclick={() => onFilter(hostToken)}
								>
									Filter to this {WEB.noun}
								</button>
								<button
									type="button"
									class="text-primary hover:text-primary/80"
									onclick={() => onTab(WEB.tab, hostToken)}
								>
									Open in {WEB.nounPlural}
								</button>
							{/snippet}
						</PeekCard>
					</div>
					<div class="flex min-w-0 items-center gap-1.5 text-2xs text-muted-foreground">
						{#if asset?.title}
							<span class="truncate">{asset.title}</span>
						{:else if v.ip}
							<span class="font-mono">{v.ip}</span>
						{/if}
						{#if asset?.asn_org}
							<span class="truncate">· {asset.asn_org}</span>
						{/if}
						{#if asset?.country}
							<CountryFlag code={asset.country} class="shrink-0" />
						{/if}
						{#if asset?.is_cdn}
							<span class="shrink-0 rounded border border-border px-1"
								>{asset.cdn_name ?? 'CDN'}</span
							>
						{/if}
					</div>
				{:else}
					<span class="text-xs leading-6 text-muted-foreground">{origin || '—'}</span>
				{/if}
			</div>
		{/if}

		{#if findingPrefs.shows('related')}
			<div class="{FCOL.related} min-w-0 flex-col gap-0.5" role="cell">
				{#if v.host && hostTotal > 1}
					<Hint text={onHost.map((c) => `${c.n} ${SEVERITY_LABELS[c.sev] ?? c.sev}`).join(' · ')}>
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="flex h-6 w-fit items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
								aria-label="{hostTotal} open findings on {v.host}"
								onclick={(e) => pivot(e, hostToken)}
							>
								<span class="flex items-center gap-0.5">
									{#each onHost as c (c.sev)}
										<span class="size-1.5 rounded-full {SEVERITY_CHIP[c.sev].edge}"></span>
									{/each}
								</span>
								<span class="tabular-nums">{hostTotal} on this {WEB.noun}</span>
							</button>
						{/snippet}
					</Hint>
				{:else}
					<span class="text-xs leading-6 text-muted-foreground"
						>{v.host ? `Only finding on this ${WEB.noun}` : '—'}</span
					>
				{/if}
				{#if others}
					<PeekCard
						{projectId}
						{scanId}
						q={templateToken}
						title="{v.template_name} on {v.host_count} {WEB.nounPlural}"
						total={others}
						exclude={v.id}
						line={(f) => ({ main: f.host ?? originLabel(f), sub: locationLabel(f) })}
						onPick={onOpen}
					>
						{#snippet trigger(props)}
							<button
								{...props}
								type="button"
								class="w-fit text-left text-2xs text-muted-foreground hover:text-foreground"
								onclick={(e) => pivot(e, templateToken)}
							>
								Same check on {others} more
							</button>
						{/snippet}
					</PeekCard>
				{:else if v.replays}
					<span class="text-2xs text-muted-foreground">
						Reproduced on {v.replays} equivalent
					</span>
				{/if}
			</div>
		{/if}

		{#if findingPrefs.shows('risk')}
			<div class="{FCOL.risk} min-w-0 items-start gap-2" role="cell">
				<div class="flex min-w-0 flex-col gap-0.5">
					{#if v.cve_ids.length}
						<a
							href={ROUTES.cve(v.cve_ids[0])}
							class="h-6 truncate font-mono text-xs leading-6 hover:text-primary"
							onclick={stopProp}
						>
							{v.cve_ids[0]}{v.cve_ids.length > 1 ? ` +${v.cve_ids.length - 1}` : ''}
						</a>
					{/if}
					{#if v.exploit_score > 0}
						<Hint text="Exploitation rank out of 100">
							{#snippet child(props)}
								<button
									{...props}
									type="button"
									class="w-fit text-left font-mono text-2xs tabular-nums hover:text-primary"
									onclick={(e) => pivot(e, `exploit:>=${Math.max(10, v.exploit_score - 10)}`)}
								>
									<span class="text-muted-foreground">Rank</span>
									<span class="font-semibold" style="color:{exploitTone(v.exploit_score)}"
										>{v.exploit_score}</span
									>
								</button>
							{/snippet}
						</Hint>
					{/if}
					{#if v.epss_score != null}
						<Hint text="Probability of exploitation in the next 30 days">
							{#snippet child(props)}
								<span
									{...props}
									class="font-mono text-2xs tabular-nums {likely
										? 'font-semibold text-destructive'
										: 'text-muted-foreground'}"
								>
									EPSS {epssPercent(v.epss_score)}
								</span>
							{/snippet}
						</Hint>
					{/if}
					{#if !v.cve_ids.length && v.epss_score == null && v.exploit_score <= 0}
						<span class="text-xs leading-6 text-muted-foreground">—</span>
					{/if}
				</div>
			</div>
		{/if}

		{#if findingPrefs.shows('evidence')}
			<!-- svelte-ignore a11y_interactive_supports_focus -->
			<div class="{FCOL.evidence} h-6 items-center" role="cell" onclick={stopProp}>
				<EvidenceMark evidence={v.evidence} showLabel onFilter={(t) => onFilter(t)} />
			</div>
		{/if}

		{#if findingPrefs.shows('review')}
			<!-- svelte-ignore a11y_interactive_supports_focus -->
			<div class="{FCOL.review} h-6 items-center" role="cell" onclick={stopProp}>
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<button
								{...props}
								type="button"
								class="inline-flex h-6 items-center gap-1.5 rounded-md px-1.5 text-xs hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {v.state ===
								VulnState.OPEN
									? 'text-muted-foreground'
									: ''}"
								aria-label="Review state: {VULN_STATE_LABELS[v.state] ?? v.state}"
							>
								<span
									class="size-2 rounded-full {v.state === VulnState.CONFIRMED
										? 'bg-destructive'
										: v.state === VulnState.OPEN
											? 'border border-muted-foreground/60'
											: 'bg-muted-foreground/50'}"
								></span>
								{VULN_STATE_LABELS[v.state] ?? v.state}
							</button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="start" class="w-48">
						<DropdownMenu.RadioGroup value={v.state} onValueChange={(s) => onTriage(v, s)}>
							{#each Object.entries(VULN_STATE_LABELS) as [value, label] (value)}
								<DropdownMenu.RadioItem {value}>
									{label}
									<DropdownMenu.Shortcut>{VULN_STATE_KEYS[value]}</DropdownMenu.Shortcut>
								</DropdownMenu.RadioItem>
							{/each}
						</DropdownMenu.RadioGroup>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</div>
		{/if}

		{#if showIssue}
			<!-- svelte-ignore a11y_interactive_supports_focus -->
			<div class="{FCOL.issue} min-h-6 flex-col items-start" role="cell" onclick={stopProp}>
				{#each v.tickets ?? [] as ticket (ticket.issue_id)}
					<TicketChip
						state={ticket.state}
						externalKey={ticket.external_key}
						url={ticket.url}
						remoteStatus={ticket.remote_status}
						remoteCategory={ticket.remote_category}
						error={ticket.error}
						trackerName={ticket.tracker_name}
						compact
					/>
				{/each}
			</div>
		{/if}

		{#if findingPrefs.shows('seen')}
			<div
				class="{FCOL.seen} h-6 items-center text-xs text-muted-foreground tabular-nums"
				role="cell"
			>
				<Hint text={formatDateTime(v.discovered_at)}>
					{#snippet child(props)}
						<span {...props}>{relativeTime(v.discovered_at)}</span>
					{/snippet}
				</Hint>
			</div>
		{/if}

		<!-- svelte-ignore a11y_interactive_supports_focus -->
		<div class="{FCOL.actions} items-center gap-0.5" role="cell" onclick={stopProp}>
			<Button
				variant="ghost"
				size="icon"
				class="size-7"
				aria-label={expanded ? 'Collapse finding brief' : 'Expand finding brief'}
				aria-expanded={expanded}
				onclick={onToggle}
			>
				<ChevronDown class="size-4 transition-transform {expanded ? 'rotate-180' : ''}" />
			</Button>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="ghost" size="icon" class="size-7">
							<Ellipsis class="size-4" />
							<span class="sr-only">Actions for {v.template_name}</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-56">
					<DropdownMenu.Item onclick={() => onOpen(v)}>Open finding</DropdownMenu.Item>
					{#if v.url}
						<DropdownMenu.Item onclick={() => openExternal(v.matched_at)}>
							<ExternalLink class="size-3.5" /> Open location
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Item onclick={() => copy(v.matched_at)}>
						<Copy class="size-3.5" /> Copy location
					</DropdownMenu.Item>
					{#if v.curl_command}
						<DropdownMenu.Item onclick={() => copy(v.curl_command ?? '')}>
							<Terminal class="size-3.5" /> Copy curl command
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={() => onFilter(templateToken)}>
						<Filter class="size-3.5" /> All findings from this check
					</DropdownMenu.Item>
					{#if v.host}
						<DropdownMenu.Item onclick={() => onFilter(hostToken)}>
							<Filter class="size-3.5" /> All findings on this {WEB.noun}
						</DropdownMenu.Item>
						<DropdownMenu.Item onclick={() => onTab(WEB.tab, hostToken)}>
							<Globe class="size-3.5" /> Open in {WEB.nounPlural}
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Item onclick={() => onRescan(v)}>Rescan this finding</DropdownMenu.Item>
					{#if onFileIssue && !v.tickets?.length}
						<DropdownMenu.Item onclick={() => onFileIssue(v)}>
							<SquareKanban class="size-3.5" /> File issue
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={() => onFilter(excludeToken('template', v.template_id))}>
						<EyeOff class="size-3.5" />
						<span class="truncate">Hide {v.template_name}</span>
					</DropdownMenu.Item>
					{#if v.host}
						<DropdownMenu.Item onclick={() => onFilter(excludeToken('host', v.host ?? ''))}>
							<EyeOff class="size-3.5" />
							<span class="truncate">Hide {v.host}</span>
						</DropdownMenu.Item>
					{/if}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>

	{#if expanded}
		<div role="row">
			<div class="px-4 pt-1 pb-4 @xl/findings:pl-12" role="cell">
				<FindingBrief {v} {projectId} {scanId} {onOpen} {onFilter} {onTab} {onTriage} {onRescan} />
			</div>
		</div>
	{/if}
</div>
