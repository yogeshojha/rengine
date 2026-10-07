<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		AI_ICON,
		aiCategoryLabel,
		aiModelQuery,
		aiQuery,
		aiServiceLabel
	} from '$lib/config/ai-services';
	import { SHEET_ROW_TIGHT, SHEET_DT, SHEET_HEAD, sheetStep } from './sheet';
	import SheetTop from './sheet-top.svelte';
	import SheetBar from './sheet-bar.svelte';
	import Globe from '@lucide/svelte/icons/globe';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import NotesButton from '$lib/components/notes/notes-button.svelte';
	import AskTab from './vulnerabilities/ask/ask-tab.svelte';
	import AskStarters from './vulnerabilities/ask/ask-starters.svelte';
	import type { AskSubject } from '$lib/types/ask';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import Network from '@lucide/svelte/icons/network';
	import Plug from '@lucide/svelte/icons/plug';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Link2 from '@lucide/svelte/icons/link-2';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Copy from '@lucide/svelte/icons/copy';
	import Star from '@lucide/svelte/icons/star';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Filter from '@lucide/svelte/icons/filter';
	import ImageOff from '@lucide/svelte/icons/image-off';
	import Layers from '@lucide/svelte/icons/layers';
	import MailWarning from '@lucide/svelte/icons/mail-warning';
	import MailCheck from '@lucide/svelte/icons/mail-check';
	import CrossLinks from '$lib/components/cross-links.svelte';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import CornerDownRight from '@lucide/svelte/icons/corner-down-right';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Check from '@lucide/svelte/icons/check';
	import X from '@lucide/svelte/icons/x';
	import {
		CHECK_BY_KEY as POSTURE_BY_KEY,
		postureQuery,
		sortChecks as sortPosture
	} from '$lib/config/domain-posture';
	import {
		CHECK_BY_KEY,
		GROUP_ICONS,
		GROUP_LABELS,
		TONE_DOT,
		TONE_TEXT,
		checkLabel,
		hygieneQuery,
		sortChecks,
		type HygieneGroup
	} from '$lib/config/hygiene';
	import {
		providerFor,
		PROVIDER_KIND_ICONS,
		PROVIDER_KIND_LABELS
	} from '$lib/config/hosting-providers';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Item from '$lib/components/ui/item';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Progress } from '$lib/components/ui/progress';
	import Hint from '$lib/components/hint.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ScreenshotThumb from './screenshot-thumb.svelte';
	import TechIcon from './tech-icon.svelte';
	import CodeBlock from '$lib/components/code-block.svelte';
	import ProxySend from './endpoints/proxy-send.svelte';
	import { handoffToProxy } from './endpoints/proxy';
	import { connectors as connectorStore } from '$lib/stores/connectors.svelte';
	import { SEND_SHORTCUT, type ActionKind } from '$lib/config/connectors';
	import OverflowPopover from './table/overflow-popover.svelte';
	import HostStructure from './web-assets/host-structure.svelte';
	import RecheckHistory from './recheck-history.svelte';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { httpAssetsApi } from '$lib/api/scan-results';
	import { subdomainsApi } from '$lib/api/subdomains';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import type { HttpAssetDetail } from '$lib/types/http-asset';
	import type { SubdomainCorrelation } from '$lib/utilities/scan-insights';
	import { certState, daysUntilExpiry, exactToken } from '$lib/utilities/scan-insights';
	import {
		formatResponseTime,
		httpStatusClass,
		httpStatusReason,
		httpStatusTextClass,
		isPrivateIp,
		STATUS_DOT
	} from '$lib/utilities/scan-correlation';
	import { formatBytes } from '$lib/utilities/format';
	import { isSensitivePort } from '$lib/config/service-classes';
	import {
		CLUSTER_SIGNAL_LABELS,
		DROP_REASON_LABELS,
		SURFACE_STATE_LABELS,
		TIER_LABELS,
		tierOutcome
	} from '$lib/config/scan-surface';
	import { COVERAGE_STATUS_LABELS } from '$lib/config/vulnerabilities';
	import { formatDateTime, formatShortDate, relativeTime } from '$lib/utilities/dates';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { hostPort } from '$lib/utilities/net';
	import { externalHref } from '$lib/utilities/links';
	import { plural } from '$lib/utilities/strings';

	interface Props {
		sub: SubdomainRead | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		projectId: string;
		scanId: string;
		scopeScanId?: string;
		index?: number;
		pageOffset?: number;
		total?: number;
		capped?: boolean;
		onStep?: (dir: -1 | 1) => void;
		onFilter?: (dsl: string) => void;
		onPivot?: (name: string) => void;
		onOpenEndpoints?: (host: string) => void;
		focus?: { tab: string; pane?: string } | null;
	}

	let {
		sub,
		open,
		onOpenChange,
		projectId,
		scanId,
		scopeScanId,
		index = 0,
		pageOffset = 0,
		total = 0,
		capped = false,
		onStep,
		onFilter,
		onPivot,
		onOpenEndpoints,
		focus = null
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const MAX_SANS = 4;
	const MAX_HOSTS = 16;

	let tab = $state('overview');
	let tabRefs = $state<Record<string, HTMLElement | null>>({});
	let queued = $state('');
	let recheckCount = $derived(sub ? rechecks.history(scanId, sub.name).length : 0);
	let contentEl = $state<HTMLElement | null>(null);
	let bodyEl = $state<HTMLElement | null>(null);
	let detail = $state<HttpAssetDetail | null>(null);
	let detailLoading = $state(false);
	let detailErrored = $state(false);
	let httpView = $state('response');
	let loadedFor = '';
	let detailFor = '';
	let tabFor = '';
	let focusFor: typeof focus = null;
	let corr = $state<SubdomainCorrelation | null>(null);
	let corrLoading = $state(false);
	let corrErrored = $state(false);

	$effect.pre(() => {
		const name = open && sub ? sub.name : '';
		const asked = focus;
		if (name === tabFor && asked === focusFor) return;
		const fresh = !tabFor || asked !== focusFor;
		tabFor = name;
		focusFor = asked;
		if (!name) return;
		const target = fresh ? asked : null;
		untrack(() => {
			tab = target?.tab ?? 'overview';
			httpView = target?.pane ?? 'response';
			queued = '';
			bodyEl?.scrollTo({ top: 0 });
			const held = document.activeElement;
			if (held?.getAttribute('role') === 'tab' && contentEl?.contains(held)) {
				tabRefs[tab]?.focus();
			}
		});
	});

	let primaryAsset = $derived(corr?.primary_asset ?? null);
	let hostAssets = $derived(corr?.services ?? []);
	let aiAssets = $derived(hostAssets.filter((a) => !!a.ai_service));
	let ports = $derived(corr?.ports ?? []);
	let ipMetas = $derived(corr?.ip_metas ?? []);
	let related = $derived(corr?.related ?? []);
	let relatedHosts = $derived(new Set(related.flatMap((r) => r.hosts)).size);

	function loadCorrelation(name: string) {
		corr = null;
		corrErrored = false;
		corrLoading = true;
		subdomainsApi
			.correlation(projectId, scopeScanId ?? scanId, name)
			.then((c) => {
				if (loadedFor === name) corr = c;
			})
			.catch(() => {
				if (loadedFor === name) corrErrored = true;
			})
			.finally(() => {
				if (loadedFor === name) corrLoading = false;
			});
	}

	function loadDetail(assetId: string, forName: string) {
		detailFor = assetId;
		detailLoading = true;
		detailErrored = false;
		httpAssetsApi
			.detail(projectId, assetId)
			.then((d) => {
				if (loadedFor === forName) detail = d;
			})
			.catch(() => {
				if (loadedFor !== forName) return;
				detail = null;
				detailErrored = true;
			})
			.finally(() => {
				if (loadedFor === forName) detailLoading = false;
			});
	}

	$effect(() => {
		if (!open || !sub) return;
		const name = sub.name;
		if (loadedFor !== name) {
			loadedFor = name;
			detailFor = '';
			detail = null;
			detailLoading = false;
			detailErrored = false;
			loadCorrelation(name);
		}
		const assetId = corr?.primary_asset?.id;
		if (assetId && detailFor !== assetId) loadDetail(assetId, name);
	});

	let hasHttp = $derived(sub?.http_status != null);
	let canSend = $derived(hasHttp && (!!detail || corrLoading || detailLoading));
	let url = $derived(sub?.http_url ?? (sub ? `https://${sub.name}` : ''));
	let proxies = $derived(connectorStore.items);
	let proxyCatalog = $derived(connectorStore.catalog);
	$effect(() => {
		const id = projectId;
		if (!open || !id) return;
		untrack(() => {
			void connectorStore.load(id);
			void connectorStore.loadCatalog();
		});
	});
	async function sendToProxy(connectorId: string, kind: ActionKind) {
		if (!detail) return null;
		return handoffToProxy({
			connectorId,
			projectId,
			scanId: detail.scan_id,
			body: { kind, asset_ids: [detail.id] },
			connectors: proxies,
			catalog: proxyCatalog
		});
	}
	let askSubject = $derived<AskSubject | null>(
		sub
			? {
					dimension: SurfaceDimension.WEB_ASSETS,
					key: sub.name,
					targetId: sub.target_id,
					scanId: sub.scan_id,
					projectId,
					label: sub.name
				}
			: null
	);

	function ask(question: string) {
		queued = question;
		tab = 'ask';
	}
	let redirected = $derived(!!sub?.final_url && sub.final_url !== sub.http_url);
	let cert = $derived(sub ? certState(sub) : null);
	let expiryDays = $derived(sub ? daysUntilExpiry(sub) : null);
	let validityPct = $derived.by(() => {
		const from = primaryAsset?.tls_not_before;
		const to = sub?.tls_not_after;
		if (!from || !to) return null;
		const a = new Date(from).getTime();
		const b = new Date(to).getTime();
		if (b <= a) return 0;
		return Math.max(0, Math.min(100, ((b - Date.now()) / (b - a)) * 100));
	});
	let rawResponse = $derived(
		detail ? [detail.raw_response_header, detail.response_body].filter(Boolean).join('\n\n') : ''
	);
	let headerEntries = $derived(detail ? Object.entries(detail.response_headers ?? {}) : []);
	let hygieneIssues = $derived(sortChecks(sub?.hygiene_issues ?? []));
	let hygieneChecked = $derived(sub?.hygiene_checked ?? []);
	let postureIssues = $derived(sortPosture(sub?.posture_issues ?? []));
	let postureChecked = $derived(sub?.posture_checked ?? []);
	let verdicts = $derived(detail?.hygiene ?? []);
	let verdictFailing = $derived(verdicts.filter((v) => v.failed).length);
	let evidenceByKey = $derived<Record<string, string>>(
		Object.fromEntries(
			verdicts.filter((v) => v.failed && v.evidence).map((v) => [v.key, v.evidence ?? ''])
		)
	);
	let verdictGroups = $derived.by(() => {
		const out: { group: HygieneGroup; list: typeof verdicts }[] = [];
		for (const v of verdicts) {
			const spec = CHECK_BY_KEY[v.key];
			if (!spec) continue;
			const bucket = out.find((g) => g.group === spec.group);
			if (bucket) bucket.list.push(v);
			else out.push({ group: spec.group, list: [v] });
		}
		return out;
	});
	function showChecks() {
		tab = 'http';
		httpView = 'hygiene';
	}
	let headerText = $derived(headerEntries.map(([k, v]) => `${k}: ${fmtHeader(v)}`).join('\n'));
	let privateIps = $derived((sub?.resolved_ips ?? []).filter(isPrivateIp));
	let flagged = $derived(
		!!sub &&
			(sub.is_cdn ||
				!!sub.waf ||
				(cert !== null && cert !== 'valid') ||
				privateIps.length > 0 ||
				sub.is_wildcard ||
				redirected)
	);
	let provider = $derived(providerFor(sub?.cname));
	let ProviderIcon = $derived(provider ? PROVIDER_KIND_ICONS[provider.kind] : null);

	function fmtHeader(v: string | string[]): string {
		return Array.isArray(v) ? v.join(', ') : v;
	}
	async function copyHeaders() {
		if (await writeClipboard(headerText)) toast.success('Headers copied');
		else toast.error('Headers not copied');
	}
</script>

<svelte:window onkeydown={(e) => sheetStep(e, open, onStep)} />

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content
		bind:ref={contentEl}
		side="right"
		tabindex={-1}
		class="flex w-full flex-col gap-0 p-0 outline-none sm:max-w-2xl"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			contentEl?.focus();
		}}
	>
		{#if sub}
			<Sheet.Header class={SHEET_HEAD}>
				<SheetTop noun={WEB.noun} {index} {pageOffset} {total} {capped} {onStep}>
					<span class="flex items-center gap-1.5 text-xs">
						<span
							class="size-2 shrink-0 rounded-full {STATUS_DOT[httpStatusClass(sub.http_status)]}"
							aria-hidden="true"
						></span>
						{#if hasHttp}
							<span class="font-mono font-medium {httpStatusTextClass(sub.http_status)}"
								>{sub.http_status}</span
							>
							<span class="text-muted-foreground">{httpStatusReason(sub.http_status)}</span>
						{/if}
					</span>
					{#if sub.is_important}<Star class="size-3.5 shrink-0 fill-warning text-warning" />{/if}
				</SheetTop>
				<div class="flex min-w-0 items-center gap-1">
					<Sheet.Title class="min-w-0 truncate font-mono text-base font-medium"
						>{sub.name}</Sheet.Title
					>
					<CopyButton value={sub.name} />
					{#if hasHttp}
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="ghost"
										size="icon-sm"
										class="size-7 shrink-0"
										href={externalHref(url)}
										target="_blank"
										rel="noreferrer noopener"
										aria-label="Open in browser"
									>
										<ExternalLink class="size-3.5 text-muted-foreground" />
									</Button>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content>Open in browser</Tooltip.Content>
						</Tooltip.Root>
					{/if}
				</div>
				{#if !hasHttp || sub.page_title || flagged}
					<div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
						{#if !hasHttp || sub.page_title}
							<Sheet.Description class="min-w-0 truncate">
								{#if hasHttp}
									{sub.page_title}
								{:else if sub.resolved_ips?.length}
									Resolves but no web service answered
								{:else}
									Did not resolve to an address
								{/if}
							</Sheet.Description>
						{/if}
						{#if sub.is_cdn}
							<Badge variant="info" class="font-normal">{sub.cdn_name ?? 'CDN'}</Badge>
						{/if}
						{#if sub.waf}<Badge variant="secondary" class="font-normal">WAF · {sub.waf}</Badge>{/if}
						{#if cert === 'expired'}
							<Badge variant="destructive" class="font-normal">Certificate expired</Badge>
						{:else if cert === 'expiring'}
							<Badge variant="warning" class="font-normal"
								>Certificate expires in {expiryDays}d</Badge
							>
						{:else if cert === 'self-signed'}
							<Badge variant="warning" class="font-normal">Self-signed certificate</Badge>
						{/if}
						{#if privateIps.length}
							<Badge variant="warning" class="font-normal">Private address</Badge>
						{/if}
						{#if sub.is_wildcard}<Badge variant="outline" class="font-normal">Wildcard</Badge>{/if}
						{#if redirected}<Badge variant="outline" class="font-normal">Redirects</Badge>{/if}
					</div>
				{/if}
			</Sheet.Header>

			<SheetBar>
				<NotesButton
					anchor={{
						targetId: sub.target_id,
						scanId: sub.scan_id,
						dimension: SurfaceDimension.WEB_ASSETS,
						assetKey: sub.name,
						assetLabel: sub.name
					}}
					class="h-8"
				/>
				{#if canSend}
					<ProxySend
						connectors={proxies}
						catalog={proxyCatalog}
						shortcut={SEND_SHORTCUT}
						class="h-8"
						onSend={sendToProxy}
					/>
				{/if}
			</SheetBar>

			<Tabs.Root bind:value={tab} class="flex min-h-0 flex-1 flex-col gap-0">
				<ScrollArea orientation="horizontal" class="shrink-0 border-b border-border">
					<Tabs.List
						class="h-auto w-max min-w-full justify-start gap-0 rounded-none bg-transparent p-0 px-2"
					>
						{@render tabTrigger('overview', 'Overview', null)}
						<Tabs.Trigger
							value="ask"
							bind:ref={tabRefs.ask}
							class="flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 py-2.5 text-xs font-medium text-primary shadow-none hover:text-primary data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent"
						>
							<Sparkles class="size-3.5" />
							Ask
						</Tabs.Trigger>
						{@render tabTrigger('http', 'HTTP', null)}
						{@render tabTrigger('services', 'Services', hostAssets.length + ports.length || null)}
						{@render tabTrigger('related', 'Related', relatedHosts || null)}
						{@render tabTrigger('structure', 'Structure', sub.endpoint_count || null)}
						{#if recheckCount}
							{@render tabTrigger('rechecks', 'Re-checks', recheckCount)}
						{/if}
					</Tabs.List>
				</ScrollArea>

				<ScrollArea class="min-h-0 flex-1" bind:viewportRef={bodyEl}>
					<Tabs.Content value="rechecks" class="m-0 p-5">
						<RecheckHistory {scanId} assetKey={sub.name} />
					</Tabs.Content>

					<Tabs.Content value="overview" class="m-0 flex flex-col gap-6 p-5">
						{#if askSubject}
							<AskStarters subject={askSubject} onAsk={ask} />
						{/if}
						{#if sub.screenshot_path}
							<ScreenshotThumb
								path={sub.screenshot_path}
								alt={sub.name}
								class="aspect-video w-full"
							/>
						{:else if hasHttp}
							<div
								class="flex aspect-[16/6] w-full flex-col items-center justify-center gap-1 rounded-md border border-dashed border-border text-muted-foreground"
							>
								<ImageOff class="size-5" />
								<span class="text-xs">No screenshot</span>
							</div>
						{/if}

						{#if redirected}
							<div
								class="flex items-start gap-2 rounded-md border border-border bg-muted/40 p-3 text-xs"
							>
								<CornerDownRight class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
								<div class="min-w-0">
									<span class="text-muted-foreground">Redirects to</span>
									<a
										href={externalHref(sub.final_url)}
										target="_blank"
										rel="noreferrer noopener"
										class="ml-1 font-mono break-all hover:text-primary">{sub.final_url}</a
									>
								</div>
							</div>
						{/if}

						<section class="flex flex-col gap-2">
							<SectionHead icon={Network} title="Identity" />
							<dl class="flex flex-col divide-y divide-border/60">
								<div class={SHEET_ROW_TIGHT}>
									<dt class={SHEET_DT}>Resolves to</dt>
									<dd class="flex flex-wrap gap-1">
										{#if sub.resolved_ips?.length}
											{#each sub.resolved_ips as ip (ip)}
												{@render chip(
													ip,
													`ip:${ip}`,
													true,
													isPrivateIp(ip) ? 'Private range' : undefined
												)}
											{/each}
										{:else}
											<span class="text-xs text-muted-foreground">No DNS answer</span>
										{/if}
									</dd>
								</div>
								{#if sub.cname}
									<div class={SHEET_ROW_TIGHT}>
										<dt class={SHEET_DT}>CNAME</dt>
										<dd class="flex flex-wrap items-center gap-1">
											{#if provider && ProviderIcon}
												{@const prov = provider}
												<Tooltip.Root>
													<Tooltip.Trigger>
														{#snippet child({ props })}
															<button
																{...props}
																type="button"
																onclick={() => onFilter?.(`cname:${prov.suffix}`)}
															>
																<Badge variant="secondary" class="cursor-pointer gap-1 font-normal">
																	<ProviderIcon class="size-3" />
																	{prov.label}
																</Badge>
															</button>
														{/snippet}
													</Tooltip.Trigger>
													<Tooltip.Content>
														{PROVIDER_KIND_LABELS[prov.kind]} · Filter by provider
													</Tooltip.Content>
												</Tooltip.Root>
											{/if}
											{@render chip(sub.cname, `cname:${sub.cname}`, true)}
										</dd>
									</div>
								{/if}
								{#if sub.asn}
									<div class={SHEET_ROW_TIGHT}>
										<dt class={SHEET_DT}>Network</dt>
										<dd class="text-sm">
											<span class="font-mono">AS{sub.asn}</span>
											{#if sub.asn_org}<span class="text-muted-foreground">
													· {sub.asn_org}</span
												>{/if}
										</dd>
									</div>
								{/if}
								<div class={SHEET_ROW_TIGHT}>
									<dt class={SHEET_DT}>Discovered via</dt>
									<dd class="flex flex-wrap gap-1">
										{#each sub.sources ?? [] as src (src)}
											{@render chip(src, `source:${src}`)}
										{/each}
									</dd>
								</div>
								<div class={SHEET_ROW_TIGHT}>
									<dt class={SHEET_DT}>First seen</dt>
									<Hint text={formatDateTime(sub.discovered_at)}>
										{#snippet child(props)}
											<dd {...props} class="text-sm">
												{formatShortDate(sub.discovered_at)}
												<span class="text-muted-foreground">
													· {relativeTime(sub.discovered_at)}
												</span>
											</dd>
										{/snippet}
									</Hint>
								</div>
								{#if sub.favicon_hash}
									<div class={SHEET_ROW_TIGHT}>
										<dt class={SHEET_DT}>Favicon</dt>
										<dd>
											{@render chip(
												sub.favicon_hash,
												`favicon:${sub.favicon_hash}`,
												true,
												'Filter by favicon'
											)}
											{#if (sub.favicon_count ?? 0) > 1}
												<span class="ml-1 text-xs text-muted-foreground">
													Shared by {sub.favicon_count}
													{WEB.nounPlural}
												</span>
											{/if}
										</dd>
									</div>
								{/if}
							</dl>
						</section>

						{#if hasHttp}
							<section class="flex flex-col gap-2">
								<SectionHead icon={Globe} title="Web service" />
								<dl class="flex flex-col divide-y divide-border/60">
									<div class={SHEET_ROW_TIGHT}>
										<dt class={SHEET_DT}>URL</dt>
										<dd>
											<a
												href={externalHref(url)}
												target="_blank"
												rel="noreferrer noopener"
												class="font-mono text-sm break-all hover:text-primary">{url}</a
											>
										</dd>
									</div>
									{#if sub.page_title}
										<div class={SHEET_ROW_TIGHT}>
											<dt class={SHEET_DT}>Page title</dt>
											<dd class="flex flex-wrap items-center gap-2 text-sm">
												<span class="break-words">{sub.page_title}</span>
												{#if (sub.title_count ?? 0) > 1}
													{@const pageTitle = sub.page_title}
													<Button
														variant="outline"
														size="sm"
														class="h-6 text-xs"
														onclick={() => onFilter?.(exactToken('title', pageTitle))}
													>
														<Layers data-icon="inline-start" />
														{sub.title_count}
														{WEB.nounPlural} show this page
													</Button>
												{/if}
											</dd>
										</div>
									{/if}
									{#if sub.cross_links?.length}
										<div class={SHEET_ROW_TIGHT}>
											<dt class={SHEET_DT}>Shared with</dt>
											<dd class="flex flex-wrap items-center gap-2 text-sm">
												<CrossLinks links={sub.cross_links} onHost={onPivot} />
											</dd>
										</div>
									{/if}
									{@render kv('Web server', sub.webserver)}
									{@render kv('Content type', sub.content_type)}
									{@render kv(
										'Response',
										[
											sub.content_length != null ? formatBytes(sub.content_length) : null,
											sub.response_time != null ? formatResponseTime(sub.response_time) : null,
											detail?.lines != null ? plural(detail.lines, 'line') : null,
											detail?.words != null ? plural(detail.words, 'word') : null
										]
											.filter(Boolean)
											.join(' · ') || null
									)}
									{#if detail?.surface}
										{@const surface = detail.surface}
										<div class={SHEET_ROW_TIGHT}>
											<dt class={SHEET_DT}>Vulnerability scan</dt>
											<dd class="flex min-w-0 flex-col gap-1 text-sm">
												{#if surface.state === 'covered' && surface.representative_value}
													<span class="break-all">
														Covered by
														<button
															type="button"
															class="font-mono hover:text-primary"
															onclick={() => {
																const rep = surface.representative_value ?? '';
																const host = rep.replace(/^https?:\/\//, '').replace(/:\d+$/, '');
																onPivot?.(host);
															}}>{surface.representative_value}</button
														>
													</span>
													<span class="text-xs text-muted-foreground">
														{surface.cluster_signals
															.map((k) => CLUSTER_SIGNAL_LABELS[k] ?? k)
															.join(' · ')}
													</span>
												{:else if surface.state === 'not_scanned'}
													<span>
														Not scanned{surface.drop_reason
															? ` · ${DROP_REASON_LABELS[surface.drop_reason] ?? surface.drop_reason}`
															: ''}
													</span>
												{:else}
													<span>
														{SURFACE_STATE_LABELS[surface.state] ?? surface.state}{surface.members >
														1
															? ` · stands for ${surface.members} web assets`
															: ''}
													</span>
													{#if surface.tiers_planned.length}
														<span class="text-xs text-muted-foreground">
															{surface.tiers_planned
																.map((t) => {
																	const done = tierOutcome(surface.tiers_done[t]);
																	const label = TIER_LABELS[t] ?? t;
																	return done
																		? `${label}: ${COVERAGE_STATUS_LABELS[done] ?? done}`
																		: `${label}: not reached`;
																})
																.join(' · ')}
														</span>
													{/if}
												{/if}
												{#if surface.note}
													<span class="text-xs text-warning">{surface.note}</span>
												{/if}
											</dd>
										</div>
									{/if}
								</dl>
							</section>
						{:else}
							<div
								class="flex items-start gap-3 rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground"
							>
								<Globe class="mt-0.5 size-4 shrink-0" />
								<div>
									<p class="font-medium text-foreground">No HTTP service</p>
									<p class="mt-0.5">
										{sub.resolved_ips?.length
											? 'Resolves. No answer on the probed web ports.'
											: 'Did not resolve. Not probed.'}
									</p>
								</div>
							</div>
						{/if}

						{#if hasHttp && hygieneChecked.length}
							<section class="flex flex-col gap-2">
								<div class="flex items-center justify-between">
									<SectionHead
										icon={hygieneIssues.length ? ShieldAlert : ShieldCheck}
										title="Web hygiene"
									/>
									<Button variant="ghost" size="sm" class="h-6 text-xs" onclick={showChecks}>
										All checks <ChevronRight data-icon="inline-end" />
									</Button>
								</div>
								{#if hygieneIssues.length}
									<ul class="flex flex-col divide-y divide-border/60">
										{#each hygieneIssues as key (key)}
											{@const spec = CHECK_BY_KEY[key]}
											{@const evidence = evidenceByKey[key]}
											<li class="flex items-start gap-2 py-2">
												<span class="flex h-5 shrink-0 items-center">
													<span
														class="size-1.5 rounded-full {spec ? TONE_DOT[spec.tone] : 'bg-muted'}"
														aria-hidden="true"
													></span>
												</span>
												<div class="min-w-0 flex-1">
													<Tooltip.Root>
														<Tooltip.Trigger>
															{#snippet child({ props })}
																<button
																	{...props}
																	type="button"
																	class="text-left text-sm leading-5 hover:text-primary"
																	onclick={() => onFilter?.(hygieneQuery(key))}
																>
																	{checkLabel(key)}
																</button>
															{/snippet}
														</Tooltip.Trigger>
														<Tooltip.Content class="flex max-w-xs items-center gap-1.5">
															{spec?.help ?? 'Filter table'}
															<Fingerprint class="size-3 opacity-60" />
															<span class="font-mono">{hygieneQuery(key)}</span>
														</Tooltip.Content>
													</Tooltip.Root>
													{#if evidence}
														<p class="font-mono text-2xs break-all text-muted-foreground">
															{evidence}
														</p>
													{/if}
												</div>
											</li>
										{/each}
									</ul>
								{:else}
									<p class="text-xs text-muted-foreground">
										Passes all {hygieneChecked.length} checks that apply.
									</p>
								{/if}
								{#if hostAssets.length > 1}
									<p class="text-xs text-muted-foreground">
										Across {hostAssets.length} web services.
									</p>
								{/if}
							</section>
						{/if}

						{#if postureChecked.length}
							<section class="flex flex-col gap-2">
								<SectionHead
									icon={postureIssues.length ? MailWarning : MailCheck}
									title="Domain posture"
								/>
								{#if postureIssues.length}
									<ul class="flex flex-col divide-y divide-border/60">
										{#each postureIssues as key (key)}
											{@const spec = POSTURE_BY_KEY[key]}
											<li class="flex items-start gap-2 py-2">
												<span class="flex h-5 shrink-0 items-center">
													<span
														class="size-1.5 rounded-full {spec ? TONE_DOT[spec.tone] : 'bg-muted'}"
														aria-hidden="true"
													></span>
												</span>
												<div class="min-w-0 flex-1">
													<Tooltip.Root>
														<Tooltip.Trigger>
															{#snippet child({ props })}
																<button
																	{...props}
																	type="button"
																	class="text-left text-sm leading-5 hover:text-primary"
																	onclick={() => onFilter?.(postureQuery(key))}
																>
																	{spec?.label ?? key}
																</button>
															{/snippet}
														</Tooltip.Trigger>
														<Tooltip.Content class="flex max-w-xs items-center gap-1.5">
															{spec?.help ?? 'Filter table'}
															<Fingerprint class="size-3 opacity-60" />
															<span class="font-mono">{postureQuery(key)}</span>
														</Tooltip.Content>
													</Tooltip.Root>
													{#if spec}
														<p class="text-xs text-muted-foreground">{spec.fix}</p>
													{/if}
												</div>
											</li>
										{/each}
									</ul>
								{:else}
									<p class="text-xs text-muted-foreground">
										The zone passes all {postureChecked.length} checks that apply.
									</p>
								{/if}
							</section>
						{/if}

						{#if aiAssets.length}
							<section class="flex flex-col gap-2">
								<SectionHead icon={AI_ICON} title="AI services" />
								<ul class="flex flex-col divide-y divide-border/60">
									{#each aiAssets as a (a.id)}
										{@const service = a.ai_service ?? ''}
										<li class="flex flex-col gap-1.5 py-2">
											<div class="flex flex-wrap items-center gap-1.5">
												{@render chip(aiServiceLabel(service), aiQuery(service))}
												<span class="text-xs text-muted-foreground">
													{aiCategoryLabel(a.ai_category)}
												</span>
												<span class="ml-auto font-mono text-2xs break-all text-muted-foreground">
													{a.scheme}://{hostPort(a.host, a.port)}{a.ai_endpoint ?? ''}
												</span>
											</div>
											{#if a.ai_models?.length}
												<div class="flex flex-wrap items-center gap-1">
													<span class="text-2xs text-muted-foreground">Models listed</span>
													{#each a.ai_models as model (model)}
														{@render chip(model, aiModelQuery(model), true)}
													{/each}
												</div>
											{/if}
										</li>
									{/each}
								</ul>
							</section>
						{/if}

						{#if sub.tech.length || detail?.cpe?.length}
							<section class="flex flex-col gap-2">
								<SectionHead icon={Layers} title="Technologies" />
								<div class="flex flex-wrap gap-1">
									{#each sub.tech as t (t)}
										{@render chip(t, `tech:${t}`, false, undefined, false, true)}
									{/each}
								</div>
								{#if detail?.cpe?.length}
									<div class="flex flex-wrap gap-1">
										{#each detail.cpe as c (c)}
											<Badge variant="secondary" class="font-mono text-2xs font-normal"
												>{c.cpe}</Badge
											>
										{/each}
									</div>
								{/if}
							</section>
						{/if}

						{#if sub.tls_not_after || primaryAsset?.tls_version}
							<section class="flex flex-col gap-2">
								<div class="flex items-center justify-between">
									<SectionHead
										icon={sub.tls_expired || sub.tls_self_signed ? ShieldAlert : ShieldCheck}
										title="TLS certificate"
									/>
									{#if primaryAsset?.tls_version}
										<span class="text-xs text-muted-foreground">
											{primaryAsset.tls_version}{primaryAsset.tls_cipher
												? ` · ${primaryAsset.tls_cipher}`
												: ''}
										</span>
									{/if}
								</div>
								{#if sub.tls_not_after}
									<div class="flex flex-col gap-1.5">
										<div class="flex items-center justify-between text-xs">
											<span
												class={cert === 'expired'
													? 'text-destructive'
													: cert === 'expiring'
														? 'text-warning'
														: 'text-muted-foreground'}
											>
												{#if cert === 'expired'}
													Expired {formatShortDate(sub.tls_not_after)}
												{:else}
													Expires in {expiryDays}d · {formatShortDate(sub.tls_not_after)}
												{/if}
											</span>
											{#if primaryAsset?.tls_not_before}
												<span class="text-muted-foreground">
													Issued {formatShortDate(primaryAsset.tls_not_before)}
												</span>
											{/if}
										</div>
										{#if validityPct != null}
											<Progress
												value={validityPct}
												class="h-1.5 {cert === 'expired'
													? '*:data-[slot=progress-indicator]:bg-destructive'
													: cert === 'expiring'
														? '*:data-[slot=progress-indicator]:bg-warning'
														: ''}"
												aria-label="Certificate validity remaining"
											/>
										{/if}
									</div>
								{/if}
								{#if corrLoading}
									<Skeleton class="h-16 w-full" />
								{:else if primaryAsset}
									<dl class="flex flex-col divide-y divide-border/60">
										{@render kv('Subject', primaryAsset.tls_subject_cn)}
										{@render kv('Issuer', primaryAsset.tls_issuer_org ?? primaryAsset.tls_issuer)}
										{#if primaryAsset.tls_sans?.length}
											<div class={SHEET_ROW_TIGHT}>
												<dt class={SHEET_DT}>SANs</dt>
												<dd class="flex flex-wrap items-center gap-1">
													{#each primaryAsset.tls_sans.slice(0, MAX_SANS) as san (san)}
														<Badge variant="outline" class="font-mono text-2xs font-normal"
															>{san}</Badge
														>
													{/each}
													<OverflowPopover
														items={primaryAsset.tls_sans}
														shown={MAX_SANS}
														label="subject alternative names"
														mono
													/>
												</dd>
											</div>
										{/if}
										{#if primaryAsset.tls_fingerprint}
											<div class={SHEET_ROW_TIGHT}>
												<dt class={SHEET_DT}>Fingerprint</dt>
												<dd class="flex min-w-0 items-center gap-1">
													<span class="min-w-0 truncate font-mono text-xs"
														>{primaryAsset.tls_fingerprint}</span
													>
													<span class="flex h-5 shrink-0 items-center">
														<CopyButton value={primaryAsset.tls_fingerprint} />
													</span>
												</dd>
											</div>
										{/if}
									</dl>
								{/if}
							</section>
						{/if}
					</Tabs.Content>

					<Tabs.Content value="ask" class="m-0 flex flex-col p-0">
						{#if tab === 'ask' && askSubject}
							<AskTab subject={askSubject} {queued} onQueued={() => (queued = '')} />
						{/if}
					</Tabs.Content>

					<Tabs.Content value="http" class="m-0 p-5">
						{#if !hasHttp}
							{@render emptyNote('No HTTP capture', 'No web service answered.')}
						{:else if corrLoading || (detailLoading && !detail)}
							<div class="flex flex-col gap-2">
								<Skeleton class="h-8 w-48" />
								<Skeleton class="h-64 w-full" />
							</div>
						{:else if detail}
							<div class="flex flex-col gap-3">
								<div class="flex items-center justify-between">
									<ToggleGroup.Root type="single" bind:value={httpView} variant="outline" size="sm">
										<ToggleGroup.Item value="response" class="text-xs">Response</ToggleGroup.Item>
										<ToggleGroup.Item value="headers" class="text-xs">
											Headers <span class="text-muted-foreground">{headerEntries.length}</span>
										</ToggleGroup.Item>
										<ToggleGroup.Item value="request" class="text-xs">Request</ToggleGroup.Item>
										{#if verdicts.length}
											<ToggleGroup.Item value="hygiene" class="text-xs">
												Hygiene
												<span class={verdictFailing ? TONE_TEXT.warning : 'text-muted-foreground'}>
													{verdictFailing}
												</span>
											</ToggleGroup.Item>
										{/if}
									</ToggleGroup.Root>
									{#if httpView === 'headers'}
										<Button
											variant="ghost"
											size="sm"
											class="h-7 text-xs"
											onclick={() => copyHeaders()}
										>
											<Copy data-icon="inline-start" /> Copy
										</Button>
									{/if}
								</div>
								{#if httpView === 'hygiene'}
									<div class="flex flex-col gap-4">
										<p class="text-xs text-muted-foreground tabular-nums">
											{verdictFailing} of {verdicts.length}
											{verdicts.length === 1 ? 'check' : 'checks'} that apply to this response fail.
										</p>
										{#each verdictGroups as { group, list } (group)}
											<section class="flex flex-col gap-2">
												<SectionHead icon={GROUP_ICONS[group]} title={GROUP_LABELS[group]} />
												<ul class="divide-y divide-border/60 rounded-md border border-border">
													{#each list as v (v.key)}
														{@const spec = CHECK_BY_KEY[v.key]}
														<li class="flex items-start gap-2 px-3 py-2">
															<span class="flex h-5 shrink-0 items-center">
																{#if v.failed}
																	<X class="size-3.5 {spec ? TONE_TEXT[spec.tone] : ''}" />
																{:else}
																	<Check class="size-3.5 text-success" />
																{/if}
															</span>
															<div class="min-w-0 flex-1">
																<div class="flex flex-wrap items-baseline gap-x-2">
																	<span class="text-sm leading-5">{spec?.control ?? v.key}</span>
																	{#if spec?.header}
																		<span class="font-mono text-2xs text-muted-foreground"
																			>{spec.header}</span
																		>
																	{/if}
																</div>
																{#if v.failed}
																	<p class="text-xs {spec ? TONE_TEXT[spec.tone] : ''}">
																		{checkLabel(v.key)}
																	</p>
																{/if}
																{#if v.evidence}
																	<p class="font-mono text-2xs break-all text-muted-foreground">
																		{v.evidence}
																	</p>
																{/if}
																{#if v.failed && spec}
																	<p class="text-xs text-muted-foreground">{spec.fix}</p>
																{/if}
															</div>
														</li>
													{/each}
												</ul>
											</section>
										{/each}
									</div>
								{:else if httpView === 'headers'}
									{#if headerEntries.length}
										<div class="divide-y divide-border/60 rounded-md border border-border">
											{#each headerEntries as [k, v] (k)}
												<div class="grid grid-cols-[10rem_1fr] gap-3 px-3 py-1.5 text-xs">
													<span class="truncate font-mono font-medium text-muted-foreground"
														>{k}</span
													>
													<span class="font-mono break-all">{fmtHeader(v)}</span>
												</div>
											{/each}
										</div>
									{:else}
										{@render emptyNote('No headers captured', null)}
									{/if}
								{:else}
									{@const body = httpView === 'request' ? detail.raw_request : rawResponse}
									{#if body}
										<CodeBlock
											code={body}
											lang="http"
											label={httpView === 'request' ? 'Request' : 'Response'}
											maxHeight="60vh"
											maxLines={0}
										/>
									{:else}
										{@render emptyNote(`No raw ${httpView} captured`, null)}
									{/if}
								{/if}
							</div>
						{:else if corrErrored}
							{@render corrState()}
						{:else if detailErrored && primaryAsset}
							{@const assetId = primaryAsset.id}
							{@const name = sub.name}
							<EmptyState compact icon={TriangleAlert} title="HTTP capture not loaded">
								<Button variant="outline" size="sm" onclick={() => loadDetail(assetId, name)}>
									Retry
								</Button>
							</EmptyState>
						{:else}
							{@render emptyNote('No HTTP capture', null)}
						{/if}
					</Tabs.Content>

					<Tabs.Content value="services" class="m-0 flex flex-col gap-6 p-5">
						{#if corrLoading || corrErrored}
							{@render corrState()}
						{:else}
							{#if hostAssets.length}
								<section class="flex flex-col gap-2">
									<SectionHead icon={Globe} title="Web services" />
									<Item.Group class="gap-0.5">
										{#each hostAssets as a (a.id)}
											<Item.Root size="sm" variant="outline">
												<Item.Media>
													<span
														class="size-2 rounded-full {STATUS_DOT[httpStatusClass(a.status_code)]}"
														aria-hidden="true"
													></span>
												</Item.Media>
												<Item.Content class="gap-0">
													<Item.Title class="font-mono text-xs font-normal">
														{a.scheme}://{hostPort(a.host, a.port)}
													</Item.Title>
													{#if a.title}
														<Item.Description class="text-xs">{a.title}</Item.Description>
													{/if}
													{#if a.ai_service}
														<Item.Description class="flex items-center gap-1 text-xs">
															<AI_ICON class="size-3" />
															{aiServiceLabel(a.ai_service)}
														</Item.Description>
													{/if}
												</Item.Content>
												<Item.Actions class="gap-2">
													<span class="font-mono text-xs {httpStatusTextClass(a.status_code)}">
														{a.status_code ?? '—'}
													</span>
													<Button
														variant="ghost"
														size="icon"
														class="size-7"
														href={externalHref(a.url)}
														target="_blank"
														rel="noreferrer noopener"
														aria-label="Open {a.url}"
													>
														<ExternalLink />
													</Button>
												</Item.Actions>
											</Item.Root>
										{/each}
									</Item.Group>
								</section>
							{/if}
							{#if ports.length}
								<section class="flex flex-col gap-2">
									<SectionHead icon={Plug} title="Open ports" />
									<div class="flex flex-wrap gap-1">
										{#each ports as p (p.id)}
											{@render chip(
												`${p.number}${p.service_name ? `/${p.service_name}` : ''}`,
												`port:${p.number}`,
												true,
												isSensitivePort(p.number) ? 'Sensitive service' : undefined,
												isSensitivePort(p.number)
											)}
										{/each}
									</div>
								</section>
							{/if}
							{#if ipMetas.length}
								<section class="flex flex-col gap-2">
									<SectionHead icon={Network} title="Network" />
									<Item.Group class="gap-0.5">
										{#each ipMetas as m (m.ip)}
											<Item.Root size="sm" variant="outline">
												<Item.Content class="gap-0">
													<Item.Title class="font-mono text-xs font-normal">{m.ip}</Item.Title>
													<Item.Description class="text-xs">
														{[m.asn ? `AS${m.asn}` : null, m.asn_org, m.country]
															.filter(Boolean)
															.join(' · ') || 'No network data'}
													</Item.Description>
												</Item.Content>
												<Item.Actions>
													{#if m.is_cdn}
														<Badge variant="info" class="font-normal">{m.cdn_name ?? 'CDN'}</Badge>
													{/if}
													<Button
														variant="ghost"
														size="sm"
														class="h-7 text-xs"
														onclick={() => onFilter?.(`ip:${m.ip}`)}
													>
														<Filter data-icon="inline-start" />
														{WEB.label}
													</Button>
												</Item.Actions>
											</Item.Root>
										{/each}
									</Item.Group>
								</section>
							{/if}
							{#if !hostAssets.length && !ports.length && !ipMetas.length}
								{@render emptyNote('No services', 'No web services, open ports or network data.')}
							{/if}
						{/if}
					</Tabs.Content>

					<Tabs.Content value="related" class="m-0 flex flex-col gap-5 p-5">
						{#if corrLoading || corrErrored}
							{@render corrState()}
						{:else if related.length}
							{#each related as r (r.kind + r.value)}
								<section class="flex flex-col gap-2 rounded-md border border-border p-3">
									<div class="flex items-start gap-2">
										<Link2 class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
										<div class="min-w-0 flex-1">
											<p class="text-xs font-medium">
												{(r.total || r.hosts.length).toLocaleString()}
												{(r.total || r.hosts.length) === 1 ? WEB.noun : WEB.nounPlural}
												{r.reason}
												{#if r.targets > 1}
													<span class="text-muted-foreground">
														· {r.targets} targets
													</span>
												{/if}
											</p>
											<Hint text={r.value}>
												{#snippet child(props)}
													<p {...props} class="truncate font-mono text-2xs text-muted-foreground">
														{r.value}
													</p>
												{/snippet}
											</Hint>
										</div>
										{#if r.query}
											<Button
												variant="outline"
												size="sm"
												class="h-7 shrink-0 text-xs"
												onclick={() => onFilter?.(r.query)}
											>
												<Filter data-icon="inline-start" /> Show in table
											</Button>
										{/if}
									</div>
									<div class="flex flex-wrap items-center gap-1">
										{#each r.hosts.slice(0, MAX_HOSTS) as h (h)}
											<Hint text="Open {h}">
												{#snippet child(props)}
													<button {...props} type="button" onclick={() => onPivot?.(h)}>
														<Badge
															variant="outline"
															class="cursor-pointer font-mono text-2xs font-normal hover:bg-accent"
														>
															{h}
														</Badge>
													</button>
												{/snippet}
											</Hint>
										{/each}
										<OverflowPopover
											items={r.hosts}
											shown={MAX_HOSTS}
											label={WEB.nounPlural}
											mono
											onSelect={(h) => onPivot?.(h)}
										/>
									</div>
								</section>
							{/each}
						{:else}
							{@render emptyNote('No correlated assets', null)}
						{/if}
					</Tabs.Content>

					<Tabs.Content value="structure" class="m-0 p-0">
						{#if tab === 'structure'}
							<HostStructure host={sub.name} {projectId} {scanId} compact {onOpenEndpoints} />
						{/if}
					</Tabs.Content>
				</ScrollArea>
			</Tabs.Root>
		{/if}
	</Sheet.Content>
</Sheet.Root>

{#snippet tabTrigger(value: string, label: string, count: number | null)}
	<Tabs.Trigger
		{value}
		bind:ref={tabRefs[value]}
		class="flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 py-2.5 text-xs font-medium text-muted-foreground shadow-none hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent"
	>
		{label}
		{#if count != null}<span class="text-muted-foreground tabular-nums"
				>{count.toLocaleString()}</span
			>{/if}
	</Tabs.Trigger>
{/snippet}

{#snippet kv(label: string, value: string | number | null | undefined)}
	{#if value !== null && value !== undefined && value !== ''}
		<div class={SHEET_ROW_TIGHT}>
			<dt class={SHEET_DT}>{label}</dt>
			<dd class="min-w-0 text-sm break-words">{value}</dd>
		</div>
	{/if}
{/snippet}

{#snippet chip(text: string, dsl: string, mono = false, hint?: string, warn = false, tech = false)}
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<button {...props} type="button" onclick={() => onFilter?.(dsl)}>
					<Badge
						variant="outline"
						class="max-w-full cursor-pointer text-left font-normal whitespace-normal wrap-anywhere hover:bg-accent {mono
							? 'font-mono text-2xs'
							: ''} {warn ? 'text-warning' : ''}"
					>
						{#if tech}<TechIcon name={text} />{/if}
						{text}
					</Badge>
				</button>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content class="flex items-center gap-1.5">
			{hint ?? 'Filter table'}
			<Fingerprint class="size-3 opacity-60" />
			<span class="font-mono">{dsl}</span>
		</Tooltip.Content>
	</Tooltip.Root>
{/snippet}

{#snippet emptyNote(title: string, description: string | null)}
	<EmptyState compact {title} description={description ?? undefined} />
{/snippet}

{#snippet corrState()}
	{#if corrLoading}
		<div class="flex flex-col gap-2">
			<Skeleton class="h-8 w-full" />
			<Skeleton class="h-24 w-full" />
		</div>
	{:else}
		<EmptyState compact icon={TriangleAlert} title="Correlation not loaded">
			<Button variant="outline" size="sm" onclick={() => sub && loadCorrelation(sub.name)}>
				Retry
			</Button>
		</EmptyState>
	{/if}
{/snippet}
