<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Copy from '@lucide/svelte/icons/copy';
	import Filter from '@lucide/svelte/icons/filter';
	import Globe from '@lucide/svelte/icons/globe';
	import Network from '@lucide/svelte/icons/network';
	import Server from '@lucide/svelte/icons/server';
	import Lock from '@lucide/svelte/icons/lock';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import OverflowPopover from '../table/overflow-popover.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import TechIcon from '../tech-icon.svelte';
	import ServiceIcon from './service-icon.svelte';
	import CountryFlag from '../country-flag.svelte';
	import { stopProp } from '$lib/utilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import { exactToken, filterToken } from '$lib/utilities/scan-insights';
	import { productBrand } from '$lib/utilities/services';
	import {
		PORT_SOURCE_HELP,
		PORT_SOURCE_LABELS,
		PortSource,
		SERVICE_CLASS_FILL,
		serviceClassLabel
	} from '$lib/config/service-classes';
	import type { ServiceRead } from '$lib/utilities/services';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone, type TableColumn } from '../table/columns';
	import { SERVICE_LEAD_COLUMNS } from './columns';

	interface Props {
		service: ServiceRead;
		index: number;
		term?: string;
		columns: TableColumn[];
		checked: boolean;
		onCheck: (id: string) => void;
		selected: boolean;
		focused: boolean;
		pad: string;
		onOpen: (s: ServiceRead) => void;
		onFilter: (token: string) => void;
		onHosts: (filter: string) => void;
		onAddress: (filter: string) => void;
	}

	let {
		service: s,
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
		onHosts,
		onAddress
	}: Props = $props();

	const MAX_HOSTS = 3;

	let hosts = $derived(s.hosts ?? []);
	let endpoint = $derived(`${s.ip}:${s.port}`);
	let passive = $derived(s.source === PortSource.INTERNETDB);
	let software = $derived(s.product ? (s.version ? `${s.product} ${s.version}` : s.product) : null);
	let tone = $derived(rowTone(selected || checked, focused));
	let pin = $derived(pinTone(selected || checked, focused));
	let fill = $derived(SERVICE_CLASS_FILL[s.service_class]);
	let tile = $derived(
		`background:color-mix(in oklch, ${fill} 14%, transparent);box-shadow:inset 0 0 0 1px color-mix(in oklch, ${fill} 30%, transparent)`
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
	class="group flex cursor-pointer items-center gap-3 px-4 transition-colors {pad} {tone}"
	role="button"
	tabindex={0}
	data-service-row-index={index}
	aria-label="Open {endpoint}"
	onclick={() => onOpen(s)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(s);
		}
	}}
