<script lang="ts">
	import NewBadge from '$lib/components/new-badge.svelte';
	import { untrack } from 'svelte';
	import { SHEET_ROW, SHEET_DT, SHEET_HEAD, sheetStep } from './sheet';
	import SheetTop from './sheet-top.svelte';
	import SheetBar from './sheet-bar.svelte';
	import Network from '@lucide/svelte/icons/network';
	import NotesButton from '$lib/components/notes/notes-button.svelte';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import Plug from '@lucide/svelte/icons/plug';
	import Globe from '@lucide/svelte/icons/globe';
	import Server from '@lucide/svelte/icons/server';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Item from '$lib/components/ui/item';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import CodeBlock from '$lib/components/code-block.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import { exactToken, filterToken } from '$lib/utilities/scan-insights';
	import { productBrand, serviceLabel, type ServiceRead } from '$lib/utilities/services';
	import {
		PORT_SOURCE_HELP,
		PORT_SOURCE_LABELS,
		PortSource,
		SCAN_POLICY_LABELS,
		SERVICE_CLASS_ICONS,
		serviceClassLabel
	} from '$lib/config/service-classes';
	import { hostPort } from '$lib/utilities/net';
	import { externalHref } from '$lib/utilities/links';
	import CountryFlag from './country-flag.svelte';
	import TechIcon from './tech-icon.svelte';
	import ServiceIcon from './services/service-icon.svelte';

	interface Props {
		service: ServiceRead | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		index?: number;
		pageOffset?: number;
		total?: number;
		onStep?: (dir: -1 | 1) => void;
		onFilter?: (dsl: string) => void;
		onHosts?: (filter: string) => void;
		onAddress?: (filter: string) => void;
	}

	let {
		service: s,
		open,
		onOpenChange,
		index = 0,
		pageOffset = 0,
		total = 0,
		onStep,
		onFilter,
		onHosts,
		onAddress
	}: Props = $props();

	const SVC = SURFACE[SurfaceDimension.SERVICES];
	const IPS = SURFACE[SurfaceDimension.IPS];

	let contentEl = $state<HTMLElement | null>(null);
	let bodyEl = $state<HTMLElement | null>(null);
	let scrolledFor = '';

	$effect.pre(() => {
		const id = open ? (s?.id ?? '') : '';
		if (id === scrolledFor) return;
		scrolledFor = id;
		if (!id) return;
		untrack(() => bodyEl?.scrollTo({ top: 0 }));
	});

	let endpoint = $derived(s ? hostPort(s.ip, s.port) : '');
	let network = $derived(
		s ? [s.asn ? `AS${s.asn}` : null, s.asn_org].filter(Boolean).join(' · ') : ''
	);
	let ClassIcon = $derived(SERVICE_CLASS_ICONS[s?.service_class ?? ''] ?? Server);
</script>

