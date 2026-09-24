<script lang="ts">
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Flame from '@lucide/svelte/icons/flame';
	import PanelRightOpen from '@lucide/svelte/icons/panel-right-open';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CodeBlock from '$lib/components/code-block.svelte';
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import CountryFlag from '../../country-flag.svelte';
	import ScreenshotThumb from '../../screenshot-thumb.svelte';
	import TechIcon from '../../tech-icon.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import {
		CORROBORATION_BASIS_LABELS,
		SEVERITY_CHIP,
		SEVERITY_ORDER,
		VULN_STATE_LABELS,
		VulnState
	} from '$lib/config/vulnerabilities';
	import { formatShortDate } from '$lib/utilities/dates';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import { exactToken } from '$lib/utilities/scan-insights';
	import { epssPercent, locationLabel, type VulnerabilityRead } from '$lib/utilities/vulns';
	import { BRIEF_TABS, BRIEF_TAB_LABELS, findingPrefs, type BriefTab } from './prefs.svelte';
	import AssetTiles from './asset-tiles.svelte';
	import FindingList from './finding-list.svelte';

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const IPS = SURFACE[SurfaceDimension.IPS];

	interface Props {
		v: VulnerabilityRead;
		projectId: string;
		scanId: string;
		onOpen: (v: VulnerabilityRead) => void;
		onFilter: (token: string) => void;
		onTab: (tab: ResultTab, filter: string) => void;
		onTriage: (v: VulnerabilityRead, state: string) => void;
		onRescan: (v: VulnerabilityRead) => void;
	}

	let { v, projectId, scanId, onOpen, onFilter, onTab, onTriage, onRescan }: Props = $props();

	let asset = $derived(v.asset);
	let hostToken = $derived(v.host ? exactToken('host', v.host) : '');
	let ipToken = $derived(v.ip ? exactToken('ip', v.ip) : '');
	let templateToken = $derived(exactToken('template', v.template_id));
	let hostTotal = $derived(Object.values(v.host_findings ?? {}).reduce((a, n) => a + n, 0));

	let checkTotal = $state(0);
</script>

<Tabs.Root
	value={findingPrefs.tab}
	onValueChange={(t) => (findingPrefs.tab = t as BriefTab)}
	class="gap-2"
