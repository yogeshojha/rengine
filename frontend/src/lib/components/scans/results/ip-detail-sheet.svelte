<script lang="ts">
	import { untrack } from 'svelte';
	import { SHEET_ROW, SHEET_DT, SHEET_HEAD, sheetStep } from './sheet';
	import SheetTop from './sheet-top.svelte';
	import Network from '@lucide/svelte/icons/network';
	import Plug from '@lucide/svelte/icons/plug';
	import Globe from '@lucide/svelte/icons/globe';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Item from '$lib/components/ui/item';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { isPrivateIp } from '$lib/utilities/scan-correlation';
	import { isSensitivePort } from '$lib/config/service-classes';
	import { exactToken, filterToken, type IpGroupRead } from '$lib/utilities/scan-insights';
	import CopyButton from '$lib/components/copy-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { plural } from '$lib/utilities/strings';
	import CountryFlag from './country-flag.svelte';

	interface Props {
		group: IpGroupRead | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		index?: number;
		pageOffset?: number;
		total?: number;
		onStep?: (dir: -1 | 1) => void;
		onFilter?: (dsl: string) => void;
		onHosts?: (filter: string) => void;
		onServices?: (filter: string) => void;
		/** where focus goes when the sheet closes; the table hands it to its cursor row */
		onCloseAutoFocus?: (e: Event) => void;
	}

	let {
		group,
		open,
		onOpenChange,
		index = 0,
		pageOffset = 0,
		total = 0,
		onStep,
		onFilter,
		onHosts,
		onServices,
		onCloseAutoFocus
	}: Props = $props();

	const IPS = SURFACE[SurfaceDimension.IPS];
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const SERVICES = SURFACE[SurfaceDimension.SERVICES];

	let contentEl = $state<HTMLElement | null>(null);
	let bodyEl = $state<HTMLElement | null>(null);
	let scrolledFor = '';

	$effect.pre(() => {
		const ip = open ? (group?.ip ?? '') : '';
		if (ip === scrolledFor) return;
		scrolledFor = ip;
		if (!ip) return;
		untrack(() => bodyEl?.scrollTo({ top: 0 }));
	});

	let sensitivePorts = $derived((group?.ports ?? []).filter((p) => isSensitivePort(p.number)));
	let isPrivate = $derived(group ? isPrivateIp(group.ip) : false);
	let network = $derived(
		group
			? [group.asn ? `AS${group.asn}` : null, group.asn_org, group.country]
					.filter(Boolean)
					.join(' · ')
			: ''
	);
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
		{onCloseAutoFocus}
	>
		{#if group}
			<Sheet.Header class={SHEET_HEAD}>
				<SheetTop noun={IPS.noun} {index} {pageOffset} {total} {onStep}>
					<span
						class="size-2 shrink-0 rounded-full {group.is_alive
							? 'bg-success'
							: 'bg-muted-foreground/40'}"
						aria-hidden="true"
					></span>
				</SheetTop>
				<div class="flex min-w-0 items-center gap-1">
					<Sheet.Title class="min-w-0 truncate font-mono text-base font-medium"
						>{group.ip}</Sheet.Title
					>
					<CopyButton value={group.ip} />
				</div>
				<Sheet.Description class="truncate">
					{#if network}
						{network}{group.prefix ? ` · ${group.prefix}` : ''}
					{:else}
						{group.is_alive ? 'Responding' : 'No response'} · no network data
					{/if}
				</Sheet.Description>
				<div class="flex flex-wrap gap-1">
					<Badge variant="outline" class="font-normal">IPv{group.version}</Badge>
					{#if group.is_cdn}
						<Badge variant="info" class="font-normal">{group.cdn_name ?? 'CDN'}</Badge>
					{/if}
					{#if isPrivate}
						<Badge variant="warning" class="font-normal">Private range</Badge>
					{/if}
					{#if sensitivePorts.length}
						<Badge variant="warning" class="font-normal">
							{sensitivePorts.length} sensitive {sensitivePorts.length === 1
								? 'service'
								: 'services'}
						</Badge>
					{/if}
					{#if group.asset_count}
						<Badge variant="secondary" class="font-normal">
							{plural(group.asset_count, 'web service')}
						</Badge>
					{/if}
				</div>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1" bind:viewportRef={bodyEl}>
				<div class="flex flex-col gap-6 p-5">
					<section class="flex flex-col gap-2">
						<SectionHead icon={Network} title="Network" />
						<dl class="flex flex-col divide-y divide-border/60">
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Autonomous system</dt>
								<dd class="flex flex-wrap items-center gap-1">
									{#if group.asn}
										{@render chip(
											`AS${group.asn}${group.asn_org ? ` · ${group.asn_org}` : ''}`,
											`asn:${group.asn}`,
											'Filter addresses in this network'
										)}
									{:else}
										<span class="text-xs text-muted-foreground">Not enriched</span>
									{/if}
								</dd>
							</div>
							{#if group.country}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Country</dt>
									<dd>
										{@render chip(
											group.country,
											exactToken('country', group.country),
											'Filter by country',
											false,
											false,
											true
										)}
									</dd>
								</div>
							{/if}
							{#if group.prefix}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Prefix</dt>
									<dd>
										{@render chip(
											group.prefix,
											exactToken('prefix', group.prefix),
											'Filter by prefix',
											true
										)}
									</dd>
								</div>
							{/if}
							{#if group.ptr_hostnames.length}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>PTR</dt>
									<dd class="flex flex-wrap gap-1">
										{#each group.ptr_hostnames as ptr (ptr)}
											{@render chip(ptr, filterToken('ptr', ptr), 'Filter by PTR', true)}
										{/each}
									</dd>
								</div>
							{/if}
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Responding</dt>
								<dd class="text-sm">
									{group.is_alive ? 'Yes' : 'No'}
								</dd>
							</div>
						</dl>
					</section>

					<section class="flex flex-col gap-2">
						<div class="flex items-center justify-between">
							<SectionHead icon={Plug} title="Open ports" />
							{#if group.ports.length}
								<Button
									variant="outline"
									size="sm"
									class="h-7 text-xs"
									onclick={() => onServices?.(filterToken('ip', group.ip))}
								>
									<Plug data-icon="inline-start" />
									{group.ports.length.toLocaleString()} in {SERVICES.label}
								</Button>
							{/if}
						</div>
						{#if group.ports.length}
							<div class="flex flex-wrap gap-1">
								{#each group.ports as p (p.id)}
									{@render chip(
										`${p.number}${p.service_name ? `/${p.service_name}` : ''}`,
										`port:${p.number}`,
										isSensitivePort(p.number) ? 'Sensitive service' : 'Filter by port',
										true,
										isSensitivePort(p.number)
									)}
								{/each}
							</div>
							{#if sensitivePorts.length}
								<p class="flex items-center gap-1.5 text-xs text-warning">
									<TriangleAlert class="size-3.5" />
									Sensitive: {sensitivePorts.map((p) => p.number).join(', ')}
								</p>
							{/if}
						{:else}
							<p class="text-xs text-muted-foreground">No open ports.</p>
						{/if}
					</section>

					<section class="flex flex-col gap-2">
						<div class="flex items-center justify-between">
							<SectionHead icon={Globe} title="Web assets" />
							{#if group.host_count}
								<Button
									variant="outline"
									size="sm"
									class="h-7 text-xs"
									onclick={() => onHosts?.(filterToken('ip', group.ip))}
								>
									<Globe data-icon="inline-start" />
									{group.host_count.toLocaleString()} in {WEB.label}
								</Button>
							{/if}
						</div>
						{#if group.hosts.length}
							<Item.Group class="gap-0.5">
								{#each group.hosts as h (h)}
									<Item.Root size="sm" class="hover:bg-muted/60">
										{#snippet child({ props })}
											<button
												type="button"
												{...props}
												onclick={() => onHosts?.(exactToken('host', h))}
											>
												<Item.Content>
													<Item.Title class="font-mono text-xs font-normal">{h}</Item.Title>
												</Item.Content>
												<Item.Actions>
													<ChevronRight class="size-4 text-muted-foreground/60" />
												</Item.Actions>
											</button>
										{/snippet}
									</Item.Root>
								{/each}
							</Item.Group>
							{#if group.host_count > group.hosts.length}
								<p class="px-3 text-xs text-muted-foreground">
									{group.hosts.length.toLocaleString()} of {group.host_count.toLocaleString()} shown.
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

{#snippet chip(text: string, dsl: string, hint: string, mono = false, warn = false, flag = false)}
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