<svelte:window onkeydown={(e) => sheetStep(e, open, onStep)} />

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content
		bind:ref={contentEl}
		side="right"
		tabindex={-1}
		class="flex w-full flex-col gap-0 p-0 outline-none sm:max-w-xl"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			contentEl?.focus();
		}}
	>
		{#if s}
			<Sheet.Header class={SHEET_HEAD}>
				<SheetTop noun={SVC.noun} {index} {pageOffset} {total} {onStep}>
					<ServiceIcon
						service={s.service_name}
						serviceClass={s.service_class}
						product={s.product}
						class="size-4 shrink-0"
					/>
				</SheetTop>
				<div class="flex min-w-0 items-center gap-1">
					<Sheet.Title class="min-w-0 truncate font-mono text-base font-medium"
						>{endpoint}</Sheet.Title
					>
					<CopyButton value={endpoint} label="Copy address and port" />
				</div>
				<Sheet.Description class="truncate">
					{serviceLabel(s)} · {serviceClassLabel(s.service_class)}{network ? ` · ${network}` : ''}
				</Sheet.Description>
				<div class="flex flex-wrap gap-1">
					<Badge variant="outline" class="font-normal">{s.protocol.toUpperCase()}</Badge>
					{#if s.is_new}
						<NewBadge size="sm" />
					{/if}
					{#if s.is_http}
						<Badge variant="secondary" class="font-normal">HTTP</Badge>
					{/if}
					{#if s.tls}
						<Badge variant="secondary" class="font-normal">TLS</Badge>
					{/if}
					{#if s.is_sensitive}
						<Badge variant="warning" class="font-normal">Sensitive port</Badge>
					{/if}
					{#if s.is_cdn}
						<Badge variant="info" class="font-normal">{s.cdn_name ?? 'CDN'}</Badge>
					{/if}
					{#if s.source === PortSource.INTERNETDB}
						<Badge variant="outline" class="font-normal text-muted-foreground">Unconfirmed</Badge>
					{/if}
				</div>
			</Sheet.Header>

			{#if s.target_id}
				<SheetBar>
					<NotesButton
						anchor={{
							targetId: s.target_id,
							scanId: s.scan_id,
							dimension: SurfaceDimension.SERVICES,
							assetKey: endpoint,
							assetLabel: endpoint
						}}
						class="h-8"
					/>
				</SheetBar>
			{/if}

			<ScrollArea class="min-h-0 flex-1" bind:viewportRef={bodyEl}>
				<div class="flex flex-col gap-6 p-5">
					<section class="flex flex-col gap-2">
						<SectionHead icon={Plug} title="Service" />
						<dl class="flex flex-col divide-y divide-border/60">
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Port</dt>
								<dd class="flex flex-wrap items-center gap-1">
									{@render chip(String(s.port), `port:${s.port}`, 'Filter to this port', true)}
								</dd>
							</div>
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Service</dt>
								<dd class="flex flex-wrap items-center gap-1">
									{#if s.service_name}
										{@render chip(
											s.service_name,
											exactToken('service', s.service_name),
											'Filter to this service',
											true
										)}
									{:else}
										<span class="text-xs text-muted-foreground">Not identified</span>
									{/if}
								</dd>
							</div>
							{#if s.description}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Description</dt>
									<dd class="flex flex-col gap-0.5">
										<span class="text-sm">{s.description}</span>
										{#if s.registered}
											<span class="text-xs text-muted-foreground">
												IANA registration for port {s.port}. The running service is not identified.
											</span>
										{/if}
									</dd>
								</div>
							{/if}
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Class</dt>
								<dd class="flex flex-wrap items-center gap-1.5">
									<ClassIcon class="size-3.5 shrink-0 text-muted-foreground" />
									{@render chip(
										serviceClassLabel(s.service_class),
										`class:${s.service_class}`,
										'Filter to this service class'
									)}
								</dd>
							</div>
							{#if s.product}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Software</dt>
									<dd class="flex flex-wrap items-center gap-1">
										<TechIcon name={productBrand(s.product)} class="size-3.5 shrink-0" />
										{@render chip(
											s.version ? `${s.product} ${s.version}` : s.product,
											exactToken('product', s.product),
											'Filter to this software'
										)}
									</dd>
								</div>
							{/if}
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Evidence</dt>
								<dd class="flex flex-col items-start gap-1">
									{@render chip(
										PORT_SOURCE_LABELS[s.source] ?? s.source,
										exactToken('source', s.source),
										'Filter by source'
									)}
									<span class="text-xs text-muted-foreground">
										{PORT_SOURCE_HELP[s.source] ?? ''}
									</span>
								</dd>
							</div>
							{#if s.banner}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Banner</dt>
									<dd>
										<CodeBlock code={s.banner} label="Banner" maxHeight="10rem" maxLines={0} />
									</dd>
								</div>
							{/if}
						</dl>
					</section>

					{#if s.is_http}
						<section class="flex flex-col gap-2">
							<SectionHead icon={Globe} title="Web service" />
							<dl class="flex flex-col divide-y divide-border/60">
								{#if s.status_code != null}
									<div class={SHEET_ROW}>
										<dt class={SHEET_DT}>Status</dt>
										<dd>
											<button
												type="button"
												class="font-mono text-sm tabular-nums {httpStatusTextClass(
													s.status_code
												)} hover:text-primary"
												onclick={() => onFilter?.(`status:${s.status_code}`)}
											>
												{s.status_code}
											</button>
										</dd>
									</div>
								{/if}
								{#if s.title}
									<div class={SHEET_ROW}>
										<dt class={SHEET_DT}>Title</dt>
										<dd class="text-sm break-words">{s.title}</dd>
									</div>
								{/if}
								{#if s.url}
									<div class={SHEET_ROW}>
										<dt class={SHEET_DT}>URL</dt>
										<dd>
											<a
												href={externalHref(s.url)}
												target="_blank"
												rel="noopener noreferrer"
												class="inline-flex items-center gap-1 font-mono text-xs break-all hover:text-primary"
											>
												{s.url}
												<ExternalLink class="size-3 shrink-0" />
											</a>
										</dd>
									</div>
								{/if}
								{#if s.web_count > 1}
									<div class={SHEET_ROW}>
										<dt class={SHEET_DT}>Web assets</dt>
										<dd class="text-sm tabular-nums">{s.web_count}</dd>
									</div>
								{/if}
							</dl>
						</section>
					{/if}

					<section class="flex flex-col gap-2">
						<SectionHead icon={Network} title="Address" />
						<dl class="flex flex-col divide-y divide-border/60">
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Address</dt>
								<dd class="flex flex-wrap items-center gap-1">
									{@render chip(s.ip, filterToken('ip', s.ip), 'Filter to this address', true)}
									<Button
										variant="ghost"
										size="sm"
										class="h-6 px-2 text-xs"
										onclick={() => onAddress?.(filterToken('ip', s.ip))}
									>
										<Server class="size-3" /> Open in {IPS.label}
									</Button>
								</dd>
							</div>
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Autonomous system</dt>
								<dd class="flex flex-wrap items-center gap-1">
									{#if s.asn}
										{@render chip(
											`AS${s.asn}${s.asn_org ? ` · ${s.asn_org}` : ''}`,
											`asn:${s.asn}`,
											'Filter services in this network'
										)}
									{:else}
										<span class="text-xs text-muted-foreground">Not enriched</span>
									{/if}
								</dd>
							</div>
							{#if s.country}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Country</dt>
									<dd>
										{@render chip(
											s.country,
											exactToken('country', s.country),
											'Filter by country',
											false,
											true
										)}
									</dd>
								</div>
							{/if}
							{#if s.prefix}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Prefix</dt>
									<dd class="font-mono text-xs">{s.prefix}</dd>
								</div>
							{/if}
							{#if s.scan_policy}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Scan coverage</dt>
									<dd class="text-sm">{SCAN_POLICY_LABELS[s.scan_policy] ?? s.scan_policy}</dd>
								</div>
							{/if}
						</dl>
					</section>

					<section class="flex flex-col gap-2">
						<SectionHead icon={Globe} title="Web assets on this address" />
						{#if s.hosts.length}
							<Item.Group class="gap-0.5">
								{#each s.hosts as host (host)}
									<Item.Root size="sm" class="hover:bg-muted/60">
										{#snippet child({ props })}
											<button
												type="button"
												{...props}
												onclick={() => onHosts?.(exactToken('host', host))}
											>
												<Item.Content>
													<Item.Title class="font-mono text-xs font-normal">{host}</Item.Title>
												</Item.Content>
												<Item.Actions>
													<ChevronRight class="size-4 text-muted-foreground/60" />
												</Item.Actions>
											</button>
										{/snippet}
									</Item.Root>
								{/each}
							</Item.Group>
							{#if s.host_count > s.hosts.length}
								<p class="px-3 text-xs text-muted-foreground">
									{s.hosts.length.toLocaleString()} of {s.host_count.toLocaleString()} shown.
								</p>
							{/if}
						{:else}
							<p class="text-xs text-muted-foreground">No hostname resolves to this address.</p>
						{/if}
					</section>
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>

{#snippet chip(text: string, dsl: string, hint: string, mono = false, flag = false)}
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<button {...props} type="button" onclick={() => onFilter?.(dsl)}>
					<Badge
						variant="outline"
						class="max-w-full cursor-pointer text-left font-normal whitespace-normal wrap-anywhere hover:bg-accent {mono
							? 'font-mono text-2xs'
							: ''}"
					>
						{#if flag}<CountryFlag code={text} />{:else}{text}{/if}
					</Badge>
				</button>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content class="flex items-center gap-1.5">
			{hint}
			<Fingerprint class="size-3 opacity-60" />
			<span class="font-mono">{dsl}</span>
		</Tooltip.Content>
	</Tooltip.Root>
{/snippet}
