<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Copy from '@lucide/svelte/icons/copy';
	import Filter from '@lucide/svelte/icons/filter';
	import Globe from '@lucide/svelte/icons/globe';
	import Network from '@lucide/svelte/icons/network';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Lock from '@lucide/svelte/icons/lock';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import CopyButton from '$lib/components/copy-button.svelte';
	import OverflowPopover from '../table/overflow-popover.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import TechIcon from '../tech-icon.svelte';
	import IpHoverCard from './ip-hover-card.svelte';
	import { stopProp } from '$lib/utilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { isPrivateIp, isSensitivePort } from '$lib/utilities/scan-correlation';
	import { exactToken, filterToken, type IpGroupRead } from '$lib/utilities/scan-insights';
	import type { TableColumn } from '../table/columns';

	interface Props {
		group: IpGroupRead;
		index: number;
		term?: string;
		columns: TableColumn[];
		checked: boolean;
		onCheck: (ip: string) => void;
		selected: boolean;
		focused: boolean;
		pad: string;
		onOpen: (g: IpGroupRead) => void;
		onFilter: (token: string) => void;
		onHosts: (filter: string) => void;
	}

	let {
		group: g,
		index,
		term = '',
		columns,
		checked,
		onCheck,
		selected,
		focused,
		pad,
		onOpen,
		onFilter,
		onHosts
	}: Props = $props();

	const MAX_PORTS = 5;
	const MAX_HOSTS = 1;

	let ptr = $derived(g.ptr_hostnames ?? []);
	let ports = $derived(g.ports ?? []);
	let hosts = $derived(g.hosts ?? []);
	let priv = $derived(isPrivateIp(g.ip));
	let tone = $derived(
		selected || checked
			? 'bg-primary/5 hover:bg-primary/10'
			: focused
				? 'bg-muted/40 shadow-[inset_2px_0_0_0_var(--primary)]'
				: 'hover:bg-muted/30'
	);

	function pivot(e: Event, token: string) {
		stopProp(e);
		onFilter(token);
	}
	async function copy(text: string) {
		if (await writeClipboard(text)) toast.success('Copied');
	}
</script>

<div
	class="group flex cursor-pointer items-start gap-3 px-4 transition-colors {pad} {tone}"
	role="button"
	tabindex={0}
	data-ip-row-index={index}
	aria-label="Open {g.ip}"
	onclick={() => onOpen(g)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(g);
		}
	}}
