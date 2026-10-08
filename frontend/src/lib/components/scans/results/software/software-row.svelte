<script lang="ts">
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import NewBadge from '$lib/components/new-badge.svelte';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Globe from '@lucide/svelte/icons/globe';
	import Server from '@lucide/svelte/icons/server';
	import { toast } from 'svelte-sonner';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Hint from '$lib/components/hint.svelte';
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import TargetCell from '../table/target-cell.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import TechIcon from '../tech-icon.svelte';
	import { stopProp } from '$lib/utilities';
	import { plural } from '$lib/utilities/strings';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { excludeToken, exactToken } from '$lib/utilities/scan-insights';
	import { relativeTime } from '$lib/utilities/dates';
	import { ROUTES } from '$lib/config/routes';
	import { epssLabel } from '$lib/config/threat-intel';
	import { SEVERITY_FILL, SEVERITY_TEXT, severityLabel } from '$lib/config/vulnerabilities';
	import { CAVEAT_HELP, CONFIDENCE_HELP, CONFIDENCE_TEXT, nvdUrl } from '$lib/config/software';
	import type { SoftwareCve } from '$lib/types/software';
	import {
		ACTIONS_BODY,
		ACTIONS_PIN,
		TARGET_COLUMN,
		columnCell,
		pinTone,
		rowTone,
		type TableColumn,
		REVEAL
	} from '../table/columns';
	import { bracketed } from '$lib/utilities/net';
	import { SOFTWARE_LEAD_COLUMNS } from './columns';

	interface Props {
		row: SoftwareCve;
		index: number;
		focused?: boolean;
		term?: string;
		columns: TableColumn[];
		selected: boolean;
		checked?: boolean;
		projectWide?: boolean;
		pad: string;
		onCheck?: (id: string) => void;
		onOpen: (row: SoftwareCve) => void;
		onToken: (token: string) => void;
	}

	let {
		row,
		index,
		focused = false,
		term = '',
		columns,
		selected,
		checked = false,
		projectWide = false,
		pad,
		onCheck,
		onOpen,
		onToken
	}: Props = $props();

	let cells = $derived(columns.filter((c) => c.key !== 'target'));
	let location = $derived(row.host ?? row.ip ?? '');
	let epss = $derived(row.epss_score == null ? null : epssLabel(row.epss_score));
	let fill = $derived(SEVERITY_FILL[row.severity] ?? SEVERITY_FILL.unknown);
	let confidenceHint = $derived(
		[CONFIDENCE_HELP[row.confidence] ?? '', ...row.caveats.map((c) => CAVEAT_HELP[c.kind] ?? '')]
			.filter(Boolean)
			.join(' ')
	);

	async function copy(value: string, label: string) {
		if (await writeClipboard(value)) toast.success(`${label} copied`);
	}

	const fixedHint = $derived(
		row.fixed_in && row.fixed_in_assets
			? `Not affected: ${row.name} ${row.fixed_in}, ${plural(row.fixed_in_assets, 'asset')} on the same target`
			: null
	);
</script>

<div
	role="button"
	tabindex="0"
	data-software-row-index={index}
	class="group relative flex w-full cursor-pointer items-stretch gap-3 pr-0 pl-4 text-left text-sm transition-colors {rowTone(
		selected,
		focused
	)}"
	onclick={() => onOpen(row)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(row);
		}
	}}
