<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Copy from '@lucide/svelte/icons/copy';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Filter from '@lucide/svelte/icons/filter';
	import Flame from '@lucide/svelte/icons/flame';
	import Globe from '@lucide/svelte/icons/globe';
	import Terminal from '@lucide/svelte/icons/terminal';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import OverflowPopover from '../table/overflow-popover.svelte';
	import TechIcon from '../tech-icon.svelte';
	import CorroborationBadge from './corroboration-badge.svelte';
	import SeverityMark from './severity-mark.svelte';
	import { stopProp } from '$lib/utilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatShortDate } from '$lib/utilities/dates';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import { exactToken, filterToken } from '$lib/utilities/scan-insights';
	import { epssPercent, locationLabel, originLabel } from '$lib/utilities/vulns';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';
	import {
		EPSS_HIGH,
		PROTOCOL_ICONS,
		PROTOCOL_LABELS,
		SCANNER_LABELS,
		SEVERITY_FILL,
		VULN_STATE_LABELS,
		VulnState
	} from '$lib/config/vulnerabilities';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone, type TableColumn } from '../table/columns';
	import { VULN_LEAD_COLUMNS } from './columns';

	interface Props {
		vuln: VulnerabilityRead;
		index: number;
		term?: string;
		columns: TableColumn[];
		checked: boolean;
		onCheck: (id: string) => void;
		selected: boolean;
		focused: boolean;
		pad: string;
		onOpen: (v: VulnerabilityRead) => void;
		onFilter: (token: string) => void;
		onHost: (filter: string) => void;
		onTriage: (v: VulnerabilityRead, state: string) => void;
	}

	let {
		vuln: v,
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
		onHost,
		onTriage
	}: Props = $props();

	const MAX_TAGS = 3;

	let fill = $derived(SEVERITY_FILL[v.severity] ?? SEVERITY_FILL.unknown);
	let tone = $derived(rowTone(selected || checked, focused));
	let pin = $derived(pinTone(selected || checked, focused));
	let asset = $derived(v.asset);
	let ProtocolIcon = $derived(PROTOCOL_ICONS[v.protocol] ?? Globe);
	let reviewed = $derived(v.state !== VulnState.OPEN);
	let likely = $derived((v.epss_score ?? 0) >= EPSS_HIGH);
	let cvss = $derived(v.cvss_score);
	let path = $derived(locationLabel(v));
	let origin = $derived(originLabel(v));

	function pivot(e: Event, token: string) {
		stopProp(e);
		onFilter(token);
	}
	async function copy(text: string) {
		if (await writeClipboard(text)) toast.success('Copied');
	}
</script>

<div
	class="group relative flex cursor-pointer items-start gap-3 px-4 transition-colors {pad} {tone}"
	role="button"
	tabindex={0}
	data-vuln-row-index={index}
	aria-label="Open {v.template_name}"
	onclick={() => onOpen(v)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(v);
		}
	}}