>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="hidden shrink-0 self-center sm:flex" onclick={stopProp}>
		<Checkbox
			{checked}
			onCheckedChange={() => onCheck(g.ip)}
			aria-label="Select {g.ip}"
			class="transition-opacity {checked
				? 'opacity-100'
				: 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'}"
		/>
	</div>

	<div class="flex min-w-0 flex-[3] flex-col gap-1 contain-inline-size sm:min-w-56">
		<div class="flex items-start gap-1.5">
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<span
							{...props}
							class="mt-1.5 size-1.5 shrink-0 rounded-full {g.is_alive
								? 'bg-success'
								: 'bg-muted-foreground/40'}"
						></span>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content side="right">
					{g.is_alive ? 'Answered a probe' : 'Never answered'}
				</Tooltip.Content>
			</Tooltip.Root>
			<span class="min-w-0 wrap-anywhere">
				<IpHoverCard group={g}>
					<span class="font-mono text-sm leading-5 font-medium">
						<HighlightText text={g.ip} {term} />
					</span>
				</IpHoverCard>
			</span>
			{#if g.version === 6}
				<Badge
					variant="outline"
					class="mt-px shrink-0 px-1 text-[10px] font-normal text-muted-foreground"
				>
					IPv6
				</Badge>
			{/if}
			{#if g.is_cdn}
				<button type="button" onclick={(e) => pivot(e, filterToken('cdn', g.cdn_name ?? 'yes'))}>
					<Badge variant="info" class="mt-px shrink-0 gap-1 px-1 text-[10px] font-normal">
						<TechIcon name={g.cdn_name ?? ''} class="size-2.5" />
						{g.cdn_name ?? 'CDN'}
					</Badge>
				</button>
			{/if}
			{#if priv}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<button
								{...props}
								type="button"
								class="mt-px inline-flex shrink-0 items-center gap-1 rounded border border-warning/30 bg-warning/10 px-1.5 py-px text-xs font-medium text-warning"
								onclick={(e) => pivot(e, 'is:private')}
							>
								<Lock class="size-3" /> private
							</button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Private address published in public DNS</Tooltip.Content>
				</Tooltip.Root>
			{/if}
			{#if g.has_sensitive}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<button
								{...props}
								type="button"
								class="mt-px inline-flex shrink-0 items-center gap-1 rounded border border-warning/30 bg-warning/10 px-1.5 py-px text-xs font-medium text-warning"
								onclick={(e) => pivot(e, 'is:sensitive')}
							>
								<TriangleAlert class="size-3" /> sensitive
							</button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>An admin or database port is open</Tooltip.Content>
				</Tooltip.Root>
			{/if}
			<CopyButton
				value={g.ip}
				class="-my-0.5 hidden h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 sm:inline-flex"
			/>
		</div>

		{#if ptr.length}
			<div class="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
				<button
					type="button"
					class="min-w-0 truncate font-mono hover:text-foreground hover:underline"
					title={ptr.join(', ')}
					onclick={(e) => pivot(e, filterToken('ptr', ptr[0]))}
				>
					<HighlightText text={ptr[0]} {term} />
				</button>
				{#if ptr.length > 1}
					<span class="shrink-0 text-muted-foreground/60">+{ptr.length - 1}</span>
				{/if}
			</div>
		{/if}
	</div>

	<div class="hidden min-w-40 flex-[2] sm:block">
		{#if g.asn}
			<button
				type="button"
				class="block min-w-0 max-w-full text-left"
				onclick={(e) => pivot(e, `asn:${g.asn}`)}
				title="Filter to AS{g.asn}"
			>
				<span class="block font-mono text-xs hover:underline">AS{g.asn}</span>
				{#if g.asn_org}
					<span class="block truncate text-xs text-muted-foreground">
						<HighlightText text={g.asn_org} {term} />
					</span>
				{/if}
			</button>
		{:else}
			<span class="text-xs text-muted-foreground">—</span>
		{/if}
	</div>

	{#each columns as col (col.key)}
		<div
			class="hidden shrink-0 self-center sm:flex {col.width} {col.align === 'right'
				? 'justify-end'
				: ''}"
		>
			{#if col.key === 'ports'}
				{#if ports.length}
					<div class="flex flex-nowrap items-center gap-0.5 overflow-hidden">
						{#each ports.slice(0, MAX_PORTS) as p (p.id)}
							<button type="button" onclick={(e) => pivot(e, `port:${p.number}`)}>
								<Badge
									variant="outline"
									class="cursor-pointer px-1 font-mono text-[10px] font-normal hover:bg-accent {isSensitivePort(
										p.number
									)
										? 'border-warning/40 text-warning'
										: ''}"
									title={p.service_name ? `${p.number}/${p.service_name}` : String(p.number)}
								>
									{p.number}
								</Badge>
							</button>
						{/each}
						<OverflowPopover
							items={ports.map((p) =>
								p.service_name ? `${p.number}/${p.service_name}` : String(p.number)
							)}
							shown={MAX_PORTS}
							label="open ports"
							mono
							onSelect={(v) => onFilter(`port:${v.split('/')[0]}`)}
						/>
					</div>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'hosts'}
				{#if g.host_count}
					<div class="flex min-w-0 flex-nowrap items-center gap-1 overflow-hidden">
						<span class="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
							{g.host_count}
						</span>
						{#each hosts.slice(0, MAX_HOSTS) as h (h)}
							<button
								type="button"
								onclick={(e) => {
									stopProp(e);
									onHosts(exactToken('host', h));
								}}
								title="Open {h} in Web Assets"
							>
								<Badge
									variant="outline"
									class="max-w-32 cursor-pointer font-mono text-[10px] font-normal hover:bg-accent"
								>
									<span class="truncate">{h}</span>
								</Badge>
							</button>
						{/each}
						<OverflowPopover
							items={hosts}
							shown={MAX_HOSTS}
							label="hosts"
							mono
							onSelect={(h) => onHosts(exactToken('host', h))}
						/>
					</div>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'country'}
				{#if g.country}
					<button
						type="button"
						class="text-xs text-muted-foreground hover:text-foreground hover:underline"
						onclick={(e) => pivot(e, exactToken('country', g.country ?? ''))}
					>
						{g.country}
					</button>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'prefix'}
				{#if g.prefix}
					<button
						type="button"
						class="min-w-0 truncate font-mono text-xs text-muted-foreground hover:text-foreground hover:underline"
						onclick={(e) => pivot(e, exactToken('prefix', g.prefix ?? ''))}
					>
						{g.prefix}
					</button>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'ptr'}
				<span
					class="min-w-0 truncate font-mono text-xs text-muted-foreground"
					title={ptr.join(', ')}
				>
					{ptr.join(', ') || '—'}
				</span>
			{:else if col.key === 'assets'}
				<span class="text-xs tabular-nums text-muted-foreground">
					{g.asset_count || '—'}
				</span>
			{/if}
		</div>
	{/each}

	<div class="flex w-8 shrink-0 items-center justify-end gap-0.5 self-center sm:w-14">
		{#if g.host_count}
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon-sm"
							class="hidden size-7 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 sm:inline-flex"
							onclick={(e) => {
								stopProp(e);
								onHosts(filterToken('ip', g.ip));
							}}
							aria-label="Show hosts on {g.ip} in Web Assets"
						>
							<Globe />
						</Button>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content>Hosts in Web Assets</Tooltip.Content>
			</Tooltip.Root>
		{/if}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger onclick={stopProp} onkeydown={stopProp}>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon-sm"
						class="size-7 text-muted-foreground"
						aria-label="More actions for {g.ip}"
					>
						<Ellipsis />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-52" onclick={stopProp}>
				<DropdownMenu.Group>
					<DropdownMenu.Item onclick={() => copy(g.ip)}>
						<Copy /> Copy address
					</DropdownMenu.Item>
					{#if g.host_count}
						<DropdownMenu.Item onclick={() => onHosts(filterToken('ip', g.ip))}>
							<Globe /> Hosts in Web Assets
						</DropdownMenu.Item>
					{/if}
				</DropdownMenu.Group>
				<DropdownMenu.Separator />
				<DropdownMenu.Group>
					<DropdownMenu.Label>Pivot</DropdownMenu.Label>
					{#if g.asn}
						<DropdownMenu.Item onclick={() => onFilter(`asn:${g.asn}`)}>
							<Network /> Same network
						</DropdownMenu.Item>
					{/if}
					{#if g.prefix}
						<DropdownMenu.Item onclick={() => onFilter(exactToken('prefix', g.prefix ?? ''))}>
							<Network /> Same prefix
						</DropdownMenu.Item>
					{/if}
					{#if g.country}
						<DropdownMenu.Item onclick={() => onFilter(exactToken('country', g.country ?? ''))}>
							<Filter /> Same country
						</DropdownMenu.Item>
					{/if}
					{#if g.cdn_name}
						<DropdownMenu.Item onclick={() => onFilter(filterToken('cdn', g.cdn_name ?? ''))}>
							<Filter /> Same CDN
						</DropdownMenu.Item>
					{/if}
				</DropdownMenu.Group>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</div>