>
	<span class="absolute inset-y-0 left-0 w-[3px]" style="background:{fill}" aria-hidden="true"
	></span>

	{#if onCheck}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="hidden shrink-0 items-center sm:flex {pad}" onclick={stopProp}>
			<Checkbox
				{checked}
				onCheckedChange={() => onCheck(row.id)}
				aria-label="Select {row.cve}"
				class="transition-opacity {checked ? 'opacity-100' : REVEAL}"
			/>
		</div>
	{/if}

	{#if projectWide}
		<div class="flex shrink-0 items-center {TARGET_COLUMN.width} {pad}">
			<TargetCell value={row.target_value} onFilter={onToken} />
		</div>
	{/if}

	<div class="flex {SOFTWARE_LEAD_COLUMNS[0].width} flex-col justify-center gap-1 {pad}">
		<span class="flex flex-wrap items-center gap-1.5">
			<span class="font-mono text-xs break-all">
				<HighlightText text={row.cve} {term} />
			</span>
			{#if row.is_new}
				<NewBadge />
			{/if}
			{#if row.is_kev}
				<Badge variant="destructive" class="h-4 px-1 text-2xs">KEV</Badge>
			{/if}
			{#if row.kev_ransomware}
				<Badge variant="destructive" class="h-4 px-1 text-2xs">Ransomware</Badge>
			{/if}
		</span>
		{#if row.caveats.length || row.fixed_in}
			<span class="flex flex-wrap items-center gap-1">
				{#if row.fixed_in}
					<Hint text={fixedHint}>
						{#snippet child(props)}
							<span {...props} class="rounded-sm bg-muted px-1 text-2xs text-foreground">
								Fixed in {row.fixed_in}
							</span>
						{/snippet}
					</Hint>
				{/if}
				{#each row.caveats as caveat (caveat.kind)}
					<Hint text={CAVEAT_HELP[caveat.kind] ?? ''}>
						{#snippet child(props)}
							<span {...props} class="rounded-sm bg-muted px-1 text-2xs text-muted-foreground">
								{caveat.label}
							</span>
						{/snippet}
					</Hint>
				{/each}
			</span>
		{/if}
	</div>

	<div class="flex {SOFTWARE_LEAD_COLUMNS[1].width} items-center gap-2 {pad}">
		<TechIcon name={row.name} class="size-3.5 shrink-0" />
		<span class="min-w-0 truncate">
			<HighlightText text={row.name} {term} />
			<span class="text-muted-foreground">{row.version}</span>
		</span>
	</div>

	{#each cells as col (col.key)}
		<div class="{columnCell(col)} items-center gap-2 {pad}">
			{#if col.key === 'asset'}
				{#if row.http_asset_id}
					<Globe class="size-3.5 shrink-0 text-muted-foreground" />
				{:else}
					<Server class="size-3.5 shrink-0 text-muted-foreground" />
				{/if}
				<span class="min-w-0 font-mono break-all">
					<HighlightText text={bracketed(location)} {term} />
					{#if row.port}<span class="text-muted-foreground">:{row.port}</span>{/if}
				</span>
			{:else if col.key === 'severity'}
				<span class={SEVERITY_TEXT[row.severity] ?? 'text-muted-foreground'}>
					{severityLabel(row.severity)}
				</span>
				{#if row.cvss_score != null}
					<span class="text-xs text-muted-foreground tabular-nums">
						{row.cvss_score.toFixed(1)}
					</span>
				{/if}
			{:else if col.key === 'exploitation'}
				{#if epss != null}
					<span class="text-xs tabular-nums">{epss}</span>
				{:else}
					<span class="text-xs text-muted-foreground">Not scored</span>
				{/if}
			{:else if col.key === 'evidence'}
				<EvidenceMark evidence={row.evidence} onFilter={onToken} />
			{:else if col.key === 'confidence'}
				<Hint text={confidenceHint}>
					{#snippet child(props)}
						<span {...props} class={CONFIDENCE_TEXT[row.confidence] ?? 'text-muted-foreground'}>
							{row.confidence_label}
						</span>
					{/snippet}
				</Hint>
			{:else if col.key === 'seen'}
				<span class="text-xs text-muted-foreground">{relativeTime(row.discovered_at)}</span>
			{/if}
		</div>
	{/each}

	<div class="{ACTIONS_PIN} {pinTone(selected, focused)}">
		<div class={ACTIONS_BODY}>
			<Hint text="Hide all {row.name}">
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="hidden size-7 transition-opacity {REVEAL} sm:inline-flex"
						aria-label="Hide all {row.name}"
						onclick={(e) => {
							e.stopPropagation();
							onToken(excludeToken('software', row.name));
						}}
					>
						<EyeOff />
					</Button>
				{/snippet}
			</Hint>
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div onclick={stopProp}>
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button {...props} variant="ghost" size="icon" class="size-7">
								<Ellipsis class="size-4" />
								<span class="sr-only">Actions for {row.cve}</span>
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end" class="w-56">
						<DropdownMenu.Item onclick={() => onOpen(row)}>Open match</DropdownMenu.Item>
						<DropdownMenu.Item>
							{#snippet child({ props })}
								<a {...props} href={ROUTES.cve(row.cve)}>Open CVE exposure</a>
							{/snippet}
						</DropdownMenu.Item>
						<DropdownMenu.Item onclick={() => onToken(exactToken('cve', row.cve))}>
							Filter to this CVE
						</DropdownMenu.Item>
						<DropdownMenu.Item onclick={() => onToken(exactToken('software', row.name))}>
							Filter to {row.name}
						</DropdownMenu.Item>
						<DropdownMenu.Separator />
						<DropdownMenu.Item onclick={() => onToken(excludeToken('software', row.name))}>
							<EyeOff />
							<span class="truncate">Hide all {row.name}</span>
						</DropdownMenu.Item>
						<DropdownMenu.Item onclick={() => onToken(excludeToken('cve', row.cve))}>
							<EyeOff /> Hide all {row.cve}
						</DropdownMenu.Item>
						<DropdownMenu.Separator />
						<DropdownMenu.Item onclick={() => copy(row.cve, 'CVE')}>Copy CVE</DropdownMenu.Item>
						<DropdownMenu.Item onclick={() => copy(row.cpe, 'CPE')}>Copy CPE</DropdownMenu.Item>
						<DropdownMenu.Separator />
						<DropdownMenu.Item>
							{#snippet child({ props })}
								<a {...props} href={nvdUrl(row.cve)} target="_blank" rel="noreferrer noopener">
									<ExternalLink />
									Open on NVD
								</a>
							{/snippet}
						</DropdownMenu.Item>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</div>
		</div>
	</div>
</div>
