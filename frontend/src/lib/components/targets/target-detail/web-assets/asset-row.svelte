<script lang="ts">
	import { toast } from 'svelte-sonner';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Copy from '@lucide/svelte/icons/copy';
	import Asterisk from '@lucide/svelte/icons/asterisk';
	import CircleSlash from '@lucide/svelte/icons/circle-slash';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import Hint from '$lib/components/hint.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import OverflowPopover from '$lib/components/scans/results/table/overflow-popover.svelte';
	import HighlightText from '$lib/components/scans/results/table/highlight-text.svelte';
	import {
		ACTIONS_BODY,
		ACTIONS_PIN,
		pinTone,
		rowTone,
		type TableColumn
	} from '$lib/components/scans/results/table/columns';
	import { ASSET_LEAD_COLUMNS } from './columns';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import {
		httpStatusReason,
		httpStatusTextClass,
		isPrivateIp
	} from '$lib/utilities/scan-correlation';
	import { stopProp } from '$lib/utilities';
	import type { TargetAssetRow } from '$lib/types/target-asset';

	interface Props {
		asset: TargetAssetRow;
		columns: TableColumn[];
		term: string;
	}

	let { asset, columns, term }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const MAX_TECH = 3;
	const MAX_SOURCES = 2;

	let shown = $derived(new Set(columns.map((c) => c.key)));
	let scanHref = $derived(
		ROUTES.scanTab(asset.last_scan_id, WEB.tab, { [WEB.queryParam]: `host:${asset.name}` })
	);
	let url = $derived(`http${asset.status_code ? 's' : ''}://${asset.name}`);
	const width = (key: string) => columns.find((c) => c.key === key)?.width ?? '';
	const grow = (key: string) =>
		columns.find((c) => c.key === key)?.grow ? 'min-w-0 flex-1' : 'shrink-0';
	const [HOST_COL, STATUS_COL] = ASSET_LEAD_COLUMNS;

	async function copyHost() {
		if (await writeClipboard(asset.name)) toast.success('Host copied');
	}
</script>

