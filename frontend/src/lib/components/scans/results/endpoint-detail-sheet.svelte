<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { SEND_SHORTCUT, type ActionKind } from '$lib/config/connectors';
	import { exactToken, filterToken } from '$lib/utilities/scan-insights';
	import { formatResponseTime } from '$lib/utilities/scan-correlation';
	import { formatBytes } from '$lib/utilities/format';
	import NotesButton from '$lib/components/notes/notes-button.svelte';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Globe from '@lucide/svelte/icons/globe';
	import ListTree from '@lucide/svelte/icons/list-tree';
	import Terminal from '@lucide/svelte/icons/terminal';

	import * as Sheet from '$lib/components/ui/sheet';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import TechIcon from './tech-icon.svelte';
	import StatusMark from './endpoints/status-mark.svelte';
	import PathBreadcrumb from './endpoints/path-breadcrumb.svelte';
	import ProxySend from './endpoints/proxy-send.svelte';
	import { previewHandoff } from './endpoints/proxy';
	import { SHEET_HEAD, sheetStep, type SheetAction } from './sheet';
	import SheetTop from './sheet-top.svelte';
	import SheetBar from './sheet-bar.svelte';
	import SheetMore from './sheet-more.svelte';
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
	import { curlFor, type EndpointDetail, type EndpointRead } from '$lib/utilities/endpoints';
	import { externalHref } from '$lib/utilities/links';
	import type { Connector, ConnectorSpec, HandoffResult } from '$lib/types/connector';

	interface Props {
		endpoint: EndpointRead | null;
		projectId: string;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		index: number;
		pageOffset: number;
		total: number;
		capped?: boolean;
		onStep: (dir: -1 | 1) => void;
		onFilter?: (token: string) => void;
		onHost?: (filter: string) => void;
		onReveal?: (e: EndpointRead) => void;
		connectors?: Connector[];
		catalog?: ConnectorSpec[];
		onSend?: (
			e: EndpointRead,
			connectorId: string,
			kind: ActionKind,
			request?: string
		) => Promise<HandoffResult | null> | void;
	}

	let {
		endpoint,
		projectId,
		open,
		onOpenChange,
		index,
		pageOffset,
		total,
		capped = false,
		onStep,
		onFilter,
		onHost,
		onReveal,
		connectors = [],
		catalog = [],
		onSend
	}: Props = $props();

	let detail = $state<EndpointDetail | null>(null);
	let loading = $state(false);
	let loadedId = '';

	$effect(() => {
		const id = endpoint?.id ?? '';
		const scanId = endpoint?.scan_id ?? '';
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

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const EP = SURFACE[SurfaceDimension.ENDPOINTS];

	let contentEl = $state<HTMLElement | null>(null);
	let row = $derived(detail?.id === endpoint?.id ? detail : null);
	let sensitive = $derived((endpoint?.interest ?? []).filter((i) => SENSITIVE_INTEREST.has(i)));
	let testable = $derived((endpoint?.interest ?? []).filter((i) => !SENSITIVE_INTEREST.has(i)));
	let more = $derived.by((): SheetAction[] => {
		const e = endpoint;
		if (!e) return [];
		const out: SheetAction[] = [
			{ label: 'Copy curl command', icon: Terminal, run: () => copyCurl(e) }
		];
		if (onHost) {
			out.push({
				label: `Open in ${WEB.label}`,
				icon: Globe,
				run: () => onHost(exactToken('host', e.host))
			});
		}
		if (onReveal) out.push({ label: 'Show in structure', icon: ListTree, run: () => onReveal(e) });
		return out;
	});

	async function copyCurl(e: EndpointRead) {
		if (await writeClipboard(curlFor(e))) toast.success('curl command copied');
	}

	function preview(e: EndpointRead, connectorId: string) {
		return previewHandoff({
			connectorId,
			projectId,
			scanId: e.scan_id,
			body: { endpoint_ids: [e.id] }
		});
	}
</script>

<svelte:window onkeydown={(e) => sheetStep(e, open, onStep)} />

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content
		bind:ref={contentEl}
		side="right"
		tabindex={-1}
		class="flex w-full flex-col gap-0 p-0 outline-none sm:max-w-2xl"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			contentEl?.focus();
		}}
	>
		{#if endpoint}
			<Sheet.Header class={SHEET_HEAD}>
				<SheetTop noun={EP.noun} {index} {pageOffset} {total} {capped} {onStep}>
					<StatusMark status={endpoint.status_code} probed={endpoint.is_probed} />
					<Badge variant="outline" class="text-2xs">
						{ENDPOINT_CLASS_LABELS[endpoint.endpoint_class] ?? endpoint.endpoint_class}
					</Badge>
					{#if endpoint.is_new}
						<Badge variant="info" class="text-2xs">New</Badge>
					{/if}
				</SheetTop>
				<div class="flex min-w-0 items-start gap-1">
					<Sheet.Title class="min-w-0 py-1 font-mono text-sm break-all">{endpoint.url}</Sheet.Title>
					<CopyButton value={endpoint.url} />
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon-sm"
									class="size-7 shrink-0"
									href={externalHref(endpoint.url)}
									target="_blank"
									rel="noopener noreferrer"
									aria-label="Open in browser"
								>
									<ExternalLink />
								</Button>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>Open in browser</Tooltip.Content>
					</Tooltip.Root>
				</div>
			</Sheet.Header>

			<SheetBar>
				<NotesButton
					anchor={{
						targetId: endpoint.target_id,
						scanId: endpoint.scan_id,
						dimension: SurfaceDimension.ENDPOINTS,
						assetKey: endpoint.signature,
						assetLabel: endpoint.url
					}}
					class="h-8"
				/>
				{#if onSend && connectors.length}
					<ProxySend
						{connectors}
						{catalog}
						shortcut={SEND_SHORTCUT}
						class="h-8"
						onSend={(id, kind, request) => onSend(endpoint, id, kind, request)}
						onPreview={(id) => preview(endpoint, id)}
					/>
				{/if}
				<SheetMore actions={more} />
			</SheetBar>

			<ScrollArea class="min-h-0 flex-1">
				<div class="space-y-6 px-5 py-4">
					<section class="space-y-2">
						<h3 class="text-xs font-medium text-muted-foreground uppercase">Location</h3>
						<PathBreadcrumb
							host={endpoint.host}
							path={endpoint.dir_path}
							onSelect={(h, p) => onFilter?.(`${filterToken('dir', p)} ${filterToken('host', h)}`)}
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
							<h3 class="text-xs font-medium text-muted-foreground uppercase">Interest</h3>
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
												<Hint text="Passive source">
													{#snippet child(props)}
														<span {...props} class="text-2xs text-muted-foreground">
															no request sent
														</span>
													{/snippet}
												</Hint>
											{/if}
											{#if e.observed_at}
												<span class="ml-auto text-2xs text-muted-foreground">
													{formatShortDate(e.observed_at)}
												</span>
											{/if}
										</div>
										{#if e.detail}
											<p class="mt-0.5 text-xs text-muted-foreground">{e.detail}</p>
										{/if}
										{#if e.found_on}
											<p class="mt-0.5 font-mono text-2xs break-all text-muted-foreground">
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
										onclick={() => onFilter?.(filterToken('param', name))}
									>
										{name}
									</button>
								{/each}
							</div>
							<p class="text-xs text-muted-foreground">
								Seen with {endpoint.variants}{endpoint.more_variants ? ' or more' : ''}
								{endpoint.variants === 1 ? 'value set' : 'value sets'}.
							</p>
							{#if loading && !row}
								<Skeleton class="h-16 w-full" />
							{:else if row?.param_samples.length}
								<div class="space-y-1 rounded-md border p-2">
									{#each row.param_samples.slice(0, 5) as sample, i (i)}
										<p class="font-mono text-2xs break-all text-muted-foreground">
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
							<p class="text-xs text-muted-foreground">Not requested.</p>
						{:else}
							<dl class="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
								{#each [['Status', endpoint.status_code], ['Content type', endpoint.content_type], ['Size', formatBytes(endpoint.content_length)], ['Words', endpoint.words?.toLocaleString()], ['Lines', endpoint.lines?.toLocaleString()], ['Response time', endpoint.response_time ? formatResponseTime(endpoint.response_time) : null]] as [label, value] (label)}
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
											onclick={() => onFilter?.(filterToken('tech', name))}
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
