<script lang="ts">
	import Globe from '@lucide/svelte/icons/globe';
	import Server from '@lucide/svelte/icons/server';
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
	import type { IconComponent } from '$lib/config/icons';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Tabs from '$lib/components/ui/tabs';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import ScreenshotThumb from './screenshot-thumb.svelte';
	import TechBadges from './tech-badges.svelte';
	import { httpAssetsApi } from '$lib/api/scan-results';
	import { subdomainsApi } from '$lib/api/subdomains';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import type { HttpAssetDetail } from '$lib/types/http-asset';
	import type { SubdomainCorrelation } from '$lib/utilities/scan-insights';
	import { certState, daysUntilExpiry } from '$lib/utilities/scan-insights';
	import {
		formatBytes,
		formatResponseTime,
		httpStatusTextClass,
		isSensitivePort
	} from '$lib/utilities/scan-correlation';
	import { formatShortDate } from '$lib/utilities/dates';
	import { writeClipboard } from '$lib/utilities/clipboard';

	interface Props {
		sub: SubdomainRead | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		projectId: string;
		scanId: string;
		index?: number;
		total?: number;
		onStep?: (dir: -1 | 1) => void;
		onHost?: (name: string) => void;
	}

	let {
		sub,
		open,
		onOpenChange,
		projectId,
		scanId,
		index = 0,
		total = 0,
		onStep,
		onHost
	}: Props = $props();

	let tab = $state('overview');
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
			tab = 'overview';
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

	let url = $derived(sub?.http_url ?? (sub ? `https://${sub.name}` : ''));
	let redirected = $derived(!!sub?.final_url && sub.final_url !== sub.http_url);
	let cert = $derived(sub ? certState(sub) : null);
	let expiryDays = $derived(sub ? daysUntilExpiry(sub) : null);
	let rawResponse = $derived(
		detail ? [detail.raw_response_header, detail.response_body].filter(Boolean).join('\n\n') : ''
	);
	let headerEntries = $derived(detail ? Object.entries(detail.response_headers ?? {}) : []);

	function fmtHeader(v: string | string[]): string {
		return Array.isArray(v) ? v.join(', ') : v;
	}
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
		{#if sub}
			<Sheet.Header class="gap-2 border-b border-border p-4">
				<div class="flex items-center gap-2">
					<Badge
						variant="outline"
						class="font-mono text-[11px] {httpStatusTextClass(sub.http_status)}"
					>
						{sub.http_status ?? '—'}
					</Badge>
					{#if sub.is_important}<Star class="size-3.5 fill-warning text-warning" />{/if}
					<Sheet.Title class="truncate font-mono text-sm">{sub.name}</Sheet.Title>
					<Button
						variant="ghost"
						size="icon"
						class="size-6"
						onclick={() => writeClipboard(sub.name)}
						aria-label="Copy host"
					>
						<Copy class="size-3" />
					</Button>
					<div class="ml-auto flex items-center gap-1">
						{#if total > 1}
							<span class="text-xs tabular-nums text-muted-foreground">{index + 1} / {total}</span>
							<Button
								variant="ghost"
								size="icon"
								class="size-7"
								onclick={() => onStep?.(-1)}
								aria-label="Previous"
							>
								<ChevronUp class="size-4" />
							</Button>
							<Button
								variant="ghost"
								size="icon"
								class="size-7"
								onclick={() => onStep?.(1)}
								aria-label="Next"
							>
								<ChevronDown class="size-4" />
							</Button>
						{/if}
					</div>
				</div>
				<div class="flex items-center gap-2">
					<a
						href={url}
						target="_blank"
						rel="noreferrer noopener"
						class="flex min-w-0 items-center gap-1 truncate text-xs text-info hover:underline"
					>
						<span class="truncate">{url}</span>
						<ExternalLink class="size-3 shrink-0" />
					</a>
					{#each (sub.resolved_ips ?? []).slice(0, 1) as ip (ip)}
						<button
							type="button"
							class="font-mono text-xs text-muted-foreground hover:text-foreground"
							onclick={() => writeClipboard(ip)}
						>
							{ip}
						</button>
					{/each}
				</div>
				{#if sub.page_title}
					<p class="truncate text-sm text-muted-foreground">{sub.page_title}</p>
				{/if}
			</Sheet.Header>

			<Tabs.Root bind:value={tab} class="flex min-h-0 flex-1 flex-col gap-0">
				<Tabs.List
					class="h-9 w-full justify-start gap-1 overflow-x-auto rounded-none border-b bg-transparent px-2"
				>
					<Tabs.Trigger value="overview" class="text-xs">Overview</Tabs.Trigger>
					<Tabs.Trigger value="http" class="text-xs">HTTP</Tabs.Trigger>
					<Tabs.Trigger value="screenshot" class="text-xs">Shot</Tabs.Trigger>
					<Tabs.Trigger value="tech" class="text-xs">Tech</Tabs.Trigger>
					<Tabs.Trigger value="services" class="text-xs">
						Services {#if hostAssets.length}<span class="text-muted-foreground"
								>{hostAssets.length}</span
							>{/if}
					</Tabs.Trigger>
					<Tabs.Trigger value="tls" class="text-xs">TLS</Tabs.Trigger>
					<Tabs.Trigger value="related" class="text-xs">
						Related {#if related.length}<span class="text-muted-foreground">{related.length}</span
							>{/if}
					</Tabs.Trigger>
				</Tabs.List>

				<ScrollArea class="min-h-0 flex-1">
					<Tabs.Content value="overview" class="m-0 p-4">
						<div class="flex flex-col gap-5">
							{#if sub.screenshot_path}
								<ScreenshotThumb
									path={sub.screenshot_path}
									alt={sub.name}
									class="aspect-video w-full"
								/>
							{/if}
							{#if redirected}
								<div class="rounded-md border border-info/30 bg-info/5 p-2 text-xs">
									<span class="text-muted-foreground">Redirects to </span>
									<span class="break-all font-mono text-info">{sub.final_url}</span>
								</div>
							{/if}
							<div class="flex flex-wrap gap-1">
								{#if sub.is_cdn}
									<Badge variant="info" class="font-normal"
										>CDN{sub.cdn_name ? `: ${sub.cdn_name}` : ''}</Badge
									>
								{/if}
								{#if sub.waf}<Badge variant="secondary" class="font-normal">WAF: {sub.waf}</Badge
									>{/if}
								{#if cert === 'expired'}<Badge variant="destructive" class="font-normal"
										>Cert expired</Badge
									>
								{:else if cert === 'expiring'}<Badge variant="warning" class="font-normal"
										>Cert {expiryDays}d</Badge
									>
								{:else if cert === 'self-signed'}<Badge variant="warning" class="font-normal"
										>Self-signed</Badge
									>{/if}
							</div>
							<div class="divide-y divide-border/60">
								{@render field('Status', sub.http_status)}
								{@render field('Title', sub.page_title)}
								{@render field('Web server', sub.webserver)}
								{@render field('Content-Type', sub.content_type)}
								{@render field(
									'Content-Length',
									sub.content_length != null ? formatBytes(sub.content_length) : null
								)}
								{@render field(
									'Response time',
									sub.response_time != null ? formatResponseTime(sub.response_time) : null
								)}
								{@render field(
									'Resolved IPs',
									sub.resolved_ips?.length ? sub.resolved_ips.join(', ') : null
								)}
								{@render field('CNAME', sub.cname)}
								{@render field(
									'Network',
									sub.asn ? `AS${sub.asn}${sub.asn_org ? ` · ${sub.asn_org}` : ''}` : null
								)}
								{@render field(
									'Discovered via',
									sub.sources?.length ? sub.sources.join(', ') : null
								)}
							</div>
						</div>
					</Tabs.Content>

					<Tabs.Content value="http" class="m-0 p-4">
						{#if !primaryAsset}
							<p class="py-8 text-center text-xs text-muted-foreground">
								No live web service on this host.
							</p>
						{:else if detailLoading && !detail}
							<div class="flex flex-col gap-2">
								<Skeleton class="h-8 w-40" />
								<Skeleton class="h-64 w-full" />
							</div>
						{:else if detail}
							<div class="flex flex-col gap-3">
								<div class="flex items-center justify-between">
									<ToggleGroup.Root type="single" bind:value={httpView} variant="outline" size="sm">
										<ToggleGroup.Item value="response" class="text-xs">Response</ToggleGroup.Item>
										<ToggleGroup.Item value="headers" class="text-xs">Headers</ToggleGroup.Item>
										<ToggleGroup.Item value="request" class="text-xs">Request</ToggleGroup.Item>
									</ToggleGroup.Root>
									<Button
										variant="ghost"
										size="sm"
										class="h-7 gap-1 text-xs"
										onclick={() =>
											writeClipboard(
												httpView === 'request' ? (detail?.raw_request ?? '') : rawResponse
											)}
									>
										<Copy class="size-3" /> Copy
									</Button>
								</div>
								{#if httpView === 'headers'}
									{#if headerEntries.length}
										<div class="divide-y divide-border/60 rounded-md border">
											{#each headerEntries as [k, v] (k)}
												<div class="flex gap-3 px-2 py-1 text-xs">
													<span class="shrink-0 font-mono font-medium text-muted-foreground"
														>{k}</span
													>
													<span class="break-all text-right font-mono">{fmtHeader(v)}</span>
												</div>
											{/each}
										</div>
									{:else}
										<p class="py-6 text-center text-xs text-muted-foreground">
											No parsed headers captured.
										</p>
									{/if}
								{:else}
									{@const body = httpView === 'request' ? detail.raw_request : rawResponse}
									{#if body}
										<ScrollArea class="max-h-[60vh] rounded-md border bg-muted/30">
											<pre
												class="p-3 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap">{body}</pre>
										</ScrollArea>
										{#if httpView === 'response' && detail.content_length != null}
											<p class="text-[11px] text-muted-foreground">
												{formatBytes(detail.content_length)} · {detail.lines ?? '—'} lines · {detail.words ??
													'—'} words
											</p>
										{/if}
									{:else}
										<p class="py-6 text-center text-xs text-muted-foreground">
											No raw {httpView} captured.
										</p>
									{/if}
								{/if}
							</div>
						{:else}
							<p class="py-8 text-center text-xs text-muted-foreground">
								Could not load HTTP capture.
							</p>
						{/if}
					</Tabs.Content>

					<Tabs.Content value="screenshot" class="m-0 p-4">
						{#if sub.screenshot_path}
							<ScreenshotThumb path={sub.screenshot_path} alt={sub.name} class="w-full" />
						{:else}
							<p class="py-8 text-center text-xs text-muted-foreground">
								No screenshot for this host.
							</p>
						{/if}
					</Tabs.Content>

					<Tabs.Content value="tech" class="m-0 p-4">
						{#if sub.tech.length || (detail?.cpe?.length ?? 0)}
							<div class="flex flex-col gap-3">
								{@render heading(Server, 'Technologies')}
								<TechBadges tech={sub.tech} max={60} />
								{#if detail?.cpe?.length}
									<div class="flex flex-col gap-1">
										{@render heading(Server, 'CPE')}
										<div class="flex flex-wrap gap-1">
											{#each detail.cpe as c (c)}
												<Badge variant="secondary" class="font-mono text-[10px] font-normal"
													>{c}</Badge
												>
											{/each}
										</div>
									</div>
								{/if}
							</div>
						{:else}
							<p class="py-8 text-center text-xs text-muted-foreground">
								No technologies fingerprinted.
							</p>
						{/if}
					</Tabs.Content>

					<Tabs.Content value="services" class="m-0 p-4">
						{#if corrLoading || corrErrored}
							{@render corrState()}
						{:else}
							<div class="flex flex-col gap-4">
								{#if hostAssets.length}
									<div class="flex flex-col gap-1">
										{@render heading(Globe, 'Web services')}
										<div class="divide-y divide-border/60 rounded-md border">
											{#each hostAssets as a (a.id)}
												<div class="flex items-center gap-2 px-2 py-1.5 text-xs">
													<Badge
														variant="outline"
														class="font-mono {httpStatusTextClass(a.status_code)}"
													>
														{a.status_code ?? '—'}
													</Badge>
													<span class="font-mono">{a.scheme}://{a.host}:{a.port}</span>
													<span class="truncate text-muted-foreground">{a.title ?? ''}</span>
												</div>
											{/each}
										</div>
									</div>
								{/if}
								{#if ports.length}
									<div class="flex flex-col gap-1.5">
										{@render heading(Plug, 'Open ports')}
										<div class="flex flex-wrap gap-1">
											{#each ports as p (p.id)}
												<Badge
													variant="outline"
													class="font-mono text-[11px] font-normal {isSensitivePort(p.number)
														? 'text-warning'
														: ''}"
												>
													{p.number}{p.service_name ? `/${p.service_name}` : ''}
												</Badge>
											{/each}
										</div>
									</div>
								{/if}
								{#if ipMetas.length}
									<div class="flex flex-col gap-1">
										{@render heading(Network, 'Network')}
										<div class="divide-y divide-border/60">
											{#each ipMetas as m (m.ip)}
												{@render field(
													m.ip,
													[m.asn ? `AS${m.asn}` : null, m.asn_org, m.country]
														.filter(Boolean)
														.join(' · ') || null
												)}
											{/each}
										</div>
									</div>
								{/if}
								{#if !hostAssets.length && !ports.length && !ipMetas.length}
									<p class="py-8 text-center text-xs text-muted-foreground">
										No services or ports correlated.
									</p>
								{/if}
							</div>
						{/if}
					</Tabs.Content>

					<Tabs.Content value="tls" class="m-0 p-4">
						{#if corrLoading || corrErrored}
							{@render corrState()}
						{:else if primaryAsset?.tls_version || sub.tls_not_after}
							<div class="flex flex-col gap-2">
								<div class="flex items-center justify-between">
									{@render heading(
										sub.tls_expired || sub.tls_self_signed ? ShieldAlert : ShieldCheck,
										'TLS certificate'
									)}
									<div class="flex gap-1">
										{#if sub.tls_expired}<Badge variant="destructive" class="font-normal"
												>Expired</Badge
											>{/if}
										{#if sub.tls_self_signed}<Badge variant="warning" class="font-normal"
												>Self-signed</Badge
											>{/if}
									</div>
								</div>
								<div class="divide-y divide-border/60">
									{@render field('Version', primaryAsset?.tls_version)}
									{@render field('Cipher', detail?.tls_cipher ?? primaryAsset?.tls_cipher)}
									{@render field('Subject CN', primaryAsset?.tls_subject_cn)}
									{@render field(
										'SANs',
										primaryAsset?.tls_sans?.length ? primaryAsset.tls_sans.join(', ') : null
									)}
									{@render field(
										'Issuer',
										primaryAsset?.tls_issuer_org ?? primaryAsset?.tls_issuer
									)}
									{@render field('Serial', primaryAsset?.tls_serial)}
									{@render field('Fingerprint', primaryAsset?.tls_fingerprint)}
									{@render field(
										'Valid from',
										primaryAsset?.tls_not_before
											? formatShortDate(primaryAsset.tls_not_before)
											: null
									)}
									{@render field(
										'Valid until',
										sub.tls_not_after ? formatShortDate(sub.tls_not_after) : null
									)}
								</div>
							</div>
						{:else}
							<p class="py-8 text-center text-xs text-muted-foreground">
								No TLS certificate (host not served over HTTPS).
							</p>
						{/if}
					</Tabs.Content>

					<Tabs.Content value="related" class="m-0 p-4">
						{#if corrLoading || corrErrored}
							{@render corrState()}
						{:else if related.length}
							<div class="flex flex-col gap-4">
								{#each related as r (r.kind + r.value)}
									<div class="flex flex-col gap-1.5">
										<div class="flex items-center gap-1.5 text-xs font-medium">
											<Link2 class="size-3.5 text-muted-foreground" />
											{r.reason}
											<Badge variant="secondary" class="ml-auto rounded-sm px-1 font-normal"
												>{r.hosts.length}</Badge
											>
										</div>
										<div class="flex flex-wrap gap-1">
											{#each r.hosts.slice(0, 24) as h (h)}
												<button type="button" onclick={() => onHost?.(h)}>
													<Badge
														variant="outline"
														class="cursor-pointer font-mono text-[10px] font-normal hover:bg-accent"
														>{h}</Badge
													>
												</button>
											{/each}
											{#if r.hosts.length > 24}
												<span class="text-xs text-muted-foreground">+{r.hosts.length - 24}</span>
											{/if}
										</div>
									</div>
								{/each}
							</div>
						{:else}
							<p class="py-8 text-center text-xs text-muted-foreground">
								No correlated assets — this host shares no IP, cert, favicon, or CNAME.
							</p>
						{/if}
					</Tabs.Content>
				</ScrollArea>
			</Tabs.Root>
		{/if}
	</Sheet.Content>
</Sheet.Root>

{#snippet heading(Icon: IconComponent, title: string)}
	<div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
		<Icon class="size-3.5" />
		<span class="tracking-wide uppercase">{title}</span>
	</div>
{/snippet}

{#snippet field(label: string, value: string | number | null | undefined)}
	{#if value !== null && value !== undefined && value !== ''}
		<div class="flex justify-between gap-4 py-1 text-xs">
			<span class="shrink-0 text-muted-foreground">{label}</span>
			<span class="break-all text-right font-mono">{value}</span>
		</div>
	{/if}
{/snippet}

{#snippet corrState()}
	{#if corrLoading}
		<div class="flex flex-col gap-2 py-2">
			<Skeleton class="h-8 w-full" />
			<Skeleton class="h-24 w-full" />
		</div>
	{:else}
		<div class="flex flex-col items-center gap-2 py-8 text-xs text-muted-foreground">
			<TriangleAlert class="size-5 text-destructive" />
			Couldn't load correlation.
			<button
				type="button"
				class="text-info hover:underline"
				onclick={() => sub && loadCorrelation(sub.name)}>Retry</button
			>
		</div>
	{/if}
{/snippet}