>
	<span
		class="absolute inset-y-0 left-0 w-[3px] {reviewed ? 'opacity-30' : ''}"
		style="background:{fill}"
		aria-hidden="true"
	></span>

	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="hidden h-5 shrink-0 items-center sm:flex" onclick={stopProp}>
		<Checkbox
			{checked}
			onCheckedChange={() => onCheck(v.id)}
			aria-label="Select {v.template_name}"
			class="transition-opacity {checked
				? 'opacity-100'
				: 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'}"
		/>
	</div>

	<div class="flex flex-col gap-1 {VULN_LEAD_COLUMNS[0].width}">
		<div class="flex flex-wrap items-start gap-x-2 gap-y-1">
			<button
				type="button"
				class="flex h-5 shrink-0 items-center"
				onclick={(e) => pivot(e, exactToken('severity', v.severity))}
				aria-label="Filter to {v.severity}"
			>
				<SeverityMark severity={v.severity} />
			</button>
			<span
				class="min-w-0 text-sm leading-5 font-medium wrap-anywhere {reviewed
					? 'text-muted-foreground'
					: ''}"
			>
				<HighlightText text={v.template_name} {term} />
			</span>
			{#if v.is_kev}
				<Hint text="Listed as exploited in the wild">
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="flex h-5 shrink-0 items-center"
							onclick={(e) => pivot(e, 'is:kev')}
						>
							<Badge variant="destructive" class="gap-1 px-1.5 text-[10px] font-normal">
								<Flame class="size-2.5" /> KEV
							</Badge>
						</button>
					{/snippet}
				</Hint>
			{/if}
			{#if v.is_new}
				<Hint text="Not reported by an earlier scan of this target">
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="flex h-5 shrink-0 items-center"
							onclick={(e) => pivot(e, 'is:new')}
						>
							<Badge variant="info" class="px-1 text-[10px] font-normal">new</Badge>
						</button>
					{/snippet}
				</Hint>
			{/if}
			<CorroborationBadge
				peers={v.corroborated_by}
				scanner={v.scanner}
				onFilter={(token) => onFilter(token)}
			/>
		</div>

		<div class="flex flex-wrap items-center gap-1.5">
			<Hint text="Filter to this check">
				{#snippet child(props)}
					<button
						{...props}
						type="button"
						class="min-w-0 font-mono text-[11px] text-muted-foreground hover:text-foreground hover:underline"
						onclick={(e) => pivot(e, exactToken('template', v.template_id))}
					>
						<HighlightText text={v.template_id} {term} />
					</button>
				{/snippet}
			</Hint>
			{#each v.tags.slice(0, MAX_TAGS) as tag (tag)}
				<button
					type="button"
					class="flex h-4 shrink-0 items-center"
					onclick={(e) => pivot(e, exactToken('tag', tag))}
				>
					<Badge variant="outline" class="px-1 text-[10px] font-normal hover:bg-accent">
						{tag}
					</Badge>
				</button>
			{/each}
			{#if v.tags.length > MAX_TAGS}
				<OverflowPopover
					class="shrink-0"
					items={v.tags}
					shown={MAX_TAGS}
					label="tags"
					onSelect={(t) => onFilter(exactToken('tag', t))}
				/>
			{/if}
		</div>
	</div>

	<div class="{VULN_LEAD_COLUMNS[1].width} flex flex-col gap-0.5">
		<Hint text={v.matched_at}>
			{#snippet child(props)}
				<button
					{...props}
					type="button"
					class="min-w-0 text-left font-mono text-xs leading-4 wrap-anywhere hover:underline"
					onclick={(e) => pivot(e, filterToken('location', path))}
				>
					<HighlightText text={path} {term} />
				</button>
			{/snippet}
		</Hint>
		<span class="flex items-center gap-1">
			<span class="min-w-0 truncate font-mono text-[11px] text-muted-foreground">{origin}</span>
			<CopyButton
				value={v.matched_at}
				class="size-5 shrink-0 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
			/>
		</span>
	</div>

	{#each columns as col (col.key)}
		<div
			class="hidden sm:flex {col.grow ? 'min-w-0 flex-1' : 'shrink-0'} {col.width} {col.align ===
			'right'
				? 'justify-end'
				: ''}"
		>
			{#if col.key === 'asset'}
				{#if asset}
					<div class="flex min-w-0 flex-col gap-1">
						<div class="flex min-w-0 items-center gap-1.5">
							{#if asset.status_code != null}
								<span
									class="shrink-0 font-mono text-xs tabular-nums {httpStatusTextClass(
										asset.status_code
									)}">{asset.status_code}</span
								>
							{/if}
							{#if v.host}
								<Hint text="Open {v.host} in Web assets">
									{#snippet child(props)}
										<button
											{...props}
											type="button"
											class="min-w-0 truncate text-xs hover:underline"
											onclick={(e) => {
												stopProp(e);
												onHost(exactToken('host', v.host ?? ''));
											}}
										>
											{asset.title || v.host}
										</button>
									{/snippet}
								</Hint>
							{/if}
						</div>
						{#if asset.tech.length || asset.is_cdn}
							<div class="flex min-w-0 flex-wrap items-center gap-1">
								{#each asset.tech.slice(0, 2) as tech (tech)}
									<Badge variant="outline" class="gap-1 px-1 text-[10px] font-normal">
										<TechIcon name={tech} class="size-2.5" />
										<span class="truncate">{tech}</span>
									</Badge>
								{/each}
								{#if asset.is_cdn}
									<Badge variant="info" class="px-1 text-[10px] font-normal">
										{asset.cdn_name ?? 'CDN'}
									</Badge>
								{/if}
							</div>
						{/if}
					</div>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'risk'}
				<div class="flex min-w-0 flex-wrap items-center gap-1">
					{#if v.cve_ids.length}
						<button
							type="button"
							class="flex h-4 items-center"
							onclick={(e) => pivot(e, exactToken('cve', v.cve_ids[0]))}
						>
							<Badge
								variant="outline"
								class="px-1 font-mono text-[10px] font-normal hover:bg-accent"
							>
								{v.cve_ids[0]}
							</Badge>
						</button>
						{#if v.cve_ids.length > 1}
							<span class="text-[10px] text-muted-foreground">+{v.cve_ids.length - 1}</span>
						{/if}
					{/if}
					{#if cvss !== null}
						<Hint text="CVSS base score">
							{#snippet child(props)}
								<span {...props} class="font-mono text-xs tabular-nums text-muted-foreground">
									{cvss.toFixed(1)}
								</span>
							{/snippet}
						</Hint>
					{/if}
					{#if v.epss_score != null}
						<Hint text="Probability of exploitation in the next 30 days">
							{#snippet child(props)}
								<span
									{...props}
									class="font-mono text-xs tabular-nums {likely
										? 'text-warning'
										: 'text-muted-foreground'}"
								>
									{epssPercent(v.epss_score)}
								</span>
							{/snippet}
						</Hint>
					{/if}
					{#if !v.cve_ids.length && v.cvss_score == null && v.epss_score == null}
						<span class="text-xs text-muted-foreground">—</span>
					{/if}
				</div>
			{:else if col.key === 'reach'}
				{#if v.host_count > 1}
					<Hint text="This check fired on {v.host_count} hosts in this scan">
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="text-xs text-muted-foreground hover:text-foreground hover:underline"
								onclick={(e) => pivot(e, exactToken('template', v.template_id))}
							>
								{v.host_count} hosts
							</button>
						{/snippet}
					</Hint>
				{:else}
					<span class="text-xs text-muted-foreground">—</span>
				{/if}
			{:else if col.key === 'type'}
				<button
					type="button"
					class="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
					onclick={(e) => pivot(e, exactToken('type', v.protocol))}
				>
					<ProtocolIcon class="size-3.5" />
					{PROTOCOL_LABELS[v.protocol] ?? v.protocol}
				</button>
			{:else if col.key === 'scanner'}
				<Hint text="Filter to findings from this scanner">
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="min-w-0 truncate text-xs text-muted-foreground hover:text-foreground hover:underline"
							onclick={(e) => pivot(e, exactToken('scanner', v.scanner))}
						>
							{SCANNER_LABELS[v.scanner] ?? v.scanner}
						</button>
					{/snippet}
				</Hint>
			{:else if col.key === 'review'}
				{#if reviewed}
					<button
						type="button"
						class="flex h-5 items-center"
						onclick={(e) => pivot(e, exactToken('state', v.state))}
					>
						<Badge variant="secondary" class="px-1.5 text-[10px] font-normal">
							{VULN_STATE_LABELS[v.state] ?? v.state}
						</Badge>
					</button>
				{:else}
					<span class="text-xs text-muted-foreground">Open</span>
				{/if}
			{:else if col.key === 'seen'}
				<span class="text-xs whitespace-nowrap text-muted-foreground">
					{formatShortDate(v.discovered_at)}
				</span>
			{/if}
		</div>
	{/each}

	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class={ACTIONS_PIN} onclick={stopProp}>
		<div class="{ACTIONS_BODY} {pin}">
			{#if v.url}
				<Hint text="Open in a new tab">
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="hidden size-7 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 sm:inline-flex"
							href={v.matched_at}
							target="_blank"
							rel="noopener noreferrer"
						>
							<ExternalLink class="size-3.5" />
							<span class="sr-only">Open {v.matched_at}</span>
						</Button>
					{/snippet}
				</Hint>
			{/if}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="ghost" size="icon" class="size-7">
							<Ellipsis class="size-4" />
							<span class="sr-only">Actions for {v.template_name}</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-56">
					<DropdownMenu.Item onclick={() => onOpen(v)}>Open finding</DropdownMenu.Item>
					<DropdownMenu.Item onclick={() => copy(v.matched_at)}>
						<Copy class="mr-2 size-3.5" /> Copy location
					</DropdownMenu.Item>
					{#if v.curl_command}
						<DropdownMenu.Item onclick={() => copy(v.curl_command ?? '')}>
							<Terminal class="mr-2 size-3.5" /> Copy curl command
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={() => onFilter(exactToken('template', v.template_id))}>
						<Filter class="mr-2 size-3.5" /> Everywhere this check fired
					</DropdownMenu.Item>
					{#if v.host}
						<DropdownMenu.Item onclick={() => onHost(exactToken('host', v.host ?? ''))}>
							<Globe class="mr-2 size-3.5" /> Open host in Web assets
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Label>Review</DropdownMenu.Label>
					<DropdownMenu.RadioGroup value={v.state} onValueChange={(state) => onTriage(v, state)}>
						{#each Object.entries(VULN_STATE_LABELS) as [value, label] (value)}
							<DropdownMenu.RadioItem {value}>{label}</DropdownMenu.RadioItem>
						{/each}
					</DropdownMenu.RadioGroup>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
