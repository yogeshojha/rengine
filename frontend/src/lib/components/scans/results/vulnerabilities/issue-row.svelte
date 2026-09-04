<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Bug from '@lucide/svelte/icons/bug';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Copy from '@lucide/svelte/icons/copy';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Filter from '@lucide/svelte/icons/filter';
	import CheckCheck from '@lucide/svelte/icons/check-check';
	import Flame from '@lucide/svelte/icons/flame';
	import Globe from '@lucide/svelte/icons/globe';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Hint from '$lib/components/hint.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import OverflowPopover from '../table/overflow-popover.svelte';
	import SeverityMark from './severity-mark.svelte';
	import { stopProp } from '$lib/utilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatShortDate } from '$lib/utilities/dates';
	import { exactToken } from '$lib/utilities/scan-insights';
	import { epssPercent, type IssueRead } from '$lib/utilities/vulns';
	import {
		EPSS_HIGH,
		PROTOCOL_ICONS,
		SEVERITY_FILL,
		TEMPLATE_SET_ICONS,
		TEMPLATE_SET_LABELS,
		VULN_STATE_LABELS,
		VulnState
	} from '$lib/config/vulnerabilities';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone, type TableColumn } from '../table/columns';
	import { ISSUE_LEAD_COLUMNS } from './columns';

	interface Props {
		issue: IssueRead;
		index: number;
		term?: string;
		columns: TableColumn[];
		checked: boolean;
		onCheck: (id: string) => void;
		expanded: boolean;
		focused: boolean;
		pad: string;
		onToggle: (issue: IssueRead) => void;
		onFilter: (token: string) => void;
		onFindings: (token: string) => void;
		onHosts: (filter: string) => void;
		onTriage: (issue: IssueRead, state: string) => void;
	}

	let {
		issue: it,
		index,
		term = '',
		columns,
		checked,
		onCheck,
		expanded,
		focused,
		pad,
		onToggle,
		onFilter,
		onFindings,
		onHosts,
		onTriage
	}: Props = $props();

	const MAX_HOSTS = 3;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let fill = $derived(SEVERITY_FILL[it.severity] ?? SEVERITY_FILL.unknown);
	let tone = $derived(rowTone(expanded || checked, focused));
	let pin = $derived(pinTone(expanded || checked, focused));
	let tile = $derived(
		`background:color-mix(in oklch, ${fill} 14%, transparent);color:color-mix(in oklch, ${fill} 85%, var(--foreground));box-shadow:inset 0 0 0 1px color-mix(in oklch, ${fill} 30%, transparent)`
	);
	let setKey = $derived(it.sets[0] ?? null);
	let Icon = $derived((setKey && TEMPLATE_SET_ICONS[setKey]) || PROTOCOL_ICONS[it.protocol] || Bug);
	let likely = $derived((it.epss_score ?? 0) >= EPSS_HIGH);
	let cvss = $derived(it.cvss_score);
	let openCount = $derived(it.states[VulnState.OPEN] ?? 0);
	let reviewed = $derived(it.findings - openCount);
	let allReviewed = $derived(openCount === 0 && it.findings > 0);
	let reach = $derived.by(() => {
		const hosts = plural(it.hosts, 'host', 'hosts');
		if (it.addresses > 0 && it.addresses < it.hosts) {
			return `${hosts} on ${plural(it.addresses, 'address', 'addresses')}`;
		}
		return hosts;
	});
	let hostFilter = $derived(
		it.sample_hosts.length === 1
			? exactToken('host', it.sample_hosts[0])
			: `host:[${it.sample_hosts.map((h) => JSON.stringify(h)).join(',')}]`
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
	class="group relative flex cursor-pointer items-start gap-3 px-4 transition-colors {pad} {tone}"
	role="button"
	tabindex={0}
	data-vuln-row-index={index}
	aria-expanded={expanded}
	aria-label="{expanded ? 'Collapse' : 'Expand'} {it.template_name}"
	onclick={() => onToggle(it)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onToggle(it);
		}
	}}