>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="hidden shrink-0 sm:flex" onclick={stopProp}>
		<Checkbox
			{checked}
			onCheckedChange={() => onCheck(s.id)}
			aria-label="Select {endpoint}"
			class="transition-opacity {checked
				? 'opacity-100'
				: 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'}"
		/>
	</div>

	<div class="flex flex-col gap-1 {SERVICE_LEAD_COLUMNS[0].width}">
		<div class="flex flex-wrap items-start gap-x-1.5 gap-y-1">
			<span class="flex min-w-0 items-start gap-2">
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<span {...props} class="flex h-5 shrink-0 items-center">
								<span class="flex size-6 items-center justify-center rounded-md" style={tile}>
									<ServiceIcon
										service={s.service_name}
										serviceClass={s.service_class}
										product={s.product}
										class="size-4"
									/>
								</span>
							</span>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="right">{serviceClassLabel(s.service_class)}</Tooltip.Content>
				</Tooltip.Root>
				<Tooltip.Root open={s.is_sensitive ? undefined : false}>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<span {...props} class="min-w-0 leading-5 wrap-anywhere">
								<span
									class="font-mono text-sm leading-5 font-medium {s.is_sensitive
										? 'text-warning'
										: ''}"
								>
									<HighlightText text={s.ip} {term} /><span
										class={s.is_sensitive ? 'text-warning/60' : 'text-muted-foreground'}>:</span
									><HighlightText text={String(s.port)} {term} />
								</span>
							</span>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>An administrative or datastore port</Tooltip.Content>
				</Tooltip.Root>
			</span>

			{#if s.service_name}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<button
								{...props}
								type="button"
								class="flex h-5 shrink-0 items-center"
								onclick={(e) => pivot(e, exactToken('service', s.service_name ?? ''))}
							>
								<Badge variant="secondary" class="px-1.5 font-mono text-[10px] font-normal">
									{s.service_name}
								</Badge>
							</button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="bottom" class="max-w-72">
						{#if s.description}
							<span class="block">{s.description}</span>
							{#if s.registered}
								<span class="block text-muted-foreground">
									IANA registration for port {s.port}, not confirmed by this scan
								</span>
							{/if}
						{:else}
							Filter to {s.service_name}
						{/if}
					</Tooltip.Content>
				</Tooltip.Root>
			{/if}
			{#if s.is_new}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<button
								{...props}
								type="button"
								class="flex h-5 shrink-0 items-center"
								onclick={(e) => pivot(e, 'is:new')}
							>
								<Badge variant="info" class="px-1 text-[10px] font-normal">new</Badge>
							</button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Not open in an earlier scan of this target</Tooltip.Content>
				</Tooltip.Root>
			{/if}
			{#if s.tls}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<span {...props} class="flex h-5 shrink-0 items-center text-muted-foreground">
								<Lock class="size-3" />
							</span>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Negotiates TLS</Tooltip.Content>
				</Tooltip.Root>
			{/if}
			{#if s.is_cdn}
				<button
					type="button"
					class="flex h-5 shrink-0 items-center"
					onclick={(e) => pivot(e, filterToken('cdn', s.cdn_name ?? 'yes'))}
				>
					<Badge variant="info" class="gap-1 px-1 text-[10px] font-normal">
						<TechIcon name={s.cdn_name ?? ''} class="size-2.5" />
						{s.cdn_name ?? 'CDN'}
					</Badge>
				</button>
			{/if}
			<span class="hidden h-5 shrink-0 items-center sm:flex">
				<CopyButton
					value={endpoint}
					class="size-6 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
				/>
			</span>
		</div>

		{#if passive}
			<Hint text={PORT_SOURCE_HELP[PortSource.INTERNETDB]}>
				{#snippet child(props)}
					<button
						{...props}
						type="button"
						class="flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
						onclick={(e) => pivot(e, 'is:passive')}
					>
						<span class="size-1 rounded-full bg-muted-foreground/50"></span>
						Not observed by this scan
					</button>
				{/snippet}
			</Hint>
		{:else if s.banner && !software}
			<Hint text={s.banner}>
				{#snippet child(props)}
					<span {...props} class="min-w-0 truncate font-mono text-xs text-muted-foreground">
						<HighlightText text={s.banner ?? ''} {term} />
					</span>
				{/snippet}
			</Hint>
		{/if}
	</div>

	<div class={SERVICE_LEAD_COLUMNS[1].width}>
		{#if software}
			<Hint text={s.banner ?? software}>
				{#snippet child(props)}
					<button
						{...props}
						type="button"
						class="block min-w-0 max-w-full text-left"
						onclick={(e) => pivot(e, exactToken('product', s.product ?? ''))}
					>
						<span class="flex items-start gap-1.5">
							<span class="flex h-4 shrink-0 items-center">
								<TechIcon name={productBrand(s.product)} class="size-3.5" />
							</span>
							<span class="min-w-0 text-xs leading-4 wrap-anywhere hover:underline">
								<HighlightText text={software} {term} />
							</span>
						</span>
					</button>
				{/snippet}
			</Hint>
		{:else}
			<span class="text-xs text-muted-foreground">—</span>
		{/if}
	</div>

	{#each columns as col (col.key)}
		<div
			class="hidden sm:flex {col.grow ? 'min-w-0 flex-1' : 'shrink-0'} {col.width} {col.align ===
			'right'
				? 'justify-end'
				: ''}"
		>
			{#if col.key === 'hosts'}
				{#if s.host_count}
					<div class="flex min-w-0 flex-wrap items-center gap-1">
						{#each hosts.slice(0, MAX_HOSTS) as h (h)}
							<Hint text="Open {h} in Web Assets">
								{#snippet child(props)}
									<button
										{...props}
										type="button"
										onclick={(e) => {
											stopProp(e);
											onHosts(exactToken('host', h));
										}}
									>
										<Badge
											variant="outline"
											class="max-w-full cursor-pointer font-mono text-[10px] font-normal hover:bg-accent"
										>
											<span class="truncate">{h}</span>
										</Badge>
									</button>
								{/snippet}
							</Hint>
						{/each}
						<OverflowPopover
							class="shrink-0"
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
			{:else if col.key === 'web'}
				{#if s.is_http}
					<div class="flex min-w-0 items-center gap-1.5">
						{#if s.status_code != null}
							<button
								type="button"
								class="shrink-0 font-mono text-xs tabular-nums {httpStatusTextClass(
									s.status_code
								)} hover:underline"
								onclick={(e) => pivot(e, `status:${s.status_code}`)}
							>
								{s.status_code}
							</button>
						{/if}
						<Hint text={s.title}>
							{#snippet child(props)}
								<span {...props} class="min-w-0 truncate text-xs text-muted-foreground">
									{s.title ?? '—'}
								</span>
							{/snippet}
						</Hint>
						{#if s.web_count > 1}
							<span class="shrink-0 text-xs text-muted-foreground/60">+{s.web_count - 1}</span>
						{/if}
					</div>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'network'}
				{#if s.asn}
					<Hint text="Filter to AS{s.asn}">
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="block min-w-0 max-w-full text-left"
								onclick={(e) => pivot(e, `asn:${s.asn}`)}
							>
								<span class="block font-mono text-xs hover:underline">AS{s.asn}</span>
								{#if s.asn_org}
									<span class="block truncate text-xs text-muted-foreground">
										<HighlightText text={s.asn_org} {term} />
									</span>
								{/if}
							</button>
						{/snippet}
					</Hint>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'country'}
				{#if s.country}
					<button
						type="button"
						class="text-xs text-muted-foreground hover:text-foreground hover:underline"
						onclick={(e) => pivot(e, exactToken('country', s.country ?? ''))}
					>
						<CountryFlag code={s.country} />
					</button>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'evidence'}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<button
								{...props}
								type="button"
								class="min-w-0 truncate text-xs text-muted-foreground hover:text-foreground hover:underline"
								onclick={(e) => pivot(e, exactToken('source', s.source))}
							>
								{PORT_SOURCE_LABELS[s.source] ?? s.source}
							</button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>{PORT_SOURCE_HELP[s.source] ?? s.source}</Tooltip.Content>
				</Tooltip.Root>
			{/if}
		</div>
	{/each}

	<div class={ACTIONS_PIN}>
		<div class="{ACTIONS_BODY} {pin}">
			{#if s.url}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								href={s.url}
								target="_blank"
								rel="noopener noreferrer"
								aria-label="Open {s.url}"
								class="hidden size-7 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 sm:inline-flex"
								onclick={stopProp}
							>
								<ExternalLink />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Open in a new tab</Tooltip.Content>
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
							aria-label="More actions for {endpoint}"
						>
							<Ellipsis />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-56" onclick={stopProp}>
					<DropdownMenu.Group>
						<DropdownMenu.Item onclick={() => copy(endpoint)}>
							<Copy /> Copy address and port
						</DropdownMenu.Item>
						<DropdownMenu.Item onclick={() => onAddress(filterToken('ip', s.ip))}>
							<Server /> Address in IPs
						</DropdownMenu.Item>
						{#if s.host_count}
							<DropdownMenu.Item onclick={() => onHosts(filterToken('ip', s.ip))}>
								<Globe /> Hosts in Web Assets
							</DropdownMenu.Item>
						{/if}
					</DropdownMenu.Group>
					<DropdownMenu.Separator />
					<DropdownMenu.Group>
						<DropdownMenu.Label>Pivot</DropdownMenu.Label>
						<DropdownMenu.Item onclick={() => onFilter(`port:${s.port}`)}>
							<Filter /> Same port
						</DropdownMenu.Item>
						{#if s.service_name}
							<DropdownMenu.Item
								onclick={() => onFilter(exactToken('service', s.service_name ?? ''))}
							>
								<Filter /> Same service
							</DropdownMenu.Item>
						{/if}
						{#if s.product}
							<DropdownMenu.Item onclick={() => onFilter(exactToken('product', s.product ?? ''))}>
								<Filter /> Same software
							</DropdownMenu.Item>
						{/if}
						{#if s.asn}
							<DropdownMenu.Item onclick={() => onFilter(`asn:${s.asn}`)}>
								<Network /> Same network
							</DropdownMenu.Item>
						{/if}
						<DropdownMenu.Item onclick={() => onFilter(`class:${s.service_class}`)}>
							<Filter /> Same service class
						</DropdownMenu.Item>
					</DropdownMenu.Group>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
