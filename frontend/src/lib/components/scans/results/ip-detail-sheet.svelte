<script module lang="ts">
	const ROW = 'grid grid-cols-[8.5rem_1fr] items-start gap-3 py-2';
	const DT = 'pt-0.5 text-xs text-muted-foreground';
</script>

<script lang="ts">
	import Network from '@lucide/svelte/icons/network';
	import Plug from '@lucide/svelte/icons/plug';
	import Server from '@lucide/svelte/icons/server';
	import Globe from '@lucide/svelte/icons/globe';
	import Copy from '@lucide/svelte/icons/copy';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import type { IconComponent } from '$lib/config/icons';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Item from '$lib/components/ui/item';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import { isPrivateIp, isSensitivePort } from '$lib/utilities/scan-correlation';
	import { exactToken, filterToken, type IpGroupRead } from '$lib/utilities/scan-insights';
	import { writeClipboard } from '$lib/utilities/clipboard';
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
		onServices
	}: Props = $props();

	let contentEl = $state<HTMLElement | null>(null);
	let position = $derived(pageOffset + index + 1);
	let sensitivePorts = $derived((group?.ports ?? []).filter((p) => isSensitivePort(p.number)));
	let isPrivate = $derived(group ? isPrivateIp(group.ip) : false);
	let network = $derived(
		group
			? [group.asn ? `AS${group.asn}` : null, group.asn_org, group.country]
					.filter(Boolean)
					.join(' · ')
			: ''
	);

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
		{#if group}
			<Sheet.Header class="gap-3 border-b border-border px-5 pt-5 pr-12 pb-4">
				<div class="flex items-center gap-2">
					<span
						class="size-2 shrink-0 rounded-full {group.is_alive
							? 'bg-success'
							: 'bg-muted-foreground/40'}"
					></span>
					<Sheet.Title class="truncate font-mono text-base font-medium">{group.ip}</Sheet.Title>
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon-sm"
									class="size-7"
									onclick={() => copy(group.ip)}
									aria-label="Copy address"
								>
									<Copy />
								</Button>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>Copy address</Tooltip.Content>
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
											aria-label="Previous address"
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
											aria-label="Next address"
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
					{#if network}
						{network}{group.prefix ? ` · ${group.prefix}` : ''}
					{:else}
						{group.is_alive ? 'Responding' : 'No response observed'} · no network data
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
							{group.asset_count} web {group.asset_count === 1 ? 'service' : 'services'}
						</Badge>
					{/if}
				</div>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-6 p-5">
					<section class="flex flex-col gap-2">
						{@render heading(Network, 'Network')}
						<dl class="flex flex-col divide-y divide-border/60">
							<div class={ROW}>
								<dt class={DT}>Autonomous system</dt>
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
								<div class={ROW}>
									<dt class={DT}>Country</dt>
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
								<div class={ROW}>
									<dt class={DT}>Prefix</dt>
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
								<div class={ROW}>
									<dt class={DT}>PTR</dt>
									<dd class="flex flex-wrap gap-1">
										{#each group.ptr_hostnames as ptr (ptr)}
											{@render chip(ptr, filterToken('ptr', ptr), 'Filter by PTR', true)}
										{/each}
									</dd>
								</div>
							{/if}
							<div class={ROW}>
								<dt class={DT}>Responding</dt>
								<dd class="text-sm">
									{group.is_alive ? 'Yes' : 'No response observed'}
								</dd>
							</div>
						</dl>
					</section>

					<section class="flex flex-col gap-2">
						<div class="flex items-center justify-between">
							{@render heading(Plug, 'Open ports')}
							{#if group.ports.length}
								<Button
									variant="link"
									size="sm"
									class="h-auto gap-1 px-0 text-xs"
									onclick={() => onServices?.(filterToken('ip', group.ip))}
								>
									{group.ports.length} in Services
									<ChevronRight class="size-3.5" />
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
									{sensitivePorts.map((p) => p.number).join(', ')}
									{sensitivePorts.length === 1 ? 'is' : 'are'} commonly abused when exposed.
								</p>
							{/if}
						{:else}
							<p class="text-xs text-muted-foreground">No open ports recorded for this address.</p>
						{/if}
					</section>

					<section class="flex flex-col gap-2">
						<div class="flex items-center justify-between">
							{@render heading(Server, 'Hosts')}
							{#if group.host_count}
								<Button
									variant="outline"
									size="sm"
									class="h-7 text-xs"
									onclick={() => onHosts?.(filterToken('ip', group.ip))}
								>
									<Globe data-icon="inline-start" />
									{group.host_count} in Web Assets
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
									Showing {group.hosts.length} of {group.host_count}. Open Web Assets for the full
									list.
								</p>
							{/if}
						{:else}
							<p class="text-xs text-muted-foreground">No host names resolve to this address.</p>
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

{#snippet chip(text: string, dsl: string, hint: string, mono = false, warn = false, flag = false)}
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
