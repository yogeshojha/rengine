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
	import { ENDPOINT_COLUMNS, ENDPOINT_LEAD_COLUMNS } from './columns';
	import {
		ENDPOINT_CLASS_ICONS,
		ENDPOINT_CLASS_LABELS,
		INTEREST_LABELS,
		SENSITIVE_INTEREST
	} from '$lib/config/endpoints';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { EndpointRead } from '$lib/utilities/endpoints';

	interface Props {
		endpoint: EndpointRead;
		columns: string[];
		term?: string;
		active?: boolean;
		focused?: boolean;
		pad?: string;
		onOpen?: (e: EndpointRead) => void;
		onFilter?: (token: string) => void;
	}

	let {
		endpoint,
		columns,
		term = '',
		active = false,
		focused = false,
		pad = 'py-3',
		onOpen,
		onFilter
	}: Props = $props();

	let shown = $derived(ENDPOINT_COLUMNS.filter((c) => columns.includes(c.key)));
	let ClassIcon = $derived(ENDPOINT_CLASS_ICONS[endpoint.endpoint_class]);
	let sensitive = $derived(endpoint.interest.filter((i) => SENSITIVE_INTEREST.has(i)));
	let testable = $derived(endpoint.interest.filter((i) => !SENSITIVE_INTEREST.has(i)));
	let isRoot = $derived(endpoint.path === '/');
	let dirLabel = $derived(isRoot ? '' : endpoint.dir_path);
	let leaf = $derived(endpoint.filename ?? (isRoot ? '/' : ''));

	function size(bytes: number | null): string {
		if (bytes == null) return '—';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
		return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
	}
</script>

<div
	class="group flex items-start gap-3 border-b px-4 text-sm transition-colors {pad} {rowTone(
		active,
		focused
	)}"
	role="button"
	tabindex="0"
	onclick={() => onOpen?.(endpoint)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen?.(endpoint);
		}
	}}
>
	<div class="{ENDPOINT_LEAD_COLUMNS[0].width} shrink-0">
		<StatusMark status={endpoint.status_code} probed={endpoint.is_probed} />
	</div>

	<div class="min-w-0 flex-1 {ENDPOINT_LEAD_COLUMNS[1].width}">
		<div class="flex flex-wrap items-baseline gap-x-1 leading-5">
			<span class="font-mono text-xs text-muted-foreground">{dirLabel}</span>
			{#if leaf}
				<span class="font-mono text-sm font-medium break-all">
					<HighlightText text={leaf} {term} />
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
		{#if sensitive.length || testable.length}
			<div class="mt-1 flex flex-wrap items-center gap-1">
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
			</div>
		{/if}
	</div>

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
					<HighlightText text={endpoint.host} {term} />
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
						<HighlightText text={endpoint.title} {term} />
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
					{formatShortDate(endpoint.discovered_at)}
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