>
	<ScrollArea orientation="horizontal" class="max-w-full">
		<Tabs.List class="h-8">
			{#each BRIEF_TABS as t, i (t)}
				<Tabs.Trigger value={t} class="gap-1.5 px-3 text-xs">
					{BRIEF_TAB_LABELS[t]}
					{#if t === 'host' && hostTotal > 1}
						<span class="font-mono text-2xs text-muted-foreground tabular-nums"
							>{hostTotal - 1}</span
						>
					{:else if t === 'check' && v.host_count > 1}
						<span class="font-mono text-2xs text-muted-foreground tabular-nums"
							>{v.host_count - 1}</span
						>
					{/if}
					<kbd class="hidden font-mono text-2xs text-muted-foreground sm:inline">{i + 1}</kbd>
				</Tabs.Trigger>
			{/each}
		</Tabs.List>
	</ScrollArea>

	<Tabs.Content value="asset" class="rounded-md border bg-card p-3">
		{#if !v.host && !asset}
			<p class="text-xs text-muted-foreground">No {WEB.noun}</p>
		{:else}
			<div class="flex flex-col gap-4 sm:flex-row">
				{#if asset?.screenshot_path}
					<ScreenshotThumb
						path={asset.screenshot_path}
						alt={v.host ?? ''}
						class="aspect-video w-full shrink-0 rounded-md border sm:w-48"
						interactive
						preview
					/>
				{/if}
				<dl
					class="grid min-w-0 flex-1 grid-cols-[auto_minmax(0,1fr)] content-start gap-x-4 gap-y-1.5 text-xs"
				>
					{#if v.host}
						<dt class="text-muted-foreground first-letter:uppercase">{WEB.noun}</dt>
						<dd class="flex min-w-0 items-center gap-2">
							{#if asset?.status_code != null}
								<span class="font-mono tabular-nums {httpStatusTextClass(asset.status_code)}"
									>{asset.status_code}</span
								>
							{/if}
							<button
								type="button"
								class="truncate font-mono hover:underline"
								onclick={() => onTab(WEB.tab, hostToken)}>{v.host}</button
							>
						</dd>
					{/if}
					{#if asset?.title}
						<dt class="text-muted-foreground">Title</dt>
						<dd class="truncate">{asset.title}</dd>
					{/if}
					{#if asset?.webserver}
						<dt class="text-muted-foreground">Server</dt>
						<dd class="truncate font-mono">{asset.webserver}</dd>
					{/if}
					{#if asset?.tech.length}
						<dt class="text-muted-foreground">Technology</dt>
						<dd class="flex min-w-0 flex-wrap gap-1">
							{#each asset.tech as tech (tech)}
								<button
									type="button"
									class="inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-2xs hover:bg-muted"
									onclick={() => onFilter(exactToken('tech', tech))}
								>
									<TechIcon name={tech} class="size-3" />{tech}
								</button>
							{/each}
						</dd>
					{/if}
					{#if v.ip}
						<dt class="text-muted-foreground">Address</dt>
						<dd class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5">
							<button
								type="button"
								class="font-mono hover:underline"
								onclick={() => onTab(IPS.tab, ipToken)}>{v.ip}</button
							>
							{#if asset?.country}<CountryFlag code={asset.country} showCode />{/if}
							{#if asset?.asn}
								<button
									type="button"
									class="truncate text-muted-foreground hover:text-foreground hover:underline"
									onclick={() => onFilter(`asn:${asset.asn}`)}
								>
									AS{asset.asn}{asset.asn_org ? ` · ${asset.asn_org}` : ''}
								</button>
							{/if}
						</dd>
					{/if}
					{#if asset?.is_cdn || asset?.waf}
						<dt class="text-muted-foreground">Edge</dt>
						<dd class="flex flex-wrap gap-1.5">
							{#if asset.is_cdn}<span class="rounded border px-1.5 py-0.5 text-2xs"
									>{asset.cdn_name ?? 'CDN'}</span
								>{/if}
							{#if asset.waf}<span class="rounded border px-1.5 py-0.5 text-2xs"
									>WAF · {asset.waf}</span
								>{/if}
						</dd>
					{/if}
				</dl>
			</div>
			<AssetTiles {v} {onFilter} {onTab} class="mt-3 border-t pt-3" />
		{/if}
	</Tabs.Content>

	<Tabs.Content value="host" class="overflow-hidden rounded-md border bg-card">
		{#if v.host}
			<div class="flex flex-wrap items-center gap-2 border-b px-3 py-1.5">
				<span class="font-mono text-xs">{v.host}</span>
				<span class="flex items-center gap-0.5">
					{#each SEVERITY_ORDER as s (s)}
						{#if v.host_findings?.[s]}
							<span
								class="inline-flex h-5 min-w-5 items-center justify-center rounded px-1 font-mono text-2xs font-semibold {SEVERITY_CHIP[
									s
								].chip}">{v.host_findings[s]}</span
							>
						{/if}
					{/each}
				</span>
				<button
					type="button"
					class="ml-auto text-2xs text-primary hover:underline"
					onclick={() => onFilter(hostToken)}
				>
					Filter to this {WEB.noun}
				</button>
			</div>
			<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-80">
				<FindingList
					{projectId}
					{scanId}
					q={hostToken}
					exclude={v.id}
					main={(f) => f.template_name}
					{onOpen}
				/>
			</ScrollArea>
		{:else}
			<p class="px-3 py-4 text-xs text-muted-foreground">
				No {WEB.noun}
			</p>
		{/if}
	</Tabs.Content>

	<Tabs.Content value="check" class="overflow-hidden rounded-md border bg-card">
		<div class="flex flex-wrap items-center gap-2 border-b px-3 py-1.5 text-xs">
			<span class="font-mono">{v.template_id}</span>
			<span class="text-muted-foreground">
				{v.host_count}
				{v.host_count === 1 ? WEB.noun : WEB.nounPlural}{v.replays
					? ` · reproduced on ${v.replays} equivalent`
					: ''}
			</span>
			<button
				type="button"
				class="ml-auto text-2xs text-primary hover:underline"
				onclick={() => onFilter(templateToken)}
			>
				All {checkTotal || ''} findings from this check
			</button>
		</div>
		{#if v.corroborated_by.length}
			<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/20 px-3 py-1.5 text-2xs">
				<span class="text-muted-foreground">Corroborated by</span>
				{#each v.corroborated_by as c (c.template_id)}
					<button
						type="button"
						class="inline-flex items-center gap-1 rounded border border-border bg-background px-1.5 py-0.5 hover:bg-muted"
						onclick={() => onFilter(exactToken('template', c.template_id))}
					>
						<span
							class="size-1.5 rounded-full {(SEVERITY_CHIP[c.severity] ?? SEVERITY_CHIP.unknown)
								.edge}"
						></span>
						{c.template_name}
						<span class="text-muted-foreground"
							>· {CORROBORATION_BASIS_LABELS[c.basis] ?? c.basis}</span
						>
					</button>
				{/each}
			</div>
		{/if}
		{#if v.host_count <= 1}
			<p class="px-3 py-4 text-xs text-muted-foreground">Only on this {WEB.noun}</p>
		{:else}
			<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-80">
				<FindingList
					{projectId}
					{scanId}
					q={templateToken}
					exclude={v.id}
					sort="host"
					main={(f) => f.host ?? locationLabel(f)}
					{onOpen}
					onTotal={(n) => (checkTotal = n)}
				/>
			</ScrollArea>
		{/if}
	</Tabs.Content>

	<Tabs.Content value="evidence" class="flex flex-col gap-3 rounded-md border bg-card p-3">
		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
			<EvidenceMark evidence={v.evidence} showLabel onFilter={(t) => onFilter(t)} />
			{#if v.matcher_name}
				<span
					><span class="text-muted-foreground">Matched on</span>
					<span class="font-mono">{v.matcher_name}</span></span
				>
			{/if}
			<span class="min-w-0 truncate font-mono text-muted-foreground">{v.matched_at}</span>
		</div>
		{#if v.extracted_results.length}
			<div class="flex flex-wrap gap-1">
				{#each v.extracted_results.slice(0, 12) as r, i (i)}
					<span class="rounded border bg-muted/40 px-1.5 py-0.5 font-mono text-2xs break-all"
						>{r}</span
					>
				{/each}
			</div>
		{/if}
		{#if v.request || v.response}
			<div class="grid gap-2 lg:grid-cols-2">
				{#if v.request}
					<CodeBlock code={v.request} lang="http" label="Request" maxLines={10} wrap />
				{/if}
				{#if v.response}
					<CodeBlock code={v.response} lang="http" label="Response" maxLines={10} wrap />
				{/if}
			</div>
		{:else}
			<p class="text-xs text-muted-foreground">No request or response stored.</p>
		{/if}
		{#if v.curl_command}
			<CodeBlock code={v.curl_command} lang="shell" label="curl" maxLines={4} wrap />
		{/if}
	</Tabs.Content>

	<Tabs.Content value="intel" class="rounded-md border bg-card p-3">
		<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
			<dl class="grid grid-cols-[auto_minmax(0,1fr)] content-start gap-x-4 gap-y-1.5 text-xs">
				{#if v.cve_ids.length}
					<dt class="text-muted-foreground">CVE</dt>
					<dd class="flex flex-wrap gap-x-2 font-mono">
						{#each v.cve_ids as c (c)}<a href={ROUTES.cve(c)} class="hover:underline">{c}</a>{/each}
					</dd>
				{/if}
				{#if v.cwe_ids.length}
					<dt class="text-muted-foreground">CWE</dt>
					<dd class="font-mono">{v.cwe_ids.join(', ')}</dd>
				{/if}
				{#if v.cvss_score != null}
					<dt class="text-muted-foreground">CVSS</dt>
					<dd class="font-mono">
						{v.cvss_score.toFixed(1)}
						{#if v.cvss_metrics}<span class="text-muted-foreground break-all">
								{v.cvss_metrics}</span
							>{/if}
					</dd>
				{/if}
				{#if v.epss_score != null}
					<dt class="text-muted-foreground">EPSS</dt>
					<dd class="flex items-baseline gap-1.5 font-mono">
						<span>{epssPercent(v.epss_score)}</span>
						{#if v.epss_percentile != null}
							<span class="text-muted-foreground"
								>· percentile {Math.round(v.epss_percentile * 100)}</span
							>
						{/if}
					</dd>
				{/if}
				{#if v.is_kev}
					<dt class="text-muted-foreground">KEV</dt>
					<dd class="flex flex-wrap items-center gap-x-2 text-destructive">
						<span class="inline-flex items-center gap-1"
							><Flame class="size-3" /> Exploited in the wild</span
						>
						{#if v.kev_due_date}<span class="text-muted-foreground"
								>Due {formatShortDate(v.kev_due_date)}</span
							>{/if}
						{#if v.kev_ransomware}<span>Ransomware</span>{/if}
					</dd>
				{/if}
				{#if v.poc_count}
					<dt class="text-muted-foreground">Exploits</dt>
					<dd>{v.poc_count} published</dd>
				{/if}
				{#if v.exploit_score > 0}
					<dt class="text-muted-foreground">Rank</dt>
					<dd class="font-mono">{v.exploit_score} / 100</dd>
				{/if}
				{#if !v.cve_ids.length && v.cvss_score == null && v.epss_score == null && !v.is_kev}
					<dt class="text-muted-foreground">CVE</dt>
					<dd class="text-muted-foreground">None</dd>
				{/if}
			</dl>
			<div class="flex min-w-0 flex-col gap-2 text-xs">
				{#if v.description}
					<p class="line-clamp-4 text-muted-foreground">{v.description}</p>
				{/if}
				{#if v.remediation}
					<div>
						<div class="mb-0.5 text-2xs tracking-wide text-muted-foreground uppercase">
							Remediation
						</div>
						<p class="line-clamp-4">{v.remediation}</p>
					</div>
				{/if}
			</div>
		</div>
	</Tabs.Content>
</Tabs.Root>

<div class="mt-3 flex flex-wrap items-center gap-2">
	<Button size="sm" class="h-8 gap-1.5" onclick={() => onOpen(v)}>
		<PanelRightOpen class="size-3.5" /> Open finding
	</Button>
	{#each [VulnState.CONFIRMED, VulnState.FALSE_POSITIVE, VulnState.ACCEPTED] as s (s)}
		<Button
			size="sm"
			variant={v.state === s ? 'secondary' : 'outline'}
			class="h-8"
			onclick={() => onTriage(v, v.state === s ? VulnState.OPEN : s)}
			aria-pressed={v.state === s}
		>
			{VULN_STATE_LABELS[s]}
		</Button>
	{/each}
	<Button size="sm" variant="outline" class="h-8 gap-1.5" onclick={() => onRescan(v)}>
		<RefreshCw class="size-3.5" /> Rescan
	</Button>
	{#if v.url}
		<Button
			size="sm"
			variant="ghost"
			class="h-8 gap-1.5"
			href={v.matched_at}
			target="_blank"
			rel="noopener noreferrer"
		>
			<ExternalLink class="size-3.5" /> Open location
		</Button>
	{/if}
</div>
