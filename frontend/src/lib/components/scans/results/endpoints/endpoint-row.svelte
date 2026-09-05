<script lang="ts">
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Copy from '@lucide/svelte/icons/copy';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';

	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import HighlightText from '../table/highlight-text.svelte';
	import TechIcon from '../tech-icon.svelte';
	import SourceMarks from './source-marks.svelte';
	import StatusMark from './status-mark.svelte';
	import { ACTIONS_BODY, ACTIONS_PIN, pinTone, rowTone } from '../table/columns';
	import { ENDPOINT_COLUMNS, ENDPOINT_LEAD_COLUMNS, OUTLINE_LEAD_COLUMNS } from './columns';
	import { GUIDE_WIDTH, OUTLINE_ROW_ATTR } from './outline-context';
	import {
		ENDPOINT_CLASS_ICONS,
		ENDPOINT_CLASS_LABELS,
		ENDPOINT_CLASS_TONE,
		EndpointSource,
		INTEREST_LABELS,
		SENSITIVE_INTEREST,
		STATIC_CLASSES
	} from '$lib/config/endpoints';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { EndpointRead } from '$lib/utilities/endpoints';

	interface Props {
		endpoint: EndpointRead;
		columns: string[];
		terms?: string[];
		active?: boolean;
		focused?: boolean;
		pad?: string;
		outline?: boolean;
		depth?: number;
		label?: string;
		rowKey?: string;
		gone?: boolean;
		parentKey?: string;
		onOpen?: (e: EndpointRead) => void;
		onFilter?: (token: string) => void;
	}

	let {
		endpoint,
		columns,
		terms = [],
		active = false,
		focused = false,
		pad = 'py-3',
		outline = false,
		depth = 0,
		label,
		rowKey,
		gone = false,
		parentKey = '',
		onOpen,
		onFilter
	}: Props = $props();

	let shown = $derived(ENDPOINT_COLUMNS.filter((c) => columns.includes(c.key)));
	let ClassIcon = $derived(ENDPOINT_CLASS_ICONS[endpoint.endpoint_class]);
	let classTone = $derived(ENDPOINT_CLASS_TONE[endpoint.endpoint_class] ?? 'text-muted-foreground');
	let sensitive = $derived(endpoint.interest.filter((i) => SENSITIVE_INTEREST.has(i)));
	let testable = $derived(endpoint.interest.filter((i) => !SENSITIVE_INTEREST.has(i)));
	let isRoot = $derived(endpoint.path === '/');
	let isIndex = $derived(endpoint.filename === null && !label);
	let dirLabel = $derived(isRoot ? '' : endpoint.dir_path);
	let leaf = $derived(label ?? endpoint.filename ?? '/');
	let dim = $derived(STATIC_CLASSES.has(endpoint.endpoint_class));
	// several origins can share one path; only the index rows of a folder need to tell them apart
	let origin = $derived.by(() => {
		if (!isIndex) return '';
		const port = endpoint.port && ![80, 443].includes(endpoint.port) ? `:${endpoint.port}` : '';
		const scheme = endpoint.scheme && endpoint.scheme !== 'https' ? endpoint.scheme : '';
		return scheme || port ? `${scheme || 'https'}${port}` : '';
	});
	let attrs = $derived(
		rowKey
			? {
					[OUTLINE_ROW_ATTR]: rowKey,
					'data-outline-kind': 'leaf',
					'data-outline-name': leaf,
					'data-outline-parent': parentKey
				}
			: {}
	);

	function size(bytes: number | null): string {
		if (bytes == null) return '—';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
		return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
	}
</script>

