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
	import { Separator } from '$lib/components/ui/separator/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ThemePreview from './theme-preview.svelte';
	import SectionPill from './generate/section-pill.svelte';
	import SectionConfigPopover from './generate/section-config-popover.svelte';
	import SectionField from './builder/section-field.svelte';
	import { ReportPlan } from './generate/report-plan.svelte';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import RotateCcwIcon from '@lucide/svelte/icons/rotate-ccw';
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
	import { SELECT_NONE } from '$lib/constants';
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

	const plan = new ReportPlan();

	let templateId = $state('');
	let title = $state('');
	let theme = $state('');
	let formats = $state<string[]>([ReportFormat.PDF]);
	let useAi = $state(false);
	let explainFindings = $state(false);
	let busy = $state(false);
	let estimate = $state<ReportEstimate | null>(null);
	let baseEstimate = $state<ReportEstimate | null>(null);
	let estimating = $state(false);
	let seededFor = $state('');
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
	const usingTemplate = $derived(templateId && templateId !== SELECT_NONE ? templateId : '');
	const selected = $derived<ReportTemplate | undefined>(
		templates.find((t) => t.id === usingTemplate)
	);
	const aiAvailable = $derived(reportCatalog.aiAvailable);
	const preview = $derived(reportCatalog.themes.find((t) => t.slug === theme));
	const groups = $derived(reportCatalog.catalog?.groups ?? []);
	const promoted = $derived(
		plan.content.filter((s) => plan.enabled(s.name) && plan.launchFields(s.name).length)
	);

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

	// the template seeds the contents once; from then on the plan belongs to this report
	$effect(() => {
		const sections = reportCatalog.catalog?.sections;
		if (!open || !sections?.length) return;
		const key = `${templateId}:${sections.length}`;
		if (seededFor === key) return;
		seededFor = key;
		plan.seed(sections, selected);
		title = selected?.title || selected?.name || 'Security Assessment Report';
		if (selected?.theme) theme = selected.theme;
		formats = selected?.formats?.length ? [...selected.formats] : [ReportFormat.PDF];
		baseEstimate = null;
	});

	const body = $derived<ReportCreate>({
		template_id: usingTemplate || null,
		scan_id: activeScan,
		target_id: activeScan ? null : activeTarget,
		title,
		theme: theme || undefined,
		sections: plan.entries,
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
		JSON.stringify({ activeScan, activeTarget, useAi, explainFindings, entries: plan.entries })
	);

	$effect(() => {
		void signature;
		if (!open || !hasSubject) return;
		estimating = true;
		reportsApi
			.estimate(projectId, body)
			.then((result) => {
				estimate = result;
				if (!plan.changed) baseEstimate = result;
			})
			.catch(() => (estimate = null))
			.finally(() => (estimating = false));
	});

	const STATS: [string, 'sections' | 'findings' | 'assets' | 'pages_estimated'][] = [
		['Sections', 'sections'],
		['Findings', 'findings'],
		['Assets', 'assets'],
		['Estimated pages', 'pages_estimated']
	];

	function before(key: 'sections' | 'findings' | 'assets' | 'pages_estimated') {
		if (!baseEstimate || !estimate || baseEstimate[key] === estimate[key]) return null;
		return baseEstimate[key];
	}

	async function start() {
		if (!hasSubject) return toast.error('Select a scan or a target to report on.');
		if (!plan.enabledCount) return toast.error('Select at least one section.');
		if (!formats.length) return toast.error('Select at least one output format.');
		busy = true;
		const report = await reportsStore.create(projectId, body);
		busy = false;
		if (!report) return;
		open = false;
		toast.success('Report queued. It appears in Reports when generation completes.');
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
					: 'Select the subject, the contents and the output.'}
			</Dialog.Description>
		</Dialog.Header>

		<div class="grid min-h-0 flex-1 md:grid-cols-[1fr_16rem]">
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
												{@const picked = scanOptions.find((o) => o.id === pickedScan)}
												{picked
													? `${targetName(picked.target_id)} · ${formatShortDate(picked.created_at)}`
													: 'Select a scan'}
											{:else}
												Select a scan
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
											{pickedTarget ? targetName(pickedTarget) : 'Select a target'}
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
						</div>
					{/if}

					<div class="space-y-1.5">
						<Label class="text-xs" for="report-template">Template</Label>
						<Select.Root type="single" bind:value={templateId}>
							<Select.Trigger id="report-template" class="w-full">
								{selected?.name ?? 'Standard sections'}
							</Select.Trigger>
							<Select.Content class="max-h-72">
								<Select.Item value={SELECT_NONE} label="Standard sections">
									<span>Standard sections</span>
									<span class="ml-auto shrink-0 pl-3 text-xs text-muted-foreground"
										>no template</span
									>
								</Select.Item>
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
						<p class="text-xs text-muted-foreground">
							The template supplies the starting contents. Changes below apply to this report only
							and do not modify the template.
						</p>
					</div>

					<div class="space-y-1.5">
						<Label class="text-xs" for="report-title">Title</Label>
						<Input id="report-title" bind:value={title} class="h-9" />
					</div>

					<div class="space-y-3">
						<div class="flex flex-wrap items-baseline justify-between gap-x-3 border-b pb-1.5">
							<span class="text-sm font-medium">Contents</span>
							<span class="text-xs text-muted-foreground">
								{plan.enabledCount} sections{#if plan.furniture.length}
									&nbsp;· cover, contents and reference sections are included automatically{/if}
							</span>
						</div>

						{#each groups as group (group.key)}
							{@const inGroup = plan.content.filter((s) => s.group === group.key)}
							{#if inGroup.length}
								<div class="space-y-1.5">
									<p class="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
										{group.label}
									</p>
									<div class="flex flex-wrap gap-1.5">
										{#each inGroup as section (section.name)}
											<SectionPill
												{section}
												on={plan.enabled(section.name)}
												onToggle={() => plan.toggle(section.name)}
											>
												{#if section.fields.length}
													<SectionConfigPopover {section} {plan} hideLaunchFields />
												{/if}
											</SectionPill>
										{/each}
									</div>
								</div>
							{/if}
						{/each}
					</div>

					{#each promoted as section (section.name)}
						{@const values = plan.config(section.name)}
						{@const changed = plan.changedFields(section.name)}
						<div class="rounded-lg border">
							<div class="flex items-center justify-between gap-3 border-b px-3.5 py-2.5">
								<span class="text-sm font-medium">{section.title}</span>
								{#if changed.length}
									<span class="flex items-center gap-1">
										<span
											class="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary"
										>
											This report only
										</span>
										<Button
											variant="ghost"
											size="sm"
											class="h-6 gap-1 px-1.5 text-xs text-muted-foreground"
											onclick={() => plan.resetSection(section.name)}
										>
											<RotateCcwIcon class="size-3" /> Reset
										</Button>
									</span>
								{/if}
							</div>
							<div class="divide-y divide-border px-3.5">
								{#each plan.launchFields(section.name) as field (field.name)}
									<SectionField
										{field}
										value={values[field.name] ?? field.default}
										onChange={(value) => plan.setField(section.name, field.name, value)}
									/>
								{/each}
							</div>
						</div>
					{/each}

					<Separator />

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
										? 'The model receives a summary of the findings, never the underlying rows.'
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
										One paragraph per weakness, written once per check and reused.
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
							{#each STATS as [label, key] (key)}
								<div class="flex items-baseline justify-between gap-3">
									<span class="text-muted-foreground">{label}</span>
									<span class="tabular-nums">
										{#if before(key) !== null}
											<span class="mr-1.5 text-muted-foreground/70 line-through">
												{before(key)?.toLocaleString()}
											</span>
										{/if}
										<span class="font-medium">{estimate[key].toLocaleString()}</span>
									</span>
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
						{:else}
							<p class="text-muted-foreground">Select a subject to see what this will contain.</p>
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
				</div>
			</aside>
		</div>

		<Dialog.Footer class="justify-between border-t px-6 py-4 sm:justify-between">
			<Button
				variant="ghost"
				class="text-muted-foreground"
				disabled={!plan.changed}
				onclick={() => plan.reset()}
			>
				Reset to template
			</Button>
			<div class="flex gap-2">
				<Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
				<LoadingButton loading={busy} disabled={!hasSubject} onclick={start}>Generate</LoadingButton
				>
			</div>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
