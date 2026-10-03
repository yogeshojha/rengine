<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Server from '@lucide/svelte/icons/server';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Badge } from '$lib/components/ui/badge';
	import Hint from '$lib/components/hint.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CopyButton from '$lib/components/copy-button.svelte';
	import ScreenshotThumb from './screenshot-thumb.svelte';
	import TechIcon from './tech-icon.svelte';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import { externalHref } from '$lib/utilities/links';
	import {
		FINDING_RELATION,
		FINDING_SUMMARY,
		FINDING_TITLE,
		frontedLabel,
		networkLabel,
		ORIGIN_EXPOSED,
		type OriginFinding,
		type OriginSample
	} from '$lib/utilities/origins';

	interface Props {
		finding: OriginFinding | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		onServices: (filter: string) => void;
		index?: number;
		total?: number;
		onStep?: (index: number) => void;
	}

	let {
		finding: f,
		open,
		onOpenChange,
		onServices,
		index = 0,
		total = 1,
		onStep
	}: Props = $props();

	let bypass = $derived(f?.kind === ORIGIN_EXPOSED);
	let cdn = $derived(f ? frontedLabel(f) : '');
	let sensitive = $derived(new Set(f?.sensitive_ports ?? []));
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
		{#if f}
			<Dialog.Header class="border-b px-6 py-4 pr-8">
				<div class="flex items-center gap-2">
					<Badge variant={f.confidence === 'high' ? 'warning' : 'outline'} class="font-normal">
						{f.confidence === 'high' ? 'High confidence' : 'Medium confidence'}
					</Badge>
					<Dialog.Title>
						{FINDING_TITLE[f.kind] ?? f.kind}
					</Dialog.Title>
				</div>
				<Dialog.Description class="max-w-prose">
					{FINDING_SUMMARY[f.kind] ?? ''}
				</Dialog.Description>
			</Dialog.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-6 px-6 py-5">
					<div class="grid grid-cols-1 items-start gap-5 sm:grid-cols-[1fr_auto_1fr]">
						{@render side(
							bypass ? `Behind ${cdn}` : 'By hostname',
							f.fronted[0],
							bypass
								? `${f.fronted_total} ${f.fronted_total === 1 ? 'hostname' : 'hostnames'}`
								: (f.fronted[0]?.host ?? ''),
							cdn
						)}
						<div class="flex flex-col items-center justify-center gap-2 self-center">
							<ArrowRight class="size-5 text-muted-foreground" />
							<span class="hidden text-2xs tracking-wide text-muted-foreground uppercase sm:block">
								{FINDING_RELATION[f.kind] ?? ''}
							</span>
						</div>
						{@render side(
							'Reachable directly',
							f.exposed,
							[f.exposed.ip, networkLabel(f.exposed)].filter(Boolean).join(' · '),
							null
						)}
					</div>

					<section class="flex flex-col gap-2">
						<SectionHead title="Evidence" />
						<dl class="flex flex-col divide-y divide-border/60 rounded-lg border">
							{#each f.evidence as e (e.kind)}
								<div
									class="grid grid-cols-[7rem_minmax(0,1fr)] items-baseline gap-3 px-3 py-2 sm:grid-cols-[10rem_minmax(0,1fr)]"
								>
									<dt class="text-xs text-muted-foreground">{e.label}</dt>
									<Hint text={e.value}>
										{#snippet child(props)}
											<dd
												{...props}
												class="min-w-0 truncate font-mono text-xs max-sm:whitespace-normal max-sm:wrap-anywhere"
											>
												{e.value}
											</dd>
										{/snippet}
									</Hint>
								</div>
							{/each}
						</dl>
					</section>

					{#if f.open_ports.length}
						<section class="flex flex-col gap-2">
							<SectionHead title="Open on {f.exposed.ip}" />
							<div class="flex flex-wrap items-center gap-1">
								{#each f.open_ports as p (p)}
									<Badge
										variant="outline"
										class="px-1.5 font-mono text-2xs font-normal {sensitive.has(p)
											? 'border-warning/40 text-warning'
											: ''}"
									>
										{p}
									</Badge>
								{/each}
								{#if f.sensitive_ports.length}
									<span class="ml-1 flex items-center gap-1 text-xs text-warning">
										<TriangleAlert class="size-3.5" />
										{f.sensitive_ports.length} administrative or datastore
									</span>
								{/if}
							</div>
						</section>
					{/if}

					{#if bypass && f.fronted.length > 1}
						<section class="flex flex-col gap-2">
							<SectionHead title="Hostnames serving the same application" />
							<ul class="flex flex-wrap gap-1">
								{#each f.fronted as s (s.url)}
									<li>
										<Badge variant="outline" class="font-mono text-2xs font-normal">
											{s.host}
										</Badge>
									</li>
								{/each}
								{#if f.fronted_total > f.fronted.length}
									<li class="self-center text-xs text-muted-foreground">
										+{(f.fronted_total - f.fronted.length).toLocaleString()} more
									</li>
								{/if}
							</ul>
						</section>
					{/if}
				</div>
			</ScrollArea>

			<div class="flex flex-wrap items-center gap-2 border-t px-6 py-4">
				<Button variant="outline" size="sm" class="gap-1.5" onclick={() => onServices(f.query)}>
					<Server class="size-4" /> Services on this address
				</Button>
				<Button
					variant="outline"
					size="sm"
					class="gap-1.5"
					href={externalHref(f.exposed.url)}
					target="_blank"
					rel="noopener noreferrer"
				>
					<ExternalLink class="size-4" /> Open address
				</Button>
				<CopyButton value={f.exposed.ip ?? ''} class="size-8" />
				{#if total > 1 && onStep}
					<div class="ml-auto flex items-center gap-1 text-xs text-muted-foreground tabular-nums">
						<Button
							variant="ghost"
							size="icon"
							class="size-7"
							disabled={index <= 0}
							aria-label="Previous finding"
							onclick={() => onStep(index - 1)}
						>
							<ChevronLeft class="size-4" />
						</Button>
						<span>{index + 1} of {total}</span>
						<Button
							variant="ghost"
							size="icon"
							class="size-7"
							disabled={index >= total - 1}
							aria-label="Next finding"
							onclick={() => onStep(index + 1)}
						>
							<ChevronRight class="size-4" />
						</Button>
					</div>
				{/if}
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>

{#snippet side(
	label: string,
	sample: OriginSample | undefined,
	caption: string,
	logo: string | null
)}
	<div class="flex min-w-0 flex-col gap-2">
		<span class="text-2xs tracking-wide text-muted-foreground uppercase">{label}</span>
		<ScreenshotThumb
			path={sample?.screenshot_path}
			alt={label}
			class="aspect-[4/3] w-full rounded-md border object-cover"
		/>
		<div class="flex min-w-0 flex-col gap-0.5">
			<span class="flex items-center gap-1.5">
				{#if sample?.status_code != null}
					<span class="font-mono text-xs tabular-nums {httpStatusTextClass(sample.status_code)}">
						{sample.status_code}
					</span>
				{/if}
				<span class="min-w-0 truncate text-xs">{sample?.title ?? sample?.host ?? '—'}</span>
			</span>
			<span class="flex min-w-0 items-center gap-1 text-xs text-muted-foreground">
				{#if logo}<TechIcon name={logo} class="size-3" />{/if}
				<span class="truncate">{caption}</span>
			</span>
			{#if sample?.webserver}
				<span class="truncate text-xs text-muted-foreground">{sample.webserver}</span>
			{/if}
		</div>
	</div>
{/snippet}
