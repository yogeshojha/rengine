<script lang="ts">
	import { untrack } from 'svelte';
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
	import MapPin from '@lucide/svelte/icons/map-pin';
	import ScanEye from '@lucide/svelte/icons/scan-eye';
	import SearchCheck from '@lucide/svelte/icons/search-check';
	import Variable from '@lucide/svelte/icons/variable';
	import ArrowDownLeft from '@lucide/svelte/icons/arrow-down-left';

	import * as Sheet from '$lib/components/ui/sheet';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import TechIcon from './tech-icon.svelte';
	import StatusMark from './endpoints/status-mark.svelte';
	import PathBreadcrumb from './endpoints/path-breadcrumb.svelte';
	import ProxySend from './endpoints/proxy-send.svelte';
	import { SHEET_ROW, SHEET_DT, SHEET_HEAD, sheetStep, type SheetAction } from './sheet';
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
			kind: ActionKind
		) => Promise<HandoffResult | null> | void;
		/** where focus goes when the sheet closes; the table hands it to its cursor row */
		onCloseAutoFocus?: (e: Event) => void;
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
		onSend,
		onCloseAutoFocus
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
	let bodyEl = $state<HTMLElement | null>(null);
	let scrolledFor = '';

	$effect.pre(() => {
		const id = open ? (endpoint?.id ?? '') : '';
		if (id === scrolledFor) return;
		scrolledFor = id;
		if (!id) return;
		untrack(() => bodyEl?.scrollTo({ top: 0 }));
	});

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
		{onCloseAutoFocus}
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
									<ExternalLink class="size-3.5 text-muted-foreground" />
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
						onSend={(id, kind) => onSend(endpoint, id, kind)}
					/>
				{/if}
				<SheetMore actions={more} />
			</SheetBar>

			<ScrollArea class="min-h-0 flex-1" bind:viewportRef={bodyEl}>
				<div class="flex flex-col gap-6 p-5">
					<section class="flex flex-col gap-2">
						<SectionHead icon={MapPin} title="Location" />
						<PathBreadcrumb
							host={endpoint.host}
							path={endpoint.dir_path}
							onSelect={(h, p) => onFilter?.(`${filterToken('dir', p)} ${filterToken('host', h)}`)}
						/>
						<dl class="flex flex-col divide-y divide-border/60">
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Depth</dt>
								<dd class="text-sm tabular-nums">{endpoint.depth}</dd>
							</div>
							<div class={SHEET_ROW}>
								<dt class={SHEET_DT}>Port</dt>
								<dd class="font-mono text-sm tabular-nums">{endpoint.port}</dd>
							</div>
							{#if row}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Siblings in folder</dt>
									<dd class="text-sm tabular-nums">{row.siblings.toLocaleString()}</dd>
								</div>
							{/if}
							{#if endpoint.found_on}
								<div class={SHEET_ROW}>
									<dt class={SHEET_DT}>Reached from</dt>
									<dd class="font-mono text-xs break-all">{endpoint.found_on}</dd>
								</div>
							{/if}
						</dl>
					</section>

					{#if sensitive.length || testable.length}
						<section class="flex flex-col gap-2">
							<SectionHead icon={ScanEye} title="Interest" />
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

					<section class="flex flex-col gap-2">
						<SectionHead icon={SearchCheck} title="Evidence" />
						<div class="flex flex-col gap-2">
							{#each endpoint.evidence as e (e.source)}
								{@const Icon = SOURCE_ICONS[e.source] ?? SOURCE_ICONS[EndpointSource.OTHER]}
								<div class="flex gap-2.5 rounded-md border p-2.5">
									<span
										class="flex size-7 shrink-0 items-center justify-center rounded-md border {PASSIVE_SOURCES.has(
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
						<section class="flex flex-col gap-2">
							<SectionHead icon={Variable} title="Parameters" />
							<div class="flex flex-wrap gap-1.5">
								{#each endpoint.params as name (name)}
									<button
										type="button"
										class="rounded-md bg-muted px-1.5 py-0.5 font-mono text-xs hover:bg-muted/70"
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
								<div class="flex flex-col gap-1 rounded-md border p-2">
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

					<section class="flex flex-col gap-2">
						<SectionHead icon={ArrowDownLeft} title="Response" />
						{#if !endpoint.is_probed}
							<p class="text-xs text-muted-foreground">Not requested.</p>
						{:else}
							<dl class="flex flex-col divide-y divide-border/60">
								{#each [['Status', endpoint.status_code], ['Content type', endpoint.content_type], ['Size', formatBytes(endpoint.content_length)], ['Words', endpoint.words?.toLocaleString()], ['Lines', endpoint.lines?.toLocaleString()], ['Response time', endpoint.response_time ? formatResponseTime(endpoint.response_time) : null]] as [label, value] (label)}
									{#if value !== null && value !== undefined}
										<div class={SHEET_ROW}>
											<dt class={SHEET_DT}>{label}</dt>
											<dd class="text-sm tabular-nums">{value}</dd>
										</div>
									{/if}
								{/each}
								{#if endpoint.title}
									<div class={SHEET_ROW}>
										<dt class={SHEET_DT}>Title</dt>
										<dd class="text-sm break-words">{endpoint.title}</dd>
									</div>
								{/if}
								{#if endpoint.redirect_location}
									<div class={SHEET_ROW}>
										<dt class={SHEET_DT}>Redirects to</dt>
										<dd class="font-mono text-xs break-all">{endpoint.redirect_location}</dd>
									</div>
								{/if}
								{#if endpoint.tech.length}
									<div class={SHEET_ROW}>
										<dt class={SHEET_DT}>Technologies</dt>
										<dd class="flex flex-wrap items-center gap-1.5">
											{#each endpoint.tech as name (name)}
												<button
													type="button"
													class="flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs hover:bg-muted/50"
													onclick={() => onFilter?.(filterToken('tech', name))}
												>
													<TechIcon {name} class="size-3.5" />
													{name}
												</button>
											{/each}
										</dd>
									</div>
								{/if}
							</dl>
						{/if}
					</section>
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>
