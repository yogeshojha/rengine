<script lang="ts">
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Globe from '@lucide/svelte/icons/globe';
	import Server from '@lucide/svelte/icons/server';
	import { toast } from 'svelte-sonner';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import TargetCell from '../table/target-cell.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import TechIcon from '../tech-icon.svelte';
	import { stopProp } from '$lib/utilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { exactToken } from '$lib/utilities/scan-insights';
	import { relativeTime } from '$lib/utilities/dates';
	import { ROUTES } from '$lib/config/routes';
	import { SEVERITY_FILL, SEVERITY_TEXT, severityLabel } from '$lib/config/vulnerabilities';
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

	const NVD = 'https://nvd.nist.gov/vuln/detail/';

	let shown = $derived(new Set(columns.map((c) => c.key)));
	let location = $derived(row.host ?? row.ip ?? '');
	let epss = $derived(row.epss_score == null ? null : Math.round(row.epss_score * 100));
	let fill = $derived(SEVERITY_FILL[row.severity] ?? SEVERITY_FILL.unknown);
	let confidenceHint = $derived(
		[CONFIDENCE_HELP[row.confidence] ?? '', ...row.caveats.map((c) => CAVEAT_HELP[c.kind] ?? '')]
			.filter(Boolean)
			.join(' ')
	);

	async function copy(value: string, label: string) {
		if (await writeClipboard(value)) toast.success(`${label} copied`);
	}
</script>

<div
	role="button"
	tabindex="0"
	class="group relative flex w-full items-stretch gap-3 pr-0 pl-4 text-left text-sm {rowTone(
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

	{#if projectWide}
		<div class="flex w-40 shrink-0 items-center {pad}">
			<TargetCell value={row.target_value} />
		</div>
	{/if}

	<div class="flex {SOFTWARE_LEAD_COLUMNS[0].width} flex-col justify-center gap-1 {pad}">
		<span class="flex flex-wrap items-center gap-1.5">
			<span class="font-mono text-xs break-all">
				<HighlightText text={row.cve} {term} />
			</span>
			{#if row.is_new}
				<Badge variant="secondary" class="h-4 px-1 text-2xs">New</Badge>
			{/if}
			{#if row.is_kev}
				<Badge variant="destructive" class="h-4 px-1 text-2xs">KEV</Badge>
			{/if}
			{#if row.kev_ransomware}
				<Badge variant="destructive" class="h-4 px-1 text-2xs">Ransomware</Badge>
			{/if}
		</span>
		{#if row.caveats.length}
			<span class="flex flex-wrap items-center gap-1">
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
			<span class={SEVERITY_TEXT[row.severity] ?? 'text-muted-foreground'}>
				{severityLabel(row.severity)}
			</span>
			{#if row.cvss_score != null}
				<span class="text-xs text-muted-foreground tabular-nums">{row.cvss_score.toFixed(1)}</span>
			{/if}
		</div>
	{/if}

	{#if shown.has('exploitation')}
		<div class="flex w-28 items-center {pad}">
			{#if epss != null}
				<span class="text-xs tabular-nums">{epss}%</span>
			{:else}
				<span class="text-xs text-muted-foreground">Not scored</span>
			{/if}
		</div>
	{/if}

	{#if shown.has('evidence')}
		<div class="flex w-32 items-center {pad}">
			<EvidenceMark evidence={row.evidence} onFilter={onToken} />
		</div>
	{/if}

	{#if shown.has('confidence')}
		<div class="flex w-28 items-center {pad}">
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
						<DropdownMenu.Item onclick={() => copy(row.cve, 'CVE')}>Copy CVE</DropdownMenu.Item>
						<DropdownMenu.Item onclick={() => copy(row.cpe, 'CPE')}>Copy CPE</DropdownMenu.Item>
						<DropdownMenu.Separator />
						<DropdownMenu.Item>
							{#snippet child({ props })}
								<a {...props} href={`${NVD}${row.cve}`} target="_blank" rel="noreferrer noopener">
									<ExternalLink class="size-3.5" />
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