>
	<span
		class="absolute inset-y-0 left-0 w-[3px] {allReviewed ? 'opacity-30' : ''}"
		style="background:{fill}"
		aria-hidden="true"
	></span>

	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="hidden h-5 shrink-0 items-center sm:flex" onclick={stopProp}>
		<Checkbox
			{checked}
			onCheckedChange={() => onCheck(it.template_id)}
			aria-label="Select {it.template_name}"
			class="transition-opacity {checked
				? 'opacity-100'
				: 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'}"
		/>
	</div>

	<div class="flex min-w-0 gap-3 {ISSUE_LEAD_COLUMNS[0].width}">
		<span class="flex h-5 shrink-0 items-center">
			<span
				class="relative flex size-7 items-center justify-center rounded-md {allReviewed
					? 'opacity-50'
					: ''}"
				style={tile}
			>
				<Icon
					class="size-4 transition-opacity group-hover:opacity-0 {expanded ? 'opacity-0' : ''}"
				/>
				<ChevronRight
					class="absolute size-4 opacity-0 transition-all group-hover:opacity-100 {expanded
						? 'rotate-90 opacity-100'
						: ''}"
				/>
			</span>
		</span>
		<div class="flex min-w-0 flex-1 flex-col gap-1">
			<div class="flex flex-wrap items-start gap-x-2 gap-y-1">
				<span
					class="min-w-0 text-sm leading-5 font-medium wrap-anywhere {allReviewed
						? 'text-muted-foreground'
						: ''}"
				>
					<HighlightText text={it.template_name} {term} />
				</span>
				{#if it.is_kev}
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
				{#if it.new_count > 0}
					<Hint
						text={it.new_count === it.findings
							? 'Not reported by an earlier scan of this target'
							: `${it.new_count} of ${it.findings} findings are new since the previous scan`}
					>
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="flex h-5 shrink-0 items-center"
								onclick={(e) => pivot(e, 'is:new')}
							>
								<Badge variant="info" class="px-1 text-[10px] font-normal">
									{it.new_count === it.findings ? 'new' : `${it.new_count} new`}
								</Badge>
							</button>
						{/snippet}
					</Hint>
				{/if}
				{#if it.corroborated > 0}
					<Hint
						text={it.corroborated === it.findings
							? 'Another check confirms this weakness at the same location'
							: `${it.corroborated} of ${it.findings} findings are confirmed by another check`}
					>
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="flex h-5 shrink-0 items-center"
								onclick={(e) => pivot(e, 'is:corroborated')}
							>
								<Badge variant="secondary" class="gap-1 px-1 text-[10px] font-normal">
									<CheckCheck class="size-2.5" />
									{it.corroborated === it.findings ? 'confirmed' : `${it.corroborated} confirmed`}
								</Badge>
							</button>
						{/snippet}
					</Hint>
				{/if}
			</div>
			<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
				<button
					type="button"
					class="flex h-4 shrink-0 items-center"
					onclick={(e) => pivot(e, exactToken('severity', it.severity))}
					aria-label="Filter to {it.severity}"
				>
					<SeverityMark severity={it.severity} />
				</button>
				<Hint text="Filter to this check">
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="min-w-0 font-mono text-[11px] text-muted-foreground hover:text-foreground hover:underline"
							onclick={(e) => pivot(e, exactToken('template', it.template_id))}
						>
							<HighlightText text={it.template_id} {term} />
						</button>
					{/snippet}
				</Hint>
				{#if setKey}
					<span class="text-[11px] text-muted-foreground">
						{TEMPLATE_SET_LABELS[setKey] ?? setKey}
					</span>
				{/if}
			</div>
		</div>
	</div>

	{#each columns as col (col.key)}
		<div
			class="hidden sm:flex {col.grow ? 'min-w-0 flex-1' : 'shrink-0'} {col.width} {col.align ===
			'right'
				? 'justify-end'
				: ''}"
		>
			{#if col.key === 'affected'}
				<div class="flex min-w-0 flex-col gap-1">
					<span class="text-xs leading-5">
						<span class="font-medium tabular-nums">{reach}</span>
						{#if it.locations > it.hosts}
							<span class="text-muted-foreground">
								· {plural(it.locations, 'location', 'locations')}
							</span>
						{/if}
					</span>
					<div class="flex min-w-0 flex-nowrap items-center gap-1">
						{#each it.sample_hosts.slice(0, MAX_HOSTS) as host (host)}
							<Hint text="Filter to {host}">
								{#snippet child(props)}
									<button
										{...props}
										type="button"
										class="min-w-0 shrink"
										onclick={(e) => pivot(e, exactToken('host', host))}
									>
										<Badge
											variant="outline"
											class="max-w-full px-1 font-mono text-[10px] font-normal hover:bg-accent"
										>
											<span class="truncate">{host}</span>
										</Badge>
									</button>
								{/snippet}
							</Hint>
						{/each}
						{#if it.hosts > MAX_HOSTS}
							<span class="shrink-0 text-[10px] text-muted-foreground tabular-nums">
								+{it.hosts - MAX_HOSTS}
							</span>
						{/if}
					</div>
				</div>
			{:else if col.key === 'risk'}
				<div class="flex min-w-0 flex-wrap items-center gap-1">
					{#if it.cve_ids.length}
						<button
							type="button"
							class="flex h-4 items-center"
							onclick={(e) => pivot(e, exactToken('cve', it.cve_ids[0]))}
						>
							<Badge
								variant="outline"
								class="px-1 font-mono text-[10px] font-normal hover:bg-accent"
							>
								{it.cve_ids[0]}
							</Badge>
						</button>
						{#if it.cve_ids.length > 1}
							<OverflowPopover
								class="shrink-0"
								items={it.cve_ids}
								shown={1}
								label="CVEs"
								mono
								onSelect={(c) => onFilter(exactToken('cve', c))}
							/>
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
					{#if it.epss_score != null}
						<Hint text="Probability of exploitation in the next 30 days">
							{#snippet child(props)}
								<span
									{...props}
									class="font-mono text-xs tabular-nums {likely
										? 'text-warning'
										: 'text-muted-foreground'}"
								>
									{epssPercent(it.epss_score)}
								</span>
							{/snippet}
						</Hint>
					{/if}
					{#if !it.cve_ids.length && it.cvss_score == null && it.epss_score == null}
						<span class="text-xs text-muted-foreground">—</span>
					{/if}
				</div>
			{:else if col.key === 'review'}
				{#if reviewed === 0}
					<span class="text-xs text-muted-foreground">Open</span>
				{:else}
					<Hint
						text={Object.entries(it.states)
							.filter(([state]) => state !== VulnState.OPEN)
							.map(([state, n]) => `${n} ${VULN_STATE_LABELS[state] ?? state}`)
							.join(' · ')}
					>
						{#snippet child(props)}
							<span {...props} class="flex h-5 items-center">
								<Badge variant="secondary" class="px-1.5 text-[10px] font-normal tabular-nums">
									{allReviewed ? 'Reviewed' : `${reviewed} of ${it.findings} reviewed`}
								</Badge>
							</span>
						{/snippet}
					</Hint>
				{/if}
			{:else if col.key === 'seen'}
				<span class="text-xs whitespace-nowrap text-muted-foreground">
					{formatShortDate(it.first_seen)}
				</span>
			{/if}
		</div>
	{/each}

	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class={ACTIONS_PIN} onclick={stopProp}>
		<div class="{ACTIONS_BODY} {pin}">
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="ghost" size="icon" class="size-7">
							<Ellipsis class="size-4" />
							<span class="sr-only">Actions for {it.template_name}</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-60">
					<DropdownMenu.Item onclick={() => onToggle(it)}>
						{expanded ? 'Collapse' : `Show ${plural(it.findings, 'finding', 'findings')}`}
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={() => onFindings(exactToken('template', it.template_id))}>
						<Filter class="mr-2 size-3.5" /> Open as a findings list
					</DropdownMenu.Item>
					{#if it.sample_hosts.length}
						<DropdownMenu.Item onclick={() => onHosts(hostFilter)}>
							<Globe class="mr-2 size-3.5" /> Affected hosts in Web Assets
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onclick={() => copy(it.template_id)}>
						<Copy class="mr-2 size-3.5" /> Copy check identifier
					</DropdownMenu.Item>
					{#if it.template_url}
						<DropdownMenu.Item>
							{#snippet child({ props })}
								<a {...props} href={it.template_url} target="_blank" rel="noopener noreferrer">
									<ExternalLink class="mr-2 size-3.5" /> View the check
								</a>
							{/snippet}
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Label
						>Review all {plural(it.findings, 'finding', 'findings')}</DropdownMenu.Label
					>
					<DropdownMenu.RadioGroup
						value={allReviewed && Object.keys(it.states).length === 1
							? Object.keys(it.states)[0]
							: reviewed === 0
								? VulnState.OPEN
								: ''}
						onValueChange={(state) => onTriage(it, state)}
					>
						{#each Object.entries(VULN_STATE_LABELS) as [value, label] (value)}
							<DropdownMenu.RadioItem {value}>{label}</DropdownMenu.RadioItem>
						{/each}
					</DropdownMenu.RadioGroup>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
