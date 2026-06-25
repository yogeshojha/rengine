<script lang="ts">
	import Globe from '@lucide/svelte/icons/globe';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Server from '@lucide/svelte/icons/server';
	import Network from '@lucide/svelte/icons/network';
	import Plug from '@lucide/svelte/icons/plug';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import type { Snippet } from 'svelte';
	import type { IconComponent } from '$lib/config/icons';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import ScreenshotThumb from './screenshot-thumb.svelte';
	import TechBadges from './tech-badges.svelte';
	import type { HttpAssetRead } from '$lib/types/http-asset';
	import type { IpAddressRead } from '$lib/types/ip-address';
	import type { PortRead } from '$lib/types/port';
	import { formatShortDate } from '$lib/utilities/dates';
	import {
		formatBytes,
		formatResponseTime,
		httpStatusTextClass
	} from '$lib/utilities/scan-correlation';

	interface Props {
		asset: HttpAssetRead | null;
		ipMeta?: IpAddressRead | null;
		ports?: PortRead[];
		neighbors?: string[];
		open: boolean;
		onOpenChange: (open: boolean) => void;
	}

	let { asset, ipMeta = null, ports = [], neighbors = [], open, onOpenChange }: Props = $props();

	let redirected = $derived(!!asset?.final_url && asset.final_url !== asset.url);
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
		{#if asset}
			<Sheet.Header class="space-y-2 border-b border-border p-4">
				<div class="flex items-center gap-2">
					<Badge
						variant="outline"
						class="font-mono text-[11px] {httpStatusTextClass(asset.status_code)}"
					>
						{asset.status_code ?? '—'}
					</Badge>
					<Sheet.Title class="truncate font-mono text-sm">{asset.host}</Sheet.Title>
				</div>
				<a
					href={asset.url}
					target="_blank"
					rel="noreferrer noopener"
					class="flex items-center gap-1 truncate text-xs text-info hover:underline"
				>
					{asset.url}
					<ExternalLink class="h-3 w-3 shrink-0" />
				</a>
				{#if asset.title}
					<p class="text-sm text-muted-foreground">{asset.title}</p>
				{/if}
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="space-y-5 p-4">
					{#if asset.screenshot_path}
						<ScreenshotThumb
							path={asset.screenshot_path}
							alt={asset.host}
							class="aspect-video w-full"
						/>
					{/if}

					{#if redirected}
						<div class="rounded-md border border-info/30 bg-info/5 p-2 text-xs">
							<span class="text-muted-foreground">Redirects to</span>
							<span class="break-all font-mono text-info">{asset.final_url}</span>
						</div>
					{/if}

					{@render section(Globe, 'Response', responseFields)}
					{@render section(Fingerprint, 'Fingerprint', fingerprintFields)}

					{#if asset.tech.length || asset.cpe.length}
						<div class="space-y-2">
							{@render heading(Server, 'Technology')}
							<TechBadges tech={asset.tech} max={50} />
							{#if asset.cpe.length}
								<div class="flex flex-wrap gap-1">
									{#each asset.cpe as c (c)}
										<Badge variant="secondary" class="font-mono text-[10px] font-normal">{c}</Badge>
									{/each}
								</div>
							{/if}
						</div>
					{/if}

					{@render networkSection()}
					{@render tlsSection()}
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>

{#snippet heading(Icon: IconComponent, title: string)}
	<div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
		<Icon class="h-3.5 w-3.5" />
		<span class="uppercase tracking-wide">{title}</span>
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

{#snippet section(Icon: IconComponent, title: string, body: Snippet)}
	<div class="space-y-1">
		{@render heading(Icon, title)}
		<div class="divide-y divide-border/60">
			{@render body()}
		</div>
	</div>
{/snippet}

{#snippet responseFields()}
	{@render field('Status', asset?.status_code)}
	{@render field('Webserver', asset?.webserver)}
	{@render field('Content-Type', asset?.content_type)}
	{@render field(
		'Content-Length',
		asset?.content_length != null ? formatBytes(asset.content_length) : null
	)}
	{@render field('Response time', formatResponseTime(asset?.response_time))}
	{@render field('Words', asset?.words)}
	{@render field('Lines', asset?.lines)}
	{@render field('Location', asset?.location)}
{/snippet}

{#snippet fingerprintFields()}
	{@render field('JARM', asset?.jarm)}
	{@render field('Favicon hash', asset?.favicon_hash)}
	{@render field('Body hash', asset?.content_hash)}
	{@render field('Header hash', asset?.header_hash)}
	{@render field('HTTP/2', asset?.supports_http2 ? 'yes' : null)}
	{@render field('Pipelining', asset?.supports_pipeline ? 'yes' : null)}
{/snippet}

{#snippet networkSection()}
	<div class="space-y-1">
		{@render heading(Network, 'Network')}
		<div class="divide-y divide-border/60">
			{@render field('IP', asset?.ip)}
			{@render field('A records', asset?.a_records?.length ? asset.a_records.join(', ') : null)}
			{@render field(
				'AAAA records',
				asset?.aaaa_records?.length ? asset.aaaa_records.join(', ') : null
			)}
			{@render field('CNAME', asset?.cname)}
			{@render field('ASN', asset?.asn ? `AS${asset.asn}` : ipMeta?.asn ? `AS${ipMeta.asn}` : null)}
			{@render field('Organization', asset?.asn_org ?? ipMeta?.asn_org)}
			{@render field('Country', ipMeta?.country)}
			{@render field('Prefix', ipMeta?.prefix)}
			{@render field('PTR', ipMeta?.ptr_hostnames?.length ? ipMeta.ptr_hostnames.join(', ') : null)}
		</div>
		<div class="flex flex-wrap gap-1 pt-1">
			{#if asset?.is_cdn}
				<Badge variant="info" class="font-normal"
					>CDN{asset.cdn_name ? `: ${asset.cdn_name}` : ''}</Badge
				>
			{/if}
			{#if asset?.waf}
				<Badge variant="warning" class="font-normal">WAF: {asset.waf}</Badge>
			{/if}
		</div>
		{#if ports.length}
			<div class="flex items-center gap-1.5 pt-2 text-xs text-muted-foreground">
				<Plug class="h-3.5 w-3.5" />
				Open ports on {asset?.ip}
			</div>
			<div class="flex flex-wrap gap-1">
				{#each ports as p (p.id)}
					<Badge variant="outline" class="font-mono text-[11px] font-normal">
						{p.number}{p.service_name ? `/${p.service_name}` : ''}
					</Badge>
				{/each}
			</div>
		{/if}
		{#if neighbors.length > 1}
			<div class="pt-2 text-xs text-muted-foreground">
				{neighbors.length} hosts share this IP
			</div>
		{/if}
	</div>
{/snippet}

{#snippet tlsSection()}
	{#if asset?.tls_version || asset?.tls_not_after}
		<div class="space-y-1">
			<div class="flex items-center justify-between">
				{@render heading(
					asset.tls_expired || asset.tls_self_signed ? ShieldAlert : ShieldCheck,
					'TLS certificate'
				)}
				<div class="flex gap-1">
					{#if asset.tls_expired}
						<Badge variant="destructive" class="font-normal">Expired</Badge>
					{/if}
					{#if asset.tls_self_signed}
						<Badge variant="warning" class="font-normal">Self-signed</Badge>
					{/if}
				</div>
			</div>
			<div class="divide-y divide-border/60">
				{@render field('Version', asset.tls_version)}
				{@render field('Cipher', asset.tls_cipher)}
				{@render field('Subject CN', asset.tls_subject_cn)}
				{@render field('SANs', asset.tls_sans?.length ? asset.tls_sans.join(', ') : null)}
				{@render field('Issuer', asset.tls_issuer_org ?? asset.tls_issuer)}
				{@render field('Serial', asset.tls_serial)}
				{@render field('Fingerprint', asset.tls_fingerprint)}
				{@render field(
					'Valid from',
					asset.tls_not_before ? formatShortDate(asset.tls_not_before) : null
				)}
				{@render field(
					'Valid until',
					asset.tls_not_after ? formatShortDate(asset.tls_not_after) : null
				)}
			</div>
		</div>
	{/if}
{/snippet}
