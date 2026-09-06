<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Hint from '$lib/components/hint.svelte';
	import ChevronLeftIcon from '@lucide/svelte/icons/chevron-left';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import MaximizeIcon from '@lucide/svelte/icons/maximize';
	import MinusIcon from '@lucide/svelte/icons/minus';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import ScanIcon from '@lucide/svelte/icons/scan';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import PdfDocument from './pdf-document.svelte';
	import PdfRail from './pdf-rail.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { FORMAT_ICONS, FORMAT_LABELS, formatBytes } from '$lib/config/reports';
	import {
		loadDocument,
		pageSizes,
		readOutline,
		type OutlineEntry,
		type PageSize
	} from '$lib/utilities/pdf';
	import type { Report } from '$lib/types/report';
	import type { PDFDocumentProxy } from 'pdfjs-dist';

	const STEPS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];

	let {
		open = $bindable(false),
		report,
		projectId
	}: {
		open?: boolean;
		report: Report;
		projectId: string;
	} = $props();

	let doc = $state<PDFDocumentProxy | null>(null);
	let sizes = $state<PageSize[]>([]);
	let outline = $state<OutlineEntry[]>([]);
	let error = $state<string | null>(null);
	let loading = $state(false);
	let page = $state(1);
	let scale = $state(1);
	let fit = $state<'width' | 'page' | null>('width');
	let zoom = $state(1);
	let view = $state<ReturnType<typeof PdfDocument> | null>(null);
	let content = $state<HTMLElement | null>(null);
	let session = 0;

	const pdfFile = $derived(report.files.find((file) => file.format === 'pdf'));
	const otherFiles = $derived(report.files.filter((file) => file.format !== 'pdf'));

	$effect(() => {
		if (!open) return;
		const id = report.id;
		const mine = ++session;
		loading = true;
		error = null;

		void (async () => {
			try {
				const bytes = await reportsApi.pdf(projectId, id);
				const loaded = await loadDocument(bytes);
				if (mine !== session) {
					void loaded.destroy();
					return;
				}
				const [measured, contents] = await Promise.all([pageSizes(loaded), readOutline(loaded)]);
				if (mine !== session) {
					void loaded.destroy();
					return;
				}
				doc = loaded;
				sizes = measured;
				outline = contents;
				page = 1;
			} catch (err) {
				if (mine === session) error = err instanceof Error ? err.message : 'Preview failed.';
			} finally {
				if (mine === session) loading = false;
			}
		})();
	});

	$effect(() => {
		if (open) return;
		session++;
		const previous = doc;
		doc = null;
		sizes = [];
		outline = [];
		error = null;
		fit = 'width';
		page = 1;
		void previous?.destroy();
	});

	function zoomIn() {
		fit = null;
		zoom = STEPS.find((step) => step > scale + 0.01) ?? STEPS[STEPS.length - 1];
	}

	function zoomOut() {
		fit = null;
		zoom = [...STEPS].reverse().find((step) => step < scale - 0.01) ?? STEPS[0];
	}

	function step(delta: number) {
		const next = Math.min(Math.max(page + delta, 1), sizes.length);
		if (next !== page) view?.goTo(next);
	}

	function onkeydown(event: KeyboardEvent) {
		const target = event.target as HTMLElement | null;
		if (target?.closest('input, textarea')) return;
		if (event.key === 'ArrowRight' || event.key === 'PageDown') step(1);
		else if (event.key === 'ArrowLeft' || event.key === 'PageUp') step(-1);
		else if (event.key === '+' || event.key === '=') zoomIn();
		else if (event.key === '-') zoomOut();
		else if (event.key === 'Home') view?.goTo(1);
		else if (event.key === 'End') view?.goTo(sizes.length);
		else return;
		event.preventDefault();
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content
		bind:ref={content}
		class="flex h-[92vh] w-[min(78rem,96vw)] max-w-none flex-col gap-0 overflow-hidden p-0 sm:max-w-none"
		onOpenAutoFocus={(event) => {
			event.preventDefault();
			content?.focus();
		}}
		{onkeydown}
	>
		<Dialog.Header class="flex-row items-center gap-3 space-y-0 border-b px-4 py-3 pr-12">
			<div class="min-w-0 flex-1 space-y-0.5">
				<Dialog.Title class="truncate text-sm font-medium">{report.title}</Dialog.Title>
				<Dialog.Description class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
					<Badge variant="outline" class="font-mono text-[10px]">{report.subject}</Badge>
					<span>{report.template_name}</span>
					{#if sizes.length}<span>{sizes.length} pages</span>{/if}
					{#if pdfFile}<span>{formatBytes(pdfFile.bytes)}</span>{/if}
				</Dialog.Description>
			</div>
			<div class="flex shrink-0 items-center gap-1.5">
				<Hint text="Open in a new tab">
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-8"
							href={reportsApi.previewUrl(projectId, report.id)}
							target="_blank"
							rel="noreferrer"
							aria-label="Open in a new tab"
						>
							<ExternalLinkIcon class="size-4" />
						</Button>
					{/snippet}
				</Hint>
				<Button
					variant="outline"
					size="sm"
					class="h-8"
					href={reportsApi.downloadUrl(projectId, report.id, 'pdf')}
					download
				>
					<DownloadIcon class="mr-1.5 size-3.5" />
					PDF
				</Button>
				{#if otherFiles.length}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class="size-8"
									aria-label="Other formats"
								>
									<ChevronRightIcon class="size-4 rotate-90" />
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end" class="w-52">
							{#each otherFiles as file (file.format)}
								{@const Icon = FORMAT_ICONS[file.format]}
								<DropdownMenu.Item>
									{#snippet child({ props })}
										<a
											{...props}
											href={reportsApi.downloadUrl(projectId, report.id, file.format)}
											download
										>
											<Icon class="size-4" />
											Download {FORMAT_LABELS[file.format]}
											<span class="text-muted-foreground ml-auto text-xs">
												{formatBytes(file.bytes)}
											</span>
										</a>
									{/snippet}
								</DropdownMenu.Item>
							{/each}
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				{/if}
			</div>
		</Dialog.Header>

		<div class="bg-muted/40 flex min-h-0 flex-1">
			{#if doc && sizes.length}
				<PdfRail {doc} {sizes} {outline} {page} onPick={(number) => view?.goTo(number)} />
				<PdfDocument bind:this={view} {doc} {sizes} {fit} {zoom} bind:page bind:scale />
			{:else}
				<div class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
					{#if error}
						<TriangleAlertIcon class="text-destructive size-6" />
						<p class="text-sm">{error}</p>
						<Button
							variant="outline"
							size="sm"
							href={reportsApi.downloadUrl(projectId, report.id, 'pdf')}
							download
						>
							<DownloadIcon class="mr-1.5 size-3.5" />
							Download instead
						</Button>
					{:else if loading}
						<Spinner class="size-5" />
						<p class="text-muted-foreground text-sm">Opening the report</p>
					{/if}
				</div>
			{/if}
		</div>

		<div class="flex h-11 shrink-0 items-center gap-1 border-t px-3">
			<Button
				variant="ghost"
				size="icon"
				class="size-8"
				disabled={page <= 1}
				onclick={() => step(-1)}
				aria-label="Previous page"
			>
				<ChevronLeftIcon class="size-4" />
			</Button>
			<span class="text-muted-foreground min-w-28 text-center text-xs tabular-nums">
				{#if sizes.length}Page {page} of {sizes.length}{/if}
			</span>
			<Button
				variant="ghost"
				size="icon"
				class="size-8"
				disabled={page >= sizes.length}
				onclick={() => step(1)}
				aria-label="Next page"
			>
				<ChevronRightIcon class="size-4" />
			</Button>

			<div class="flex-1"></div>

			<Button
				variant="ghost"
				size="icon"
				class="size-8"
				disabled={!doc}
				onclick={zoomOut}
				aria-label="Zoom out"
			>
				<MinusIcon class="size-4" />
			</Button>
			<span class="text-muted-foreground min-w-12 text-center text-xs tabular-nums">
				{#if doc}{Math.round(scale * 100)}%{/if}
			</span>
			<Button
				variant="ghost"
				size="icon"
				class="size-8"
				disabled={!doc}
				onclick={zoomIn}
				aria-label="Zoom in"
			>
				<PlusIcon class="size-4" />
			</Button>
			<Separator orientation="vertical" class="mx-1 !h-5" />
			<Hint text={fit === 'width' ? 'Fit the whole page' : 'Fit the page width'}>
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-8"
						disabled={!doc}
						onclick={() => (fit = fit === 'width' ? 'page' : 'width')}
						aria-label={fit === 'width' ? 'Fit the whole page' : 'Fit the page width'}
					>
						{#if fit === 'width'}
							<ScanIcon class="size-4" />
						{:else}
							<MaximizeIcon class="size-4" />
						{/if}
					</Button>
				{/snippet}
			</Hint>
		</div>
	</Dialog.Content>
</Dialog.Root>