<div class="group flex items-center gap-3 px-4 py-2.5 transition-colors {rowTone(false, false)}">
	<div class="flex flex-col gap-0.5 {HOST_COL.width}">
		<div class="flex min-w-0 items-center gap-1.5">
			<a
				href={scanHref}
				class="truncate font-mono text-sm {asset.current
					? ''
					: 'text-muted-foreground line-through decoration-muted-foreground/40'} hover:underline"
			>
				<HighlightText text={asset.name} terms={[term]} />
			</a>
			{#if asset.is_new}
				<Hint text="First seen in the latest scan">
					{#snippet child(props)}
						<span {...props} class="flex h-5 shrink-0 items-center text-success">
							<Sparkles class="size-3.5" />
						</span>
					{/snippet}
				</Hint>
			{/if}
			{#if !asset.current}
				<Hint text="Not found by the latest scan">
					{#snippet child(props)}
						<span {...props} class="flex h-5 shrink-0 items-center text-muted-foreground">
							<CircleSlash class="size-3.5" />
						</span>
					{/snippet}
				</Hint>
			{/if}
			{#if asset.is_wildcard}
				<Hint text="Wildcard record">
					{#snippet child(props)}
						<span {...props} class="flex h-5 shrink-0 items-center text-warning">
							<Asterisk class="size-3.5" />
						</span>
					{/snippet}
				</Hint>
			{/if}
		</div>
		{#if asset.cname}
			<span class="truncate font-mono text-xs text-muted-foreground">→ {asset.cname}</span>
		{/if}
	</div>

	<div class={STATUS_COL.width}>
		{#if asset.status_code == null}
			<span class="text-xs text-muted-foreground">—</span>
		{:else}
			<Hint text={httpStatusReason(asset.status_code)}>
				{#snippet child(props)}
					<span
						{...props}
						class="font-mono text-sm tabular-nums {httpStatusTextClass(asset.status_code)}"
					>
						{asset.status_code}
					</span>
				{/snippet}
			</Hint>
		{/if}
	</div>

	{#if shown.has('title')}
		<div
			class="hidden {grow('title')} {width(
				'title'
			)} truncate text-sm text-muted-foreground sm:block"
		>
			{#if asset.title}
				<HighlightText text={asset.title} terms={[term]} />
			{:else}
				—
			{/if}
		</div>
	{/if}

	{#if shown.has('tech')}
		<div class="hidden {width('tech')} shrink-0 sm:flex sm:items-center sm:gap-1">
			{#each asset.tech.slice(0, MAX_TECH) as name (name)}
				<Hint text={name}>
					{#snippet child(props)}
						<span {...props} class="flex h-5 shrink-0 items-center">
							<TechIcon {name} class="size-4" />
						</span>
					{/snippet}
				</Hint>
			{/each}
			{#if asset.tech.length > MAX_TECH}
				<OverflowPopover items={asset.tech} shown={MAX_TECH} label="technologies" icons />
			{:else if asset.tech.length === 0 && asset.webserver}
				<span class="truncate text-xs text-muted-foreground">{asset.webserver}</span>
			{:else if asset.tech.length === 0}
				<span class="text-xs text-muted-foreground">—</span>
			{/if}
		</div>
	{/if}

	{#if shown.has('ip')}
		<div class="hidden {width('ip')} shrink-0 flex-col sm:flex">
			{#if asset.ip}
				<span class="truncate font-mono text-xs">
					<HighlightText text={asset.ip} terms={[term]} />
				</span>
				{#if asset.is_cdn}
					<span class="truncate text-xs text-muted-foreground">{asset.cdn_name || 'CDN'}</span>
				{:else if asset.asn_org}
					<span class="truncate text-xs text-muted-foreground">{asset.asn_org}</span>
				{:else if isPrivateIp(asset.ip)}
					<span class="truncate text-xs text-muted-foreground">Private range</span>
				{/if}
			{:else if asset.resolved_ips.length}
				<span class="truncate font-mono text-xs">{asset.resolved_ips[0]}</span>
			{:else}
				<span class="text-xs text-muted-foreground">Does not resolve</span>
			{/if}
		</div>
	{/if}

	{#if shown.has('sources')}
		<div class="hidden {width('sources')} shrink-0 items-center gap-1 sm:flex">
			{#each asset.sources.slice(0, MAX_SOURCES) as source (source)}
				<Badge variant="outline" class="font-normal">{source}</Badge>
			{/each}
			{#if asset.sources.length > MAX_SOURCES}
				<OverflowPopover items={asset.sources} shown={MAX_SOURCES} label="discovery sources" />
			{:else if asset.sources.length === 0}
				<span class="text-xs text-muted-foreground">—</span>
			{/if}
		</div>
	{/if}

	{#if shown.has('scans')}
		<div class="hidden {width('scans')} shrink-0 justify-end text-sm tabular-nums sm:flex">
			{asset.scan_count.toLocaleString()}
		</div>
	{/if}

	{#if shown.has('first_seen')}
		<div
			class="hidden {width(
				'first_seen'
			)} shrink-0 justify-end text-xs text-muted-foreground sm:flex"
		>
			<Hint text={formatShortDate(asset.first_seen)}>
				{#snippet child(props)}
					<span {...props}>{relativeTime(asset.first_seen)}</span>
				{/snippet}
			</Hint>
		</div>
	{/if}

	{#if shown.has('last_seen')}
		<div
			class="hidden {width('last_seen')} shrink-0 justify-end text-xs text-muted-foreground sm:flex"
		>
			<Hint text={formatShortDate(asset.last_seen)}>
				{#snippet child(props)}
					<span {...props}>{relativeTime(asset.last_seen)}</span>
				{/snippet}
			</Hint>
		</div>
	{/if}

	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="{ACTIONS_PIN} {pinTone(false, false)}" onclick={stopProp}>
		<div class={ACTIONS_BODY}>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-8"
							aria-label="Actions for {asset.name}"
						>
							<Ellipsis class="size-4" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-56">
					<DropdownMenu.Item onclick={() => window.open(scanHref, '_self')}>
						<ExternalLink class="mr-2 size-3.5" /> Open in scan
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={copyHost}>
						<Copy class="mr-2 size-3.5" /> Copy host
					</DropdownMenu.Item>
					{#if asset.status_code != null}
						<DropdownMenu.Separator />
						<DropdownMenu.Item onclick={() => window.open(url, '_blank', 'noopener,noreferrer')}>
							<ExternalLink class="mr-2 size-3.5" /> Visit site
						</DropdownMenu.Item>
					{/if}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