{#snippet badges(compact: boolean)}
	{#if sensitive.length || testable.length || endpoint.is_new || gone || endpoint.sources.includes(EndpointSource.ROBOTS)}
		<div class="flex flex-wrap items-center gap-1 {compact ? '' : 'mt-1'}">
			{#each sensitive as key (key)}
				<Badge variant="destructive" class="h-4 gap-1 px-1.5 text-[10px]">
					<ShieldAlert class="size-2.5" />
					{INTEREST_LABELS[key] ?? key}
				</Badge>
			{/each}
			{#each testable as key (key)}
				<Badge variant="warning" class="h-4 px-1.5 text-[10px]">
					{INTEREST_LABELS[key] ?? key}
				</Badge>
			{/each}
			{#if compact && endpoint.is_new}
				<Badge variant="info" class="h-4 px-1 text-[10px]">New</Badge>
			{/if}
			{#if endpoint.sources.includes(EndpointSource.ROBOTS)}
				<Hint
					text="Listed in the site's own robots.txt. What the owner asks crawlers to skip is worth a look."
				>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<Badge variant="outline" class="h-4 px-1.5 text-[10px] font-normal">robots.txt</Badge>
						</span>
					{/snippet}
				</Hint>
			{/if}
			{#if gone}
				<Badge variant="outline" class="h-4 px-1.5 text-[10px] font-normal text-muted-foreground">
					Not found this scan
				</Badge>
			{/if}
		</div>
	{/if}
{/snippet}

{#snippet statusCell()}
	<StatusMark status={endpoint.status_code} probed={endpoint.is_probed} />
{/snippet}

<div
	class="group flex items-start gap-3 border-b px-4 text-sm transition-colors {pad} {rowTone(
		active,
		focused
	)}"
	role="button"
	tabindex="0"
	{...attrs}
	onclick={() => onOpen?.(endpoint)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen?.(endpoint);
		}
	}}
>
	{#if outline}
		<div class="min-w-0 flex-1 {OUTLINE_LEAD_COLUMNS[0].width}">
			<div class="flex items-start gap-x-1.5 leading-5">
				{#each Array(depth) as _, i (i)}
					<span class="{GUIDE_WIDTH} -ml-1.5 h-5 shrink-0 border-l border-border/70 ml-[7px]"
					></span>
				{/each}
				<span class="size-4 shrink-0"></span>
				<span class="flex h-5 shrink-0 items-center {dim ? 'text-muted-foreground/70' : classTone}">
					<ClassIcon class="size-4" />
				</span>
				<span class="flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-1">
					<span class="font-mono text-sm break-all {dim ? 'text-muted-foreground' : 'font-medium'}">
						<HighlightText text={leaf} {terms} />
					</span>
					{#if isIndex}
						<span class="text-[11px] text-muted-foreground italic">index</span>
					{/if}
					{#if origin}
						<span class="font-mono text-[11px] text-muted-foreground">{origin}</span>
					{/if}
					{#if endpoint.param_count > 0}
						<span class="font-mono text-xs text-primary">?{endpoint.params.join('&')}</span>
					{/if}
					{@render badges(true)}
				</span>
			</div>
		</div>
		<div class="{OUTLINE_LEAD_COLUMNS[1].width} shrink-0">
			{@render statusCell()}
		</div>
	{:else}
		<div class="{ENDPOINT_LEAD_COLUMNS[0].width} shrink-0">
			{@render statusCell()}
		</div>

		<div class="min-w-0 flex-1 {ENDPOINT_LEAD_COLUMNS[1].width}">
			<div class="flex flex-wrap items-baseline gap-x-1 leading-5">
				<span class="font-mono text-xs text-muted-foreground">{dirLabel}</span>
				{#if leaf}
					<span class="font-mono text-sm font-medium break-all">
						<HighlightText text={leaf} {terms} />
					</span>
				{/if}
				{#if endpoint.param_count > 0}
					<span class="font-mono text-xs text-primary">
						?{endpoint.params.join('&')}
					</span>
				{/if}
				{#if endpoint.is_new}
					<Badge variant="info" class="h-4 px-1 text-[10px]">New</Badge>
				{/if}
			</div>
			{@render badges(false)}
		</div>
	{/if}

	{#each shown as column (column.key)}
		<div class="{column.width} min-w-0 shrink-0 {column.align === 'right' ? 'text-right' : ''}">
			{#if column.key === 'host'}
				<button
					type="button"
					class="block w-full truncate text-left text-xs hover:text-primary hover:underline"
					onclick={(e) => {
						e.stopPropagation();
						onFilter?.(`host:${endpoint.host}`);
					}}
				>
					<HighlightText text={endpoint.host} {terms} />
				</button>
			{:else if column.key === 'kind'}
				<span class="flex h-5 items-center gap-1.5 text-xs text-muted-foreground">
					<ClassIcon class="size-3.5 shrink-0" />
					{ENDPOINT_CLASS_LABELS[endpoint.endpoint_class] ?? endpoint.endpoint_class}
				</span>
			{:else if column.key === 'params'}
				{#if endpoint.param_count === 0}
					<span class="text-xs text-muted-foreground">—</span>
				{:else}
					<div class="flex flex-wrap gap-1">
						{#each endpoint.params.slice(0, 3) as name (name)}
							<button
								type="button"
								class="rounded bg-muted px-1 font-mono text-[10px] hover:bg-muted/70"
								onclick={(e) => {
									e.stopPropagation();
									onFilter?.(`param:${name}`);
								}}
							>
								{name}
							</button>
						{/each}
						{#if endpoint.params.length > 3}
							<span class="text-[10px] text-muted-foreground">
								+{endpoint.params.length - 3}
							</span>
						{/if}
					</div>
					{#if endpoint.variants > 1}
						<Hint
							text="This endpoint was seen with {endpoint.variants}{endpoint.more_variants
								? ' or more'
								: ''} different parameter values."
						>
							{#snippet child(props)}
								<span {...props} class="mt-0.5 block text-[10px] text-muted-foreground">
									{endpoint.variants}{endpoint.more_variants ? '+' : ''} value sets
								</span>
							{/snippet}
						</Hint>
					{/if}
				{/if}
			{:else if column.key === 'title'}
				<span class="line-clamp-2 text-xs text-muted-foreground">
					{#if endpoint.title}
						<HighlightText text={endpoint.title} {terms} />
					{:else}
						—
					{/if}
				</span>
			{:else if column.key === 'tech'}
				<div class="flex flex-wrap items-center gap-1">
					{#each endpoint.tech.slice(0, 3) as name (name)}
						<TechIcon {name} class="size-4" />
					{/each}
					{#if endpoint.tech.length === 0}
						<span class="text-xs text-muted-foreground">—</span>
					{/if}
				</div>
			{:else if column.key === 'size'}
				<span class="font-mono text-xs tabular-nums text-muted-foreground">
					{size(endpoint.content_length)}
				</span>
			{:else if column.key === 'sources'}
				<SourceMarks sources={endpoint.sources} evidence={endpoint.evidence} />
			{:else if column.key === 'seen'}
				<span class="text-xs text-muted-foreground">
					{endpoint.discovered_at ? formatShortDate(endpoint.discovered_at) : '—'}
				</span>
			{/if}
		</div>
	{/each}

	<div class="{ACTIONS_PIN} {pinTone(active, focused)}">
		<div class={ACTIONS_BODY}>
			<Hint text="Copy URL">
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-7"
						onclick={(e) => {
							e.stopPropagation();
							void writeClipboard(endpoint.url);
						}}
					>
						<Copy class="size-3.5" />
					</Button>
				{/snippet}
			</Hint>
			<Hint text="Open in a new tab">
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-7"
						href={endpoint.url}
						target="_blank"
						rel="noopener noreferrer"
						onclick={(e) => e.stopPropagation()}
					>
						<ExternalLink class="size-3.5" />
					</Button>
				{/snippet}
			</Hint>
		</div>
	</div>
</div>
