<script module lang="ts">
	const ROW = 'grid grid-cols-[7.5rem_1fr] items-start gap-3 py-2';
	const DT = 'pt-0.5 text-xs text-muted-foreground';
	function relationDsl(kind: string, value: string): string | null {
		switch (kind) {
			case 'ip':
				return `ip:${value}`;
			case 'cname':
				return `cname:${value}`;
			case 'favicon':
				return `favicon:${value}`;
			default:
				return null;
		}
	}
</script>

<script lang="ts">
	import Globe from '@lucide/svelte/icons/globe';
	import Network from '@lucide/svelte/icons/network';
	import Plug from '@lucide/svelte/icons/plug';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Link2 from '@lucide/svelte/icons/link-2';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Copy from '@lucide/svelte/icons/copy';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Star from '@lucide/svelte/icons/star';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Filter from '@lucide/svelte/icons/filter';
	import ImageOff from '@lucide/svelte/icons/image-off';
	import Layers from '@lucide/svelte/icons/layers';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import CornerDownRight from '@lucide/svelte/icons/corner-down-right';
	import type { IconComponent } from '$lib/config/icons';
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
	import { Kbd } from '$lib/components/ui/kbd';
	import ScreenshotThumb from './screenshot-thumb.svelte';
	import OverflowPopover from './web-assets/overflow-popover.svelte';
	import { httpAssetsApi } from '$lib/api/scan-results';
	import { subdomainsApi } from '$lib/api/subdomains';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import type { HttpAssetDetail } from '$lib/types/http-asset';
	import type { SubdomainCorrelation } from '$lib/utilities/scan-insights';
	import {
		certState,
		daysUntilExpiry,
		exactToken,
		relationLabel
	} from '$lib/utilities/scan-insights';
	import {
		formatBytes,
		formatResponseTime,
		httpStatusClass,
		httpStatusReason,
		httpStatusTextClass,
		isPrivateIp,
		isSensitivePort,
		STATUS_DOT
	} from '$lib/utilities/scan-correlation';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import { writeClipboard } from '$lib/utilities/clipboard';

	interface Props {
		sub: SubdomainRead | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		projectId: string;
		scanId: string;
		index?: number;
		pageOffset?: number;
		total?: number;
		onStep?: (dir: -1 | 1) => void;
		onFilter?: (dsl: string) => void;
		onPivot?: (name: string) => void;
	}

	let {
		sub,
		open,
		onOpenChange,
		projectId,
		scanId,
		index = 0,
		pageOffset = 0,
		total = 0,
		onStep,
		onFilter,
		onPivot
	}: Props = $props();

	const MAX_SANS = 4;
	const MAX_HOSTS = 16;

	let tab = $state('overview');
	let contentEl = $state<HTMLElement | null>(null);
	let detail = $state<HttpAssetDetail | null>(null);
	let detailLoading = $state(false);
	let httpView = $state('response');
	let loadedFor = '';
	let corr = $state<SubdomainCorrelation | null>(null);
	let corrLoading = $state(false);
	let corrErrored = $state(false);

	let primaryAsset = $derived(corr?.primary_asset ?? null);
	let hostAssets = $derived(corr?.services ?? []);
	let ports = $derived(corr?.ports ?? []);
	let ipMetas = $derived(corr?.ip_metas ?? []);
	let related = $derived(corr?.related ?? []);
	let relatedHosts = $derived(new Set(related.flatMap((r) => r.hosts)).size);

	function loadCorrelation(name: string) {
		corr = null;
		corrErrored = false;
		corrLoading = true;
		subdomainsApi
			.correlation(projectId, scanId, name)
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

	$effect(() => {
		if (!open || !sub) return;
		const name = sub.name;
		if (loadedFor !== name) {
			loadedFor = name;
			httpView = 'response';
			detail = null;
			detailLoading = false;
			loadCorrelation(name);
		}
		const assetId = corr?.primary_asset?.id;
		if (assetId && !detail && !detailLoading) {
			detailLoading = true;
			const forName = name;
			httpAssetsApi
				.detail(projectId, assetId)
				.then((d) => {
					if (loadedFor === forName) detail = d;
				})
				.catch(() => {
					if (loadedFor === forName) detail = null;
				})
				.finally(() => {
					if (loadedFor === forName) detailLoading = false;
				});
		}
	});

	let hasHttp = $derived(sub?.http_status != null);
	let url = $derived(sub?.http_url ?? (sub ? `https://${sub.name}` : ''));
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
	let position = $derived(pageOffset + index + 1);
	let privateIps = $derived((sub?.resolved_ips ?? []).filter(isPrivateIp));
	let provider = $derived(providerFor(sub?.cname));
	let ProviderIcon = $derived(provider ? PROVIDER_KIND_ICONS[provider.kind] : null);

	function fmtHeader(v: string | string[]): string {
		return Array.isArray(v) ? v.join(', ') : v;
	}
	function copy(text: string) {
		writeClipboard(text);
	}
	function onKey(e: KeyboardEvent) {
		if (!open || e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		if (e.key === 'ArrowDown' || e.key === 'j') {
			e.preventDefault();
			onStep?.(1);
		} else if (e.key === 'ArrowUp' || e.key === 'k') {
			e.preventDefault();
			onStep?.(-1);
		}
	}
</script>

<svelte:window onkeydown={onKey} />

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
			<Sheet.Header class="gap-3 border-b border-border px-5 pt-5 pb-4 pr-12">
				<div class="flex items-center gap-2">
					<span class="size-2 shrink-0 rounded-full {STATUS_DOT[httpStatusClass(sub.http_status)]}"
					></span>
					{#if sub.is_important}<Star class="size-3.5 shrink-0 fill-warning text-warning" />{/if}
					<Sheet.Title class="truncate font-mono text-base font-medium">{sub.name}</Sheet.Title>
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon-sm"
									class="size-7"
									onclick={() => copy(sub.name)}
									aria-label="Copy host"
								>
									<Copy />
								</Button>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>Copy host</Tooltip.Content>
					</Tooltip.Root>
					{#if hasHttp}
						<Tooltip.Root>
							<Tooltip.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="ghost"
										size="icon-sm"
										class="size-7"
										href={url}
										target="_blank"
										rel="noreferrer noopener"
										aria-label="Open in browser"
									>
										<ExternalLink />
									</Button>
								{/snippet}
							</Tooltip.Trigger>
							<Tooltip.Content>Open in browser</Tooltip.Content>
						</Tooltip.Root>
					{/if}
					<div class="ml-auto flex items-center gap-1">
						{#if total > 1}
							<span class="text-xs text-muted-foreground tabular-nums">
								{position.toLocaleString()} / {total.toLocaleString()}
							</span>
							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<Button
											{...props}
											variant="ghost"
											size="icon-sm"
											class="size-7"
											disabled={position <= 1}
											onclick={() => onStep?.(-1)}
											aria-label="Previous host"
										>
											<ChevronUp />
										</Button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content class="flex items-center gap-1.5"
									>Previous <Kbd>k</Kbd></Tooltip.Content
								>
							</Tooltip.Root>
							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<Button
											{...props}
											variant="ghost"
											size="icon-sm"
											class="size-7"
											disabled={position >= total}
											onclick={() => onStep?.(1)}
											aria-label="Next host"
										>
											<ChevronDown />
										</Button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content class="flex items-center gap-1.5"
									>Next <Kbd>j</Kbd></Tooltip.Content
								>
							</Tooltip.Root>
						{/if}
					</div>
				</div>
				<Sheet.Description class="truncate">
					{#if hasHttp}
						<span class="font-mono {httpStatusTextClass(sub.http_status)}">{sub.http_status}</span>
						<span>{httpStatusReason(sub.http_status)}</span>
						{#if sub.page_title}<span aria-hidden="true"> · </span><span>{sub.page_title}</span
							>{/if}
					{:else if sub.resolved_ips?.length}
						Resolves but no web service answered
					{:else}
						Did not resolve to an address
					{/if}
				</Sheet.Description>
				<div class="flex flex-wrap gap-1">
					{#if sub.is_cdn}
						<Badge variant="info" class="font-normal">{sub.cdn_name ?? 'CDN'}</Badge>
					{/if}
					{#if sub.waf}<Badge variant="secondary" class="font-normal">WAF · {sub.waf}</Badge>{/if}
					{#if cert === 'expired'}
						<Badge variant="destructive" class="font-normal">Certificate expired</Badge>
					{:else if cert === 'expiring'}
						<Badge variant="warning" class="font-normal">Certificate expires in {expiryDays}d</Badge
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
			</Sheet.Header>

			<Tabs.Root bind:value={tab} class="flex min-h-0 flex-1 flex-col gap-0">
				<Tabs.List
					class="h-auto w-full justify-start gap-0 rounded-none border-b border-border bg-transparent p-0 px-2"
				>
					{@render tabTrigger('overview', 'Overview', null)}
					{@render tabTrigger('http', 'HTTP', null)}
					{@render tabTrigger('services', 'Services', hostAssets.length + ports.length || null)}
					{@render tabTrigger('related', 'Related', relatedHosts || null)}
				</Tabs.List>

				<ScrollArea class="min-h-0 flex-1">
					<Tabs.Content value="overview" class="m-0 flex flex-col gap-6 p-5">
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
								<span class="text-xs">No screenshot captured</span>
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
										href={sub.final_url}
										target="_blank"
										rel="noreferrer noopener"
										class="ml-1 font-mono break-all hover:underline">{sub.final_url}</a
									>
								</div>
							</div>
						{/if}

						<section class="flex flex-col gap-2">
							{@render heading(Network, 'Identity')}
							<dl class="flex flex-col divide-y divide-border/60">
								<div class={ROW}>
									<dt class={DT}>Resolves to</dt>
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
									<div class={ROW}>
										<dt class={DT}>CNAME</dt>
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
														{PROVIDER_KIND_LABELS[prov.kind]} · filter hosts on {prov.label}
													</Tooltip.Content>
												</Tooltip.Root>
											{/if}
											{@render chip(sub.cname, `cname:${sub.cname}`, true)}
										</dd>
									</div>
								{/if}
								{#if sub.asn}
									<div class={ROW}>
										<dt class={DT}>Network</dt>
										<dd class="text-sm">
											<span class="font-mono">AS{sub.asn}</span>
											{#if sub.asn_org}<span class="text-muted-foreground">
													· {sub.asn_org}</span
												>{/if}
										</dd>
									</div>
								{/if}
								<div class={ROW}>
									<dt class={DT}>Discovered via</dt>
									<dd class="flex flex-wrap gap-1">
										{#each sub.sources ?? [] as src (src)}
											{@render chip(src, `source:${src}`)}
										{/each}
									</dd>
								</div>
								<div class={ROW}>
									<dt class={DT}>First seen</dt>
									<dd class="text-sm" title={sub.discovered_at}>
										{formatShortDate(sub.discovered_at)}
										<span class="text-muted-foreground">· {relativeTime(sub.discovered_at)}</span>
									</dd>
								</div>
								{#if sub.favicon_hash}
									<div class={ROW}>
										<dt class={DT}>Favicon</dt>
										<dd>
											{@render chip(
												sub.favicon_hash,
												`favicon:${sub.favicon_hash}`,
												true,
												'Filter hosts sharing this favicon'
											)}
											{#if (sub.favicon_count ?? 0) > 1}
												<span class="ml-1 text-xs text-muted-foreground">
													shared by {sub.favicon_count} hosts
												</span>
											{/if}
										</dd>
									</div>
								{/if}
							</dl>
						</section>

						{#if hasHttp}
							<section class="flex flex-col gap-2">
								{@render heading(Globe, 'Web service')}
								<dl class="flex flex-col divide-y divide-border/60">
									<div class={ROW}>
										<dt class={DT}>URL</dt>
										<dd>
											<a
												href={url}
												target="_blank"
												rel="noreferrer noopener"
												class="font-mono text-sm break-all hover:underline">{url}</a
											>
										</dd>
									</div>
									{#if sub.page_title}
										<div class={ROW}>
											<dt class={DT}>Page title</dt>
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
														{sub.title_count} hosts show this page
													</Button>
												{/if}
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
											detail?.lines != null ? `${detail.lines} lines` : null,
											detail?.words != null ? `${detail.words} words` : null
										]
											.filter(Boolean)
											.join(' · ') || null
									)}
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
											? 'The host resolves, but nothing answered on the probed web ports.'
											: 'The name did not resolve, so it was not probed.'}
									</p>
								</div>
							</div>
						{/if}

						{#if sub.tech.length || detail?.cpe?.length}
							<section class="flex flex-col gap-2">
								{@render heading(Layers, 'Technologies')}
								<div class="flex flex-wrap gap-1">
									{#each sub.tech as t (t)}
										{@render chip(t, `tech:${t}`)}
									{/each}
								</div>
								{#if detail?.cpe?.length}
									<div class="flex flex-wrap gap-1">
										{#each detail.cpe as c (c)}
											<Badge variant="secondary" class="font-mono text-[10px] font-normal"
												>{c}</Badge
											>
										{/each}
									</div>
								{/if}
							</section>
						{/if}

						{#if sub.tls_not_after || primaryAsset?.tls_version}
							<section class="flex flex-col gap-2">
								<div class="flex items-center justify-between">
									{@render heading(
										sub.tls_expired || sub.tls_self_signed ? ShieldAlert : ShieldCheck,
										'TLS certificate'
									)}
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
													? '[&>div]:bg-destructive'
													: cert === 'expiring'
														? '[&>div]:bg-warning'
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
											<div class={ROW}>
												<dt class={DT}>SANs</dt>
												<dd class="flex flex-wrap items-center gap-1">
													{#each primaryAsset.tls_sans.slice(0, MAX_SANS) as san (san)}
														<Badge variant="outline" class="font-mono text-[10px] font-normal"
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
											<div class={ROW}>
												<dt class={DT}>Fingerprint</dt>
												<dd class="flex items-center gap-1">
													<span class="truncate font-mono text-xs"
														>{primaryAsset.tls_fingerprint}</span
													>
													<Button
														variant="ghost"
														size="icon-sm"
														class="size-6 shrink-0"
														onclick={() => copy(primaryAsset?.tls_fingerprint ?? '')}
														aria-label="Copy fingerprint"
													>
														<Copy />
													</Button>
												</dd>
											</div>
										{/if}
									</dl>
								{/if}
							</section>
						{/if}
					</Tabs.Content>

					<Tabs.Content value="http" class="m-0 p-5">
						{#if !hasHttp}
							{@render emptyNote('No HTTP capture', 'This host has no live web service.')}
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
									</ToggleGroup.Root>
									<Button
										variant="ghost"
										size="sm"
										class="h-7 text-xs"
										onclick={() =>
											copy(httpView === 'request' ? (detail?.raw_request ?? '') : rawResponse)}
									>
										<Copy data-icon="inline-start" /> Copy
									</Button>
								</div>
								{#if httpView === 'headers'}
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
										<ScrollArea class="max-h-[60vh] rounded-md border border-border bg-muted/30">
											<pre
												class="p-3 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap">{body}</pre>
										</ScrollArea>
									{:else}
										{@render emptyNote(`No raw ${httpView} captured`, null)}
									{/if}
								{/if}
							</div>
						{:else}
							{@render emptyNote('Could not load the HTTP capture', null)}
						{/if}
					</Tabs.Content>

					<Tabs.Content value="services" class="m-0 flex flex-col gap-6 p-5">
						{#if corrLoading || corrErrored}
							{@render corrState()}
						{:else}
							{#if hostAssets.length}
								<section class="flex flex-col gap-2">
									{@render heading(Globe, 'Web services')}
									<Item.Group class="gap-0.5">
										{#each hostAssets as a (a.id)}
											<Item.Root size="sm" variant="outline">
												<Item.Media>
													<span
														class="size-2 rounded-full {STATUS_DOT[httpStatusClass(a.status_code)]}"
													></span>
												</Item.Media>
												<Item.Content class="gap-0">
													<Item.Title class="font-mono text-xs font-normal">
														{a.scheme}://{a.host}:{a.port}
													</Item.Title>
													{#if a.title}
														<Item.Description class="text-xs">{a.title}</Item.Description>
													{/if}
												</Item.Content>
												<Item.Actions class="gap-2">
													<span class="font-mono text-xs {httpStatusTextClass(a.status_code)}">
														{a.status_code ?? '—'}
													</span>
													<Button
														variant="ghost"
														size="icon-sm"
														class="size-6"
														href={a.url}
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
									{@render heading(Plug, 'Open ports')}
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
									{@render heading(Network, 'Network')}
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
														<Filter data-icon="inline-start" /> Hosts
													</Button>
												</Item.Actions>
											</Item.Root>
										{/each}
									</Item.Group>
								</section>
							{/if}
							{#if !hostAssets.length && !ports.length && !ipMetas.length}
								{@render emptyNote(
									'No services correlated',
									'No web services, open ports or network data for this host.'
								)}
							{/if}
						{/if}
					</Tabs.Content>

					<Tabs.Content value="related" class="m-0 flex flex-col gap-5 p-5">
						{#if corrLoading || corrErrored}
							{@render corrState()}
						{:else if related.length}
							{#each related as r (r.kind + r.value)}
								{@const dsl = relationDsl(r.kind, r.value)}
								<section class="flex flex-col gap-2 rounded-md border border-border p-3">
									<div class="flex items-start gap-2">
										<Link2 class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
										<div class="min-w-0 flex-1">
											<p class="text-xs font-medium">
												{r.hosts.length}
												{r.hosts.length === 1 ? 'host' : 'hosts'}
												{relationLabel(r)}
											</p>
											<p
												class="truncate font-mono text-[11px] text-muted-foreground"
												title={r.value}
											>
												{r.value}
											</p>
										</div>
										{#if dsl}
											<Button
												variant="outline"
												size="sm"
												class="h-7 shrink-0 text-xs"
												onclick={() => onFilter?.(dsl)}
											>
												<Filter data-icon="inline-start" /> Show in table
											</Button>
										{/if}
									</div>
									<div class="flex flex-wrap items-center gap-1">
										{#each r.hosts.slice(0, MAX_HOSTS) as h (h)}
											<button type="button" onclick={() => onPivot?.(h)} title="Open {h}">
												<Badge
													variant="outline"
													class="cursor-pointer font-mono text-[10px] font-normal hover:bg-accent"
												>
													{h}
												</Badge>
											</button>
										{/each}
										<OverflowPopover
											items={r.hosts}
											shown={MAX_HOSTS}
											label="hosts"
											mono
											onSelect={(h) => onPivot?.(h)}
										/>
									</div>
								</section>
							{/each}
						{:else}
							{@render emptyNote(
								'No correlated assets',
								'This host shares no IP, certificate, favicon or CNAME with other hosts in the scan.'
							)}
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
		class="flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 py-2.5 text-xs font-medium text-muted-foreground shadow-none hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent"
	>
		{label}
		{#if count != null}<span class="text-muted-foreground tabular-nums">{count}</span>{/if}
	</Tabs.Trigger>
{/snippet}

{#snippet heading(Icon: IconComponent, title: string)}
	<div
		class="flex items-center gap-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase"
	>
		<Icon class="size-3.5" />
		<span>{title}</span>
	</div>
{/snippet}

{#snippet kv(label: string, value: string | number | null | undefined)}
	{#if value !== null && value !== undefined && value !== ''}
		<div class={ROW}>
			<dt class={DT}>{label}</dt>
			<dd class="min-w-0 text-sm break-words">{value}</dd>
		</div>
	{/if}
{/snippet}

{#snippet chip(text: string, dsl: string, mono = false, hint?: string, warn = false)}
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<button {...props} type="button" onclick={() => onFilter?.(dsl)}>
					<Badge
						variant="outline"
						class="cursor-pointer font-normal hover:bg-accent {mono
							? 'font-mono text-[10px]'
							: ''} {warn ? 'text-warning' : ''}"
					>
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
	<div class="flex flex-col items-center gap-1 py-10 text-center">
		<p class="text-sm font-medium">{title}</p>
		{#if description}<p class="max-w-xs text-xs text-muted-foreground">{description}</p>{/if}
	</div>
{/snippet}

{#snippet corrState()}
	{#if corrLoading}
		<div class="flex flex-col gap-2">
			<Skeleton class="h-8 w-full" />
			<Skeleton class="h-24 w-full" />
		</div>
	{:else}
		<div class="flex flex-col items-center gap-2 py-10 text-xs text-muted-foreground">
			<TriangleAlert class="size-5 text-destructive" />
			Correlation could not be loaded.
			<Button variant="outline" size="sm" onclick={() => sub && loadCorrelation(sub.name)}>
				Retry
			</Button>
		</div>
	{/if}
{/snippet}
