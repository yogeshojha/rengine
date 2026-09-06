<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ThemePreview from './theme-preview.svelte';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import CheckIcon from '@lucide/svelte/icons/check';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { reports as reportsStore } from '$lib/stores/reports.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { scansApi } from '$lib/api/scans';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { FORMAT_LABELS, ReportFormat } from '$lib/config/reports';
	import { ROUTES } from '$lib/config/routes';
	import { formatShortDate } from '$lib/utilities/dates';
	import { cn } from '$lib/utils.js';
	import type { ScanRead } from '$lib/types/scan';
	import type { Target } from '$lib/types/target';
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
	let subjectKind = $state<'scan' | 'target'>('scan');
	let pickedScan = $state('');
	let pickedTarget = $state('');
	let scanOptions = $state<ScanRead[]>([]);
	let targetOptions = $state<Target[]>([]);
	let loadingSubjects = $state(false);

	const fixed = $derived(Boolean(scanId || targetId));
	const activeScan = $derived(scanId ?? (subjectKind === 'scan' ? pickedScan || null : null));
	const activeTarget = $derived(
		targetId ?? (subjectKind === 'target' ? pickedTarget || null : null)
	);
	const hasSubject = $derived(Boolean(activeScan || activeTarget));
	const targetName = $derived(
		(id: string) => targetOptions.find((t) => t.id === id)?.target_value ?? 'target'
	);

	const templates = $derived(reportsStore.templates);
	const selected = $derived<ReportTemplate | undefined>(templates.find((t) => t.id === templateId));
	const aiAvailable = $derived(reportCatalog.aiAvailable);
	const preview = $derived(reportCatalog.themes.find((t) => t.slug === theme));
	const sectionCount = $derived(selected?.sections.filter((s) => s.enabled).length ?? 0);

	$effect(() => {
		if (!open) return;
		void reportCatalog.fetch();
		void reportsStore.fetchTemplates(projectId);
	});

	$effect(() => {
		if (!open || fixed || !projectId || scanOptions.length || loadingSubjects) return;
		loadingSubjects = true;
		const slug = projectsStore.activeProject?.slug;
		Promise.all([
			scansApi.list(projectId, { size: 50, sort_by: 'started', sort_dir: 'desc' }),
			slug ? targetsApi.list({ project_slug: slug, size: 100 }) : Promise.resolve(null)
		])
			.then(([scans, targets]) => {
				scanOptions = scans.items;
				targetOptions = targets?.items ?? [];
				if (!pickedScan && scans.items.length) pickedScan = scans.items[0].id;
			})
			.catch(() => undefined)
			.finally(() => (loadingSubjects = false));
	});

	$effect(() => {
		if (!open || templateId || !templates.length) return;
		templateId = (templates.find((t) => t.is_default) ?? templates[0]).id;
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
		scan_id: activeScan,
		target_id: activeScan ? null : activeTarget,
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

	const signature = $derived(
		JSON.stringify({ templateId, useAi, explainFindings, activeScan, activeTarget })
	);

	$effect(() => {
		void signature;
		if (!open || !templateId || !hasSubject) return;
		estimating = true;
		reportsApi
			.estimate(projectId, body)
			.then((result) => (estimate = result))
			.catch(() => (estimate = null))
			.finally(() => (estimating = false));
	});

	async function start() {
		if (!hasSubject) return toast.error('Choose a scan or a target to report on.');
		if (!templateId) return toast.error('Choose a report template.');
		if (!formats.length) return toast.error('Choose at least one output format.');
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
	<Dialog.Content class="flex max-h-[92vh] flex-col gap-0 p-0 sm:max-w-4xl">
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

		<div class="grid min-h-0 flex-1 md:grid-cols-[1fr_17rem]">
			<ScrollArea class="min-h-0 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(92vh-13rem)]">
				<div class="space-y-5 px-6 py-5">
					{#if !fixed}
						<div class="space-y-1.5">
							<Label class="text-xs">Report on</Label>
							<div class="flex gap-2">
								<ToggleGroup.Root
									type="single"
									variant="outline"
									size="sm"
									value={subjectKind}
									onValueChange={(v) => v && (subjectKind = v as 'scan' | 'target')}
								>
									<ToggleGroup.Item value="scan" class="px-3">One scan</ToggleGroup.Item>
									<ToggleGroup.Item value="target" class="px-3">A target</ToggleGroup.Item>
								</ToggleGroup.Root>
								{#if subjectKind === 'scan'}
									<Select.Root type="single" bind:value={pickedScan}>
										<Select.Trigger class="min-w-0 flex-1">
											{#if pickedScan}
												{@const s = scanOptions.find((o) => o.id === pickedScan)}
												{s
													? `${targetName(s.target_id)} · ${formatShortDate(s.created_at)}`
													: 'Choose a scan'}
											{:else}
												Choose a scan
											{/if}
										</Select.Trigger>
										<Select.Content class="max-h-72">
											{#each scanOptions as option (option.id)}
												<Select.Item
													value={option.id}
													label={`${targetName(option.target_id)} · ${formatShortDate(option.created_at)}`}
												>
													<span class="truncate">{targetName(option.target_id)}</span>
													<span class="ml-auto shrink-0 pl-3 text-xs text-muted-foreground">
														{formatShortDate(option.created_at)}
													</span>
												</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
								{:else}
									<Select.Root type="single" bind:value={pickedTarget}>
										<Select.Trigger class="min-w-0 flex-1">
											{pickedTarget ? targetName(pickedTarget) : 'Choose a target'}
										</Select.Trigger>
										<Select.Content class="max-h-72">
											{#each targetOptions as option (option.id)}
												<Select.Item value={option.id} label={option.target_value}>
													{option.target_value}
												</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
								{/if}
							</div>
							<p class="text-xs text-muted-foreground">
								{subjectKind === 'scan'
									? 'Everything that one run observed, as it observed it.'
									: 'The current surface, from the most recent run that covered each dimension.'}
							</p>
						</div>
					{/if}

					<div class="space-y-1.5">
						<Label class="text-xs" for="report-template">Template</Label>
						<Select.Root type="single" bind:value={templateId}>
							<Select.Trigger id="report-template" class="w-full">
								{selected?.name ?? 'Choose a template'}
							</Select.Trigger>
							<Select.Content class="max-h-72">
								{#each templates as template (template.id)}
									<Select.Item value={template.id} label={template.name}>
										<span class="truncate">{template.name}</span>
										<span class="ml-auto shrink-0 pl-3 text-xs text-muted-foreground">
											{template.sections.filter((s) => s.enabled).length} sections
										</span>
									</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
						{#if selected?.description}
							<p class="text-xs text-muted-foreground">{selected.description}</p>
						{/if}
					</div>

					<div class="space-y-1.5">
						<Label class="text-xs" for="report-title">Title</Label>
						<Input id="report-title" bind:value={title} class="h-9" />
					</div>

					<div class="space-y-2">
						<Label class="text-xs">Theme</Label>
						<div class="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
							{#each reportCatalog.themes as option (option.slug)}
								<button
									type="button"
									class={cn(
										'w-[4.75rem] shrink-0 rounded-md p-1 text-left transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
										theme === option.slug ? 'bg-muted' : 'hover:bg-muted/60'
									)}
									aria-pressed={theme === option.slug}
									onclick={() => (theme = option.slug)}
								>
									<ThemePreview
										theme={option}
										variant="cover"
										class={cn(
											theme === option.slug
												? 'ring-2 ring-primary ring-offset-1 ring-offset-background'
												: ''
										)}
									/>
									<span class="mt-1.5 block truncate text-[11px] leading-tight">{option.name}</span>
								</button>
							{/each}
						</div>
					</div>

					<div class="space-y-2">
						<Label class="text-xs">Formats</Label>
						<ToggleGroup.Root
							type="multiple"
							variant="outline"
							size="sm"
							value={formats}
							onValueChange={(v) => (formats = v.length ? v : formats)}
							class="justify-start"
						>
							{#each Object.entries(FORMAT_LABELS) as [value, label] (value)}
								<ToggleGroup.Item {value} aria-label={label} class="px-3">{label}</ToggleGroup.Item>
							{/each}
						</ToggleGroup.Root>
					</div>

					<div class="space-y-3 rounded-lg border p-3.5">
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
							<div class="flex items-start justify-between gap-4 border-t pt-3">
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
				</div>
			</ScrollArea>

			<aside class="hidden border-l bg-muted/25 md:block">
				<div class="space-y-4 px-5 py-5">
					{#if preview}
						<ThemePreview theme={preview} variant="cover" class="shadow-sm" />
						<div>
							<p class="text-sm font-medium">{preview.name}</p>
							<p class="mt-0.5 text-xs text-muted-foreground">{preview.description}</p>
						</div>
					{:else}
						<Skeleton class="aspect-[1/1.414] w-full" />
					{/if}

					<div class="space-y-1.5 border-t pt-4 text-xs">
						{#if estimate}
							{#each [['Sections', sectionCount], ['Findings', estimate.findings], ['Assets', estimate.assets], ['Pages, about', estimate.pages_estimated]] as [label, value] (label)}
								<div class="flex items-baseline justify-between gap-3">
									<span class="text-muted-foreground">{label}</span>
									<span class="font-medium tabular-nums">{value.toLocaleString()}</span>
								</div>
							{/each}
							{#if estimate.ai_calls}
								<div class="flex items-baseline justify-between gap-3">
									<span class="text-muted-foreground">Model calls</span>
									<span class="font-medium tabular-nums">
										{estimate.ai_calls}{#if estimate.ai_cost_usd}
											· ${estimate.ai_cost_usd.toFixed(2)}{/if}
									</span>
								</div>
							{/if}
						{:else if estimating}
							{#each [1, 2, 3, 4] as n (n)}<Skeleton class="h-4 w-full" />{/each}
						{/if}
					</div>

					{#if estimate?.warnings.length}
						<div class="space-y-1.5 border-t pt-4">
							{#each estimate.warnings as warning (warning)}
								<p class="flex items-start gap-1.5 text-xs text-warning">
									<TriangleAlertIcon class="mt-px size-3.5 shrink-0" />
									<span>{warning}</span>
								</p>
							{/each}
						</div>
					{/if}

					<p class="flex items-start gap-1.5 border-t pt-4 text-xs text-muted-foreground">
						<CheckIcon class="mt-px size-3.5 shrink-0 text-success" />
						<span>Generation runs in the background. You can leave this page.</span>
					</p>
				</div>
			</aside>
		</div>

		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
			<LoadingButton loading={busy} disabled={!hasSubject} onclick={start}>Generate</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
