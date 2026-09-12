<script lang="ts">
	import Filter from '@lucide/svelte/icons/filter';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Globe from '@lucide/svelte/icons/globe';
	import Server from '@lucide/svelte/icons/server';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import TargetCell from '../table/target-cell.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import TechIcon from '../tech-icon.svelte';
	import { stopProp } from '$lib/utilities';
	import { exactToken } from '$lib/utilities/scan-insights';
	import { relativeTime } from '$lib/utilities/dates';
	import { SEVERITY_TEXT, severityLabel } from '$lib/config/vulnerabilities';
	import { CAVEAT_HELP, CONFIDENCE_HELP, CONFIDENCE_TEXT } from '$lib/config/software';
	import type { SoftwareCve } from '$lib/types/software';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone, type TableColumn } from '../table/columns';
	import { SOFTWARE_LEAD_COLUMNS } from './columns';

	interface Props {
		row: SoftwareCve;
		term?: string;
		columns: TableColumn[];
		selected: boolean;
		focused: boolean;
		projectWide?: boolean;
		pad: string;
		onOpen: (row: SoftwareCve) => void;
		onToken: (token: string) => void;
	}

	let {
		row,
		term = '',
		columns,
		selected,
		focused,
		projectWide = false,
		pad,
		onOpen,
		onToken
	}: Props = $props();

	let shown = $derived(new Set(columns.map((c) => c.key)));
	let location = $derived(row.host ?? row.ip ?? '');
	let epss = $derived(row.epss_score == null ? null : Math.round(row.epss_score * 100));
	const NVD = 'https://nvd.nist.gov/vuln/detail/';
	let confidenceHint = $derived(
		[CONFIDENCE_HELP[row.confidence] ?? '', ...row.caveats.map((c) => CAVEAT_HELP[c.kind] ?? '')]
			.filter(Boolean)
			.join(' ')
	);
</script>

<button
	type="button"
	class="group flex w-full items-stretch gap-3 border-b border-border/60 px-3 text-left text-sm {rowTone(
		selected,
		focused
	)}"
	onclick={() => onOpen(row)}
>
	{#if projectWide}
		<div class="flex w-40 shrink-0 items-center {pad}">
			<TargetCell value={row.target_value} />
		</div>
	{/if}

	<div class="flex {SOFTWARE_LEAD_COLUMNS[0].width} items-center gap-2 {pad}">
		<span class="font-mono text-sm break-all">
			<HighlightText text={row.cve} {term} />
		</span>
		{#if row.is_new}
			<Badge variant="secondary" class="h-4 px-1 text-2xs">New</Badge>
		{/if}
		{#if row.is_kev}
			<Badge variant="destructive" class="h-4 px-1 text-2xs">KEV</Badge>
		{/if}
	</div>

	<div class="flex {SOFTWARE_LEAD_COLUMNS[1].width} items-center gap-2 {pad}">
		<TechIcon name={row.name} class="size-3.5 shrink-0" />
		<span class="min-w-0 truncate">
			<HighlightText text={row.name} {term} />
			<span class="text-muted-foreground">{row.version}</span>
		</span>
	</div>

	{#if shown.has('asset')}
		<div class="flex min-w-56 max-w-[22rem] grow items-center gap-2 {pad}">
			{#if row.http_asset_id}
				<Globe class="size-3.5 shrink-0 text-muted-foreground" />
			{:else}
				<Server class="size-3.5 shrink-0 text-muted-foreground" />
			{/if}
			<span class="min-w-0 break-all">
				<HighlightText text={location} {term} />
				{#if row.port}<span class="text-muted-foreground">:{row.port}</span>{/if}
			</span>
		</div>
	{/if}

	{#if shown.has('severity')}
		<div class="flex w-28 items-center gap-1.5 {pad}">
			<span class={SEVERITY_TEXT[row.severity] ?? 'text-muted-foreground'}
				>{severityLabel(row.severity)}</span
			>
			{#if row.cvss_score != null}
				<span class="text-xs text-muted-foreground tabular-nums">{row.cvss_score.toFixed(1)}</span>
			{/if}
		</div>
	{/if}

	{#if shown.has('exploitation')}
		<div class="flex w-36 items-center gap-2 {pad}">
			{#if epss != null}
				<span class="text-xs tabular-nums">{epss}%</span>
			{:else}
				<span class="text-xs text-muted-foreground">Not scored</span>
			{/if}
			{#if row.kev_ransomware}
				<Badge variant="destructive" class="h-4 px-1 text-2xs">Ransomware</Badge>
			{/if}
		</div>
	{/if}

	{#if shown.has('confidence')}
		<div class="flex w-32 items-center {pad}">
			<Hint text={confidenceHint}>
				{#snippet child(props)}
					<span {...props} class={CONFIDENCE_TEXT[row.confidence] ?? 'text-muted-foreground'}>
						{row.confidence_label}
					</span>
				{/snippet}
			</Hint>
		</div>
	{/if}

	{#if shown.has('seen')}
		<div class="flex w-24 items-center text-xs text-muted-foreground {pad}">
			{relativeTime(row.discovered_at)}
		</div>
	{/if}

	<div class="{ACTIONS_PIN} {pinTone(selected, focused)}">
		<div class={ACTIONS_BODY}>
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7"
							onclick={(e) => {
								stopProp(e);
								onToken(exactToken('cve', row.cve));
							}}
						>
							<Filter class="size-3.5" />
						</Button>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content>Filter to this CVE</Tooltip.Content>
			</Tooltip.Root>
			<div class="hidden sm:block">
				<CopyButton value={row.cve} />
			</div>
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<a
							{...props}
							href={`${NVD}${row.cve}`}
							target="_blank"
							rel="noreferrer noopener"
							class="hidden size-7 items-center justify-center rounded-md hover:bg-muted sm:inline-flex"
							onclick={stopProp}
						>
							<ExternalLink class="size-3.5" />
						</a>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content>Open on NVD</Tooltip.Content>
			</Tooltip.Root>
		</div>
	</div>
</button>
