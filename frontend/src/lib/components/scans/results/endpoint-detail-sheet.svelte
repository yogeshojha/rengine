<script lang="ts">
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Copy from '@lucide/svelte/icons/copy';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Globe from '@lucide/svelte/icons/globe';
	import ListTree from '@lucide/svelte/icons/list-tree';

	import * as Sheet from '$lib/components/ui/sheet';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import TechIcon from './tech-icon.svelte';
	import StatusMark from './endpoints/status-mark.svelte';
	import PathBreadcrumb from './endpoints/path-breadcrumb.svelte';
	import {
		ENDPOINT_CLASS_LABELS,
		INTEREST_LABELS,
		PASSIVE_SOURCES,
		SOURCE_ICONS,
		SENSITIVE_INTEREST,
		EndpointSource
	} from '$lib/config/endpoints';
	import { endpointsApi } from '$lib/api/scan-results';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { EndpointDetail, EndpointRead } from '$lib/utilities/endpoints';

	interface Props {
		endpoint: EndpointRead | null;
		projectId: string;
		scanId: string;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		index: number;
		pageOffset: number;
		total: number;
		onStep: (dir: -1 | 1) => void;
		onFilter?: (token: string) => void;
		onHost?: (filter: string) => void;
		onReveal?: (e: EndpointRead) => void;
	}

	let {
		endpoint,
		projectId,
		scanId,
		open,
		onOpenChange,
		index,
		pageOffset,
		total,
		onStep,
		onFilter,
		onHost,
		onReveal
	}: Props = $props();

	let detail = $state<EndpointDetail | null>(null);
	let loading = $state(false);
	let loadedId = '';

	$effect(() => {
		const id = endpoint?.id ?? '';
		if (!open || !id || id === loadedId) return;
		loadedId = id;
		loading = true;
		endpointsApi
			.detail(projectId, scanId, id)
			.then((d) => {
				if (loadedId === id) detail = d;
			})
			.catch(() => {
				if (loadedId === id) detail = null;
			})
			.finally(() => {
				if (loadedId === id) loading = false;
			});
	});

	let row = $derived(detail?.id === endpoint?.id ? detail : null);
	let position = $derived(index >= 0 ? pageOffset + index + 1 : 0);
	let sensitive = $derived((endpoint?.interest ?? []).filter((i) => SENSITIVE_INTEREST.has(i)));
	let testable = $derived((endpoint?.interest ?? []).filter((i) => !SENSITIVE_INTEREST.has(i)));

	function size(bytes: number | null | undefined): string {
		if (bytes == null) return '—';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
		return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
	}
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
		{#if endpoint}
			<Sheet.Header class="gap-2 border-b px-5 py-4">
				<div class="flex items-center gap-2">
					<StatusMark status={endpoint.status_code} probed={endpoint.is_probed} />
					<Badge variant="outline" class="text-[10px]">
						{ENDPOINT_CLASS_LABELS[endpoint.endpoint_class] ?? endpoint.endpoint_class}
					</Badge>
					{#if endpoint.is_new}
						<Badge variant="info" class="text-[10px]">New</Badge>
					{/if}
					{#if total > 0 && position > 0}
						<div class="ml-auto flex items-center gap-1">
							<span class="text-xs tabular-nums text-muted-foreground">
								{position} of {total.toLocaleString()}
							</span>
							<Button
								variant="ghost"
								size="icon"
								class="size-7"
								aria-label="Previous endpoint"
								disabled={position <= 1}
								onclick={() => onStep(-1)}
							>
								<ChevronLeft class="size-4" />
							</Button>
							<Button
								variant="ghost"
								size="icon"
								class="size-7"
								aria-label="Next endpoint"
								disabled={position >= total}
								onclick={() => onStep(1)}
							>
								<ChevronRight class="size-4" />
							</Button>
						</div>
					{/if}
				</div>
				<Sheet.Title class="font-mono text-sm break-all">{endpoint.url}</Sheet.Title>
				<div class="flex items-center gap-2">
					<Button
						variant="outline"
						size="sm"
						class="h-7 gap-1.5 text-xs"
						onclick={() => writeClipboard(endpoint.url)}
					>
						<Copy class="size-3" /> Copy
					</Button>
					<Button
						variant="outline"
						size="sm"
						class="h-7 gap-1.5 text-xs"
						href={endpoint.url}
						target="_blank"
						rel="noopener noreferrer"
					>
						<ExternalLink class="size-3" /> Open
					</Button>
					<Button
						variant="outline"
						size="sm"
						class="h-7 gap-1.5 text-xs"
						onclick={() => onHost?.(endpoint.host)}
					>
						<Globe class="size-3" /> View host
					</Button>
					{#if onReveal}
						<Button
							variant="outline"
							size="sm"
							class="h-7 gap-1.5 text-xs"
							onclick={() => onReveal(endpoint)}
						>
							<ListTree class="size-3" /> Show in structure
						</Button>
					{/if}
				</div>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="space-y-6 px-5 py-4">
					<section class="space-y-2">
						<h3 class="text-xs font-medium text-muted-foreground uppercase">Location</h3>
						<PathBreadcrumb
							host={endpoint.host}
							path={endpoint.dir_path}
							onSelect={(h, p) => onFilter?.(`dir:"${p}"` + (h ? ` host:${h}` : ''))}
						/>
						<dl class="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
							<div class="flex justify-between gap-2">
								<dt class="text-muted-foreground">Depth</dt>
								<dd class="tabular-nums">{endpoint.depth}</dd>
							</div>
							<div class="flex justify-between gap-2">
								<dt class="text-muted-foreground">Port</dt>
								<dd class="tabular-nums">{endpoint.port}</dd>
							</div>
							{#if row}
								<div class="flex justify-between gap-2">
									<dt class="text-muted-foreground">Siblings in folder</dt>
									<dd class="tabular-nums">{row.siblings}</dd>
								</div>
							{/if}
							{#if endpoint.found_on}
								<div class="col-span-2 flex flex-col gap-0.5">
									<dt class="text-muted-foreground">Reached from</dt>
									<dd class="font-mono break-all">{endpoint.found_on}</dd>
								</div>
							{/if}
						</dl>
					</section>

					{#if sensitive.length || testable.length}
						<section class="space-y-2">
							<h3 class="text-xs font-medium text-muted-foreground uppercase">Worth testing</h3>
							<div class="flex flex-wrap gap-1.5">
								{#each sensitive as key (key)}
									<Badge variant="destructive" class="gap-1">
										<ShieldAlert class="size-3" />
										{INTEREST_LABELS[key] ?? key}
									</Badge>
								{/each}
								{#each testable as key (key)}
									<Badge variant="warning">{INTEREST_LABELS[key] ?? key}</Badge>
								{/each}
							</div>
						</section>
					{/if}

					<section class="space-y-2">
						<h3 class="text-xs font-medium text-muted-foreground uppercase">Evidence</h3>
						<p class="text-xs text-muted-foreground">
							Every source that reported this endpoint, and what it saw.
						</p>
						<div class="space-y-2">
							{#each endpoint.evidence as e (e.source)}
								{@const Icon = SOURCE_ICONS[e.source] ?? SOURCE_ICONS[EndpointSource.OTHER]}
								<div class="flex gap-2.5 rounded-md border p-2.5">
									<span
										class="flex size-7 shrink-0 items-center justify-center rounded border {PASSIVE_SOURCES.has(
											e.source
										)
											? 'border-border/60 text-muted-foreground'
											: 'border-primary/25 bg-primary/5 text-primary'}"
									>
										<Icon class="size-3.5" />
									</span>
									<div class="min-w-0 flex-1">
										<div class="flex items-baseline gap-2">
											<span class="text-sm font-medium">{e.label}</span>
											{#if e.kind !== 'active'}
												<Hint text="This source sent no request to the target.">
													{#snippet child(props)}
														<span {...props} class="text-[10px] text-muted-foreground">
															no request sent
														</span>
													{/snippet}
												</Hint>
											{/if}
											{#if e.observed_at}
												<span class="ml-auto text-[10px] text-muted-foreground">
													{formatShortDate(e.observed_at)}
												</span>
											{/if}
										</div>
										{#if e.detail}
											<p class="mt-0.5 text-xs text-muted-foreground">{e.detail}</p>
										{/if}
										{#if e.found_on}
											<p class="mt-0.5 font-mono text-[11px] break-all text-muted-foreground">
												{e.found_on}
											</p>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</section>

					{#if endpoint.param_count > 0}
						<section class="space-y-2">
							<h3 class="text-xs font-medium text-muted-foreground uppercase">Parameters</h3>
							<div class="flex flex-wrap gap-1.5">
								{#each endpoint.params as name (name)}
									<button
										type="button"
										class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs hover:bg-muted/70"
										onclick={() => onFilter?.(`param:${name}`)}
									>
										{name}
									</button>
								{/each}
							</div>
							<p class="text-xs text-muted-foreground">
								Seen with {endpoint.variants}{endpoint.more_variants ? ' or more' : ''}
								{endpoint.variants === 1 ? 'value set' : 'value sets'}. Values are samples; the
								endpoint is identified by its parameter names.
							</p>
							{#if loading && !row}
								<Skeleton class="h-16 w-full" />
							{:else if row?.param_samples.length}
								<div class="space-y-1 rounded-md border p-2">
									{#each row.param_samples.slice(0, 5) as sample, i (i)}
										<p class="font-mono text-[11px] break-all text-muted-foreground">
											{Object.entries(sample)
												.map(([k, v]) => `${k}=${v}`)
												.join('&')}
										</p>
									{/each}
								</div>
							{/if}
						</section>
					{/if}

					<section class="space-y-2">
						<h3 class="text-xs font-medium text-muted-foreground uppercase">Response</h3>
						{#if !endpoint.is_probed}
							<p class="text-xs text-muted-foreground">
								This scan did not request this endpoint, so nothing below was observed.
							</p>
						{:else}
							<dl class="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
								{#each [['Status', endpoint.status_code], ['Content type', endpoint.content_type], ['Size', size(endpoint.content_length)], ['Words', endpoint.words], ['Lines', endpoint.lines], ['Response time', endpoint.response_time ? `${Math.round(endpoint.response_time * 1000)} ms` : null]] as [label, value] (label)}
									{#if value !== null && value !== undefined}
										<div class="flex justify-between gap-2">
											<dt class="text-muted-foreground">{label}</dt>
											<dd class="tabular-nums">{value}</dd>
										</div>
									{/if}
								{/each}
							</dl>
							{#if endpoint.title}
								<div class="flex flex-col gap-0.5 text-xs">
									<span class="text-muted-foreground">Title</span>
									<p class="text-sm">{endpoint.title}</p>
								</div>
							{/if}
							{#if endpoint.redirect_location}
								<p class="font-mono text-xs break-all text-muted-foreground">
									→ {endpoint.redirect_location}
								</p>
							{/if}
							{#if endpoint.tech.length}
								<div class="flex flex-wrap items-center gap-1.5 pt-1">
									{#each endpoint.tech as name (name)}
										<button
											type="button"
											class="flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs hover:bg-muted/50"
											onclick={() => onFilter?.(`tech:${name}`)}
										>
											<TechIcon {name} class="size-3.5" />
											{name}
										</button>
									{/each}
								</div>
							{/if}
						{/if}
					</section>
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>
