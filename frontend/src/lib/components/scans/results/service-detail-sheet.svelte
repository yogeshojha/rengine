<script module lang="ts">
	const ROW = 'grid grid-cols-[8.5rem_1fr] items-start gap-3 py-2';
	const DT = 'pt-0.5 text-xs text-muted-foreground';
</script>

<script lang="ts">
	import Network from '@lucide/svelte/icons/network';
	import Plug from '@lucide/svelte/icons/plug';
	import Globe from '@lucide/svelte/icons/globe';
	import Server from '@lucide/svelte/icons/server';
	import Copy from '@lucide/svelte/icons/copy';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import type { IconComponent } from '$lib/config/icons';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Item from '$lib/components/ui/item';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
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
	import { writeClipboard } from '$lib/utilities/clipboard';
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

	let contentEl = $state<HTMLElement | null>(null);
	let position = $derived(pageOffset + index + 1);
	let endpoint = $derived(s ? `${s.ip}:${s.port}` : '');
	let network = $derived(
		s ? [s.asn ? `AS${s.asn}` : null, s.asn_org].filter(Boolean).join(' · ') : ''
	);
	let ClassIcon = $derived(SERVICE_CLASS_ICONS[s?.service_class ?? ''] ?? Server);

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
		class="flex w-full flex-col gap-0 p-0 outline-none sm:max-w-xl"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			contentEl?.focus();
		}}
	>
		{#if s}
			<Sheet.Header class="gap-3 border-b border-border px-5 pt-5 pr-12 pb-4">
				<div class="flex items-center gap-2">
					<ServiceIcon
						service={s.service_name}
						serviceClass={s.service_class}
						product={s.product}
						class="size-4 shrink-0"
					/>
					<Sheet.Title class="truncate font-mono text-base font-medium">{endpoint}</Sheet.Title>
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon-sm"
									class="size-7"
									onclick={() => copy(endpoint)}
									aria-label="Copy address and port"
								>
									<Copy />
								</Button>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>Copy address and port</Tooltip.Content>
					</Tooltip.Root>
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
											aria-label="Previous service"
										>
											<ChevronUp />
										</Button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content class="flex items-center gap-1.5">
									Previous <Kbd>k</Kbd>
								</Tooltip.Content>
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
											aria-label="Next service"
										>
											<ChevronDown />
										</Button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content class="flex items-center gap-1.5">
									Next <Kbd>j</Kbd>
								</Tooltip.Content>
							</Tooltip.Root>
						{/if}
					</div>
				</div>
				<Sheet.Description class="truncate">
					{serviceLabel(s)} · {serviceClassLabel(s.service_class)}{network ? ` · ${network}` : ''}
				</Sheet.Description>
				<div class="flex flex-wrap gap-1">
					<Badge variant="outline" class="font-normal">{s.protocol.toUpperCase()}</Badge>
					{#if s.is_new}
						<Badge variant="info" class="font-normal">New this scan</Badge>
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

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-6 p-5">
					<section class="flex flex-col gap-2">
						{@render heading(Plug, 'Service')}
						<dl class="flex flex-col divide-y divide-border/60">
							<div class={ROW}>
								<dt class={DT}>Port</dt>
								<dd class="flex flex-wrap items-center gap-1">
									{@render chip(String(s.port), `port:${s.port}`, 'Filter to this port', true)}
								</dd>
							</div>
							<div class={ROW}>
								<dt class={DT}>Service</dt>
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
								<div class={ROW}>
									<dt class={DT}>Description</dt>
									<dd class="flex flex-col gap-0.5">
										<span class="text-sm">{s.description}</span>
										{#if s.registered}
											<span class="text-xs text-muted-foreground">
												IANA registration for port {s.port}. Not confirmed by this scan.
											</span>
										{/if}
									</dd>
								</div>
							{/if}
							<div class={ROW}>
								<dt class={DT}>Class</dt>
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
								<div class={ROW}>
									<dt class={DT}>Software</dt>
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
							<div class={ROW}>
								<dt class={DT}>Evidence</dt>
								<dd class="flex flex-col gap-1">
									{@render chip(
										PORT_SOURCE_LABELS[s.source] ?? s.source,
										exactToken('source', s.source),
										'Filter by how the service was observed'
									)}
									<span class="text-xs text-muted-foreground">
										{PORT_SOURCE_HELP[s.source] ?? ''}
									</span>
								</dd>
							</div>
							{#if s.banner}
								<div class={ROW}>
									<dt class={DT}>Banner</dt>
									<dd>
										<pre
											class="max-h-40 overflow-auto rounded-md border bg-muted/30 p-2 font-mono text-[11px] leading-relaxed break-all whitespace-pre-wrap">{s.banner}</pre>
									</dd>
								</div>
							{/if}
						</dl>
					</section>

					{#if s.is_http}
						<section class="flex flex-col gap-2">
							{@render heading(Globe, 'Web service')}
							<dl class="flex flex-col divide-y divide-border/60">
								{#if s.status_code != null}
									<div class={ROW}>
										<dt class={DT}>Status</dt>
										<dd>
											<button
												type="button"
												class="font-mono text-sm tabular-nums {httpStatusTextClass(
													s.status_code
												)} hover:underline"
												onclick={() => onFilter?.(`status:${s.status_code}`)}
											>
												{s.status_code}
											</button>
										</dd>
									</div>
								{/if}
								{#if s.title}
									<div class={ROW}>
										<dt class={DT}>Title</dt>
										<dd class="text-sm break-words">{s.title}</dd>
									</div>
								{/if}
								{#if s.url}
									<div class={ROW}>
										<dt class={DT}>URL</dt>
										<dd>
											<a
												href={s.url}
												target="_blank"
												rel="noopener noreferrer"
												class="inline-flex items-center gap-1 font-mono text-xs break-all hover:underline"
											>
												{s.url}
												<ExternalLink class="size-3 shrink-0" />
											</a>
										</dd>
									</div>
								{/if}
								{#if s.web_count > 1}
									<div class={ROW}>
										<dt class={DT}>Hostnames served</dt>
										<dd class="text-sm tabular-nums">{s.web_count}</dd>
									</div>
								{/if}
							</dl>
						</section>
					{/if}

					<section class="flex flex-col gap-2">
						{@render heading(Network, 'Address')}
						<dl class="flex flex-col divide-y divide-border/60">
							<div class={ROW}>
								<dt class={DT}>Address</dt>
								<dd class="flex flex-wrap items-center gap-1">
									{@render chip(s.ip, filterToken('ip', s.ip), 'Filter to this address', true)}
									<Button
										variant="ghost"
										size="sm"
										class="h-6 gap-1 px-2 text-xs"
										onclick={() => onAddress?.(filterToken('ip', s.ip))}
									>
										<Server class="size-3" /> Open in IPs
									</Button>
								</dd>
							</div>
							<div class={ROW}>
								<dt class={DT}>Autonomous system</dt>
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
								<div class={ROW}>
									<dt class={DT}>Country</dt>
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
								<div class={ROW}>
									<dt class={DT}>Prefix</dt>
									<dd class="font-mono text-xs">{s.prefix}</dd>
								</div>
							{/if}
							{#if s.scan_policy}
								<div class={ROW}>
									<dt class={DT}>Scan coverage</dt>
									<dd class="text-sm">{SCAN_POLICY_LABELS[s.scan_policy] ?? s.scan_policy}</dd>
								</div>
							{/if}
						</dl>
					</section>

					<section class="flex flex-col gap-2">
						{@render heading(Globe, 'Hosts on this address')}
						{#if s.hosts.length}
							<Item.Group class="rounded-lg border">
								{#each s.hosts as host (host)}
									<Item.Root size="sm" class="w-full">
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
									Showing {s.hosts.length} of {s.host_count}. Open Web assets for the full list.
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

{#snippet heading(Icon: IconComponent, title: string)}
	<div
		class="flex items-center gap-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase"
	>
		<Icon class="size-3.5" />
		<span>{title}</span>
	</div>
{/snippet}

{#snippet chip(text: string, dsl: string, hint: string, mono = false, flag = false)}
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<button {...props} type="button" onclick={() => onFilter?.(dsl)}>
					<Badge
						variant="outline"
						class="cursor-pointer font-normal hover:bg-accent {mono ? 'font-mono text-[10px]' : ''}"
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
