<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { reports as reportsStore } from '$lib/stores/reports.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { FORMAT_LABELS, ReportFormat } from '$lib/config/reports';
	import { ROUTES } from '$lib/config/routes';
	import type { ReportCreate, ReportEstimate, ReportTemplate } from '$lib/types/report';

	let {
		open = $bindable(false),
		projectId,
		scanId = null,
		targetId = null,
		subject = ''
	}: {
		open?: boolean;
		projectId: string;
		scanId?: string | null;
		targetId?: string | null;
		subject?: string;
	} = $props();

	let templateId = $state('');
	let title = $state('');
	let theme = $state('');
	let formats = $state<string[]>([ReportFormat.PDF]);
	let useAi = $state(false);
	let explainFindings = $state(false);
	let busy = $state(false);
	let estimate = $state<ReportEstimate | null>(null);
	let estimating = $state(false);

	const templates = $derived(reportsStore.templates);
	const selected = $derived<ReportTemplate | undefined>(templates.find((t) => t.id === templateId));
	const aiAvailable = $derived(reportCatalog.aiAvailable);

	$effect(() => {
		if (!open) return;
		void reportCatalog.fetch();
		void reportsStore.fetchTemplates(projectId);
	});

	$effect(() => {
		if (!open || templateId || !templates.length) return;
		const preferred = templates.find((t) => t.is_default) ?? templates[0];
		templateId = preferred.id;
	});

	$effect(() => {
		const template = selected;
		if (!template) return;
		title = template.title || template.name;
		theme = template.theme;
		formats = template.formats.length ? [...template.formats] : [ReportFormat.PDF];
	});

	const body = $derived<ReportCreate>({
		template_id: templateId || null,
		scan_id: scanId,
		target_id: scanId ? null : targetId,
		title,
		theme: theme || undefined,
		formats,
		narrative: selected
			? {
					...selected.narrative,
					ai_enabled: useAi && aiAvailable,
					explain_findings: explainFindings && useAi && aiAvailable
				}
			: undefined
	});

	let signature = $derived(JSON.stringify({ templateId, useAi, explainFindings }));

	$effect(() => {
		void signature;
		if (!open || !templateId) return;
		estimating = true;
		reportsApi
			.estimate(projectId, body)
			.then((result) => (estimate = result))
			.catch(() => (estimate = null))
			.finally(() => (estimating = false));
	});

	function toggleFormat(value: string, on: boolean) {
		formats = on ? [...new Set([...formats, value])] : formats.filter((f) => f !== value);
	}

	async function start() {
		if (!templateId) {
			toast.error('Choose a report template.');
			return;
		}
		if (!formats.length) {
			toast.error('Choose at least one output format.');
			return;
		}
		busy = true;
		const report = await reportsStore.create(projectId, body);
		busy = false;
		if (!report) return;
		open = false;
		toast.success('The report is generating. It will appear in Reports when it is ready.');
		void goto(ROUTES.reports());
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="flex max-h-[92vh] flex-col gap-0 p-0 sm:max-w-2xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title class="flex items-center gap-2">
				<FileTextIcon class="size-4" />
				Generate report
			</Dialog.Title>
			<Dialog.Description>
				{subject
					? `Everything this run observed about ${subject}.`
					: 'Choose what the document says and how it looks.'}
			</Dialog.Description>
		</Dialog.Header>

		<ScrollArea
			class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(92vh-14rem)]"
		>
			<div class="space-y-5 px-6 py-5">
				<div class="space-y-1.5">
					<Label class="text-xs">Template</Label>
					<Select.Root type="single" bind:value={templateId}>
						<Select.Trigger class="w-full">
							{selected?.name ?? 'Choose a template'}
						</Select.Trigger>
						<Select.Content>
							{#each templates as template (template.id)}
								<Select.Item value={template.id}>
									<span class="flex flex-col items-start gap-0.5">
										<span>{template.name}</span>
										<span class="text-xs text-muted-foreground">{template.description}</span>
									</span>
								</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					{#if selected}
						<p class="text-xs text-muted-foreground">
							{selected.sections.filter((s) => s.enabled).length} sections
						</p>
					{/if}
				</div>

				<div class="space-y-1.5">
					<Label class="text-xs" for="report-title">Title</Label>
					<Input id="report-title" bind:value={title} class="h-9" />
				</div>

				<div class="space-y-1.5">
					<Label class="text-xs">Theme</Label>
					<div class="flex flex-wrap gap-2">
						{#each reportCatalog.themes as option (option.slug)}
							<button
								type="button"
								class="flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
								data-active={theme === option.slug}
								onclick={() => (theme = option.slug)}
							>
								<span class="size-3.5 rounded-full border" style="background:{option.accent}"
								></span>
								{option.name}
							</button>
						{/each}
					</div>
				</div>

				<div class="space-y-1.5">
					<Label class="text-xs">Formats</Label>
					<div class="flex flex-wrap gap-2">
						{#each Object.entries(FORMAT_LABELS) as [value, label] (value)}
							<button
								type="button"
								class="rounded-md border px-2.5 py-1.5 text-xs transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
								data-active={formats.includes(value)}
								onclick={() => toggleFormat(value, !formats.includes(value))}
							>
								{label}
							</button>
						{/each}
					</div>
				</div>

				<Separator />

				<div class="space-y-3">
					<div class="flex items-start justify-between gap-4">
						<div class="space-y-0.5">
							<Label class="flex items-center gap-1.5 text-sm font-medium">
								<SparklesIcon class="size-3.5" />
								Write the narrative with AI
							</Label>
							<p class="text-xs text-muted-foreground">
								{aiAvailable
									? 'The model sees a summary of the findings, never the raw rows.'
									: 'Connect a provider on the AI page to enable this.'}
							</p>
						</div>
						<Hint text={aiAvailable ? '' : 'AI is not configured on this instance.'}>
							{#snippet child(props)}
								<span class="inline-flex" {...props}>
									<Switch
										checked={useAi}
										disabled={!aiAvailable}
										onCheckedChange={(v) => (useAi = v)}
									/>
								</span>
							{/snippet}
						</Hint>
					</div>

					{#if useAi && aiAvailable}
						<div class="flex items-start justify-between gap-4 pl-1">
							<div class="space-y-0.5">
								<Label class="text-sm">Explain each finding</Label>
								<p class="text-xs text-muted-foreground">
									One short paragraph per weakness. Written once per check, then reused.
								</p>
							</div>
							<Switch checked={explainFindings} onCheckedChange={(v) => (explainFindings = v)} />
						</div>
					{/if}
				</div>

				{#if estimate}
					<div class="rounded-md border bg-muted/40 px-3 py-2.5 text-xs">
						<div class="flex flex-wrap gap-x-5 gap-y-1 text-muted-foreground">
							<span
								><span class="font-medium text-foreground">{estimate.sections}</span> sections</span
							>
							<span
								><span class="font-medium text-foreground"
									>{estimate.findings.toLocaleString()}</span
								> findings</span
							>
							<span
								><span class="font-medium text-foreground">{estimate.assets.toLocaleString()}</span> assets</span
							>
							<span
								>about <span class="font-medium text-foreground">{estimate.pages_estimated}</span> pages</span
							>
							{#if estimate.ai_calls}
								<span>
									<span class="font-medium text-foreground">{estimate.ai_calls}</span> model calls
									{#if estimate.ai_cost_usd}
										· about <span class="font-medium text-foreground"
											>${estimate.ai_cost_usd.toFixed(2)}</span
										>
									{/if}
								</span>
							{/if}
						</div>
						{#each estimate.warnings as warning (warning)}
							<p class="mt-1.5 text-warning">{warning}</p>
						{/each}
					</div>
				{:else if estimating}
					<p class="text-xs text-muted-foreground">Working out what this will contain…</p>
				{/if}
			</div>
		</ScrollArea>

		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
			<LoadingButton loading={busy} onclick={start}>Generate</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
