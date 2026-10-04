<script lang="ts">
	import { untrack } from 'svelte';
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
	import FormField from '$lib/components/form-field.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import ThemePreview from './theme-preview.svelte';
	import SectionPill from './generate/section-pill.svelte';
	import SectionConfigPopover from './generate/section-config-popover.svelte';
	import SectionField from './builder/section-field.svelte';
	import { ReportPlan } from './generate/report-plan.svelte';
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
		subject = '',
		template = ''
	}: {
		open?: boolean;
		projectId: string;
		scanId?: string | null;
		targetId?: string | null;
		subject?: string;
		template?: string;
	} = $props();

	const plan = new ReportPlan();
	const uid = $props.id();

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
	let estimateError = $state<string | null>(null);
	let seededFor = $state('');
	let seed = $state({ title: '', theme: '', formats: '', useAi: false, explainFindings: false });
	let subjectKind = $state<'scan' | 'target'>('scan');
	let pickedScan = $state('');
	let pickedTarget = $state('');
	let scanOptions = $state<ScanRead[]>([]);
	let targetOptions = $state<Target[]>([]);
	let subjectsFor = '';

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
	const templatesFailed = $derived(Boolean(reportsStore.templatesError) && !templates.length);
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
		const id = projectId;
		untrack(() => {
			void reportCatalog.fetch();
			void reportsStore.fetchTemplates(id);
		});
	});

	$effect(() => {
		if (!open) {
			subjectsFor = '';
			return;
		}
		const slug = projectsStore.activeProject?.slug ?? '';
		const key = `${projectId}:${slug}`;
		if (fixed || !projectId || subjectsFor === key) return;
		subjectsFor = key;
		Promise.all([
			scansApi.list(projectId, { size: 50, sort_by: 'started', sort_dir: 'desc' }),
			slug ? targetsApi.list({ project_slug: slug, size: 100 }) : Promise.resolve(null)
		])
			.then(([scans, targets]) => {
				if (subjectsFor !== key) return;
				scanOptions = scans.items;
				targetOptions = targets?.items ?? [];
				if (!pickedScan && scans.items.length) pickedScan = scans.items[0].id;
			})
			.catch(() => {
				if (subjectsFor === key) subjectsFor = '';
			});
	});

	$effect(() => {
		if (!open || !templates.length) return;
		const wanted = template;
		untrack(() => {
			if (wanted) templateId = wanted;
			else if (!templateId) templateId = (templates.find((t) => t.is_default) ?? templates[0]).id;
		});
	});

	$effect(() => {
		const sections = reportCatalog.catalog?.sections;
		if (!open || !sections?.length) return;
		const key = `${templateId}:${sections.length}`;
		if (seededFor === key) return;
		seededFor = key;
		plan.seed(sections, selected);
		const next = {
			title: selected?.title || selected?.name || 'Security Assessment Report',
			theme: selected?.theme ?? '',
			formats: selected?.formats?.length ? [...selected.formats] : [ReportFormat.PDF],
			useAi: selected?.narrative.ai_enabled ?? false,
			explainFindings: selected?.narrative.explain_findings ?? false
		};
		title = next.title;
		theme = next.theme;
		formats = next.formats;
		useAi = next.useAi;
		explainFindings = next.explainFindings;
		seed = { ...next, formats: next.formats.join() };
		baseEstimate = null;
	});

	$effect(() => {
		if (!open) seededFor = '';
	});

	const dirty = $derived(
		Boolean(seededFor) &&
			(plan.changed ||
				title !== seed.title ||
				theme !== seed.theme ||
				formats.join() !== seed.formats ||
				useAi !== seed.useAi ||
				explainFindings !== seed.explainFindings)
	);

	const guard = new DiscardGuard(
		() => dirty,
		() => (open = false)
	);

	function requestOpen(next: boolean) {
		if (next) open = true;
		else if (!busy) guard.close();
	}

	const body = $derived<ReportCreate>({
		template_id: usingTemplate || null,
		scan_id: activeScan,
		target_id: activeScan ? null : activeTarget,
		title,
		theme: theme || undefined,
		sections: plan.entries,
		formats,
		narrative: {
			...(selected?.narrative ?? {}),
			ai_enabled: useAi && aiAvailable,
			explain_findings: explainFindings && useAi && aiAvailable
		}
	});

	const signature = $derived(
		JSON.stringify({
			activeScan,
			activeTarget,
			useAi,
			explainFindings,
			formats,
			entries: plan.entries
		})
	);

	let estimateSeq = 0;

	$effect(() => {
		void signature;
		if (!open || !hasSubject) return;
		const mine = ++estimateSeq;
		estimating = true;
		estimateError = null;
		reportsApi
			.estimate(
				projectId,
				untrack(() => body)
			)
			.then((result) => {
				if (mine !== estimateSeq) return;
				estimate = result;
				if (!plan.changed) baseEstimate = result;
			})
			.catch((e) => {
				if (mine !== estimateSeq) return;
				estimate = null;
				estimateError = e instanceof Error ? e.message : 'Request failed.';
			})
			.finally(() => {
				if (mine === estimateSeq) estimating = false;
			});
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

	const ready = $derived(hasSubject && plan.enabledContentCount > 0 && formats.length > 0);

	async function start() {
		if (!ready) return;
		busy = true;
		const report = await reportsStore.create(projectId, body);
		busy = false;
		if (!report) return;
		open = false;
		toast.success('Report queued');
		void goto(ROUTES.reports());
	}
</script>

{#snippet estimateBlock(divided: string)}
	<div class={cn('space-y-1.5 text-xs', divided)}>
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
		{:else if estimateError}
			<p class="flex items-start gap-1.5 text-destructive">
				<TriangleAlertIcon class="mt-px size-3.5 shrink-0" />
				<span>Estimate not loaded. {estimateError}</span>
			</p>
		{:else}
			<p class="text-muted-foreground">No subject. Select a scan or a target.</p>
		{/if}
	</div>

	{#if estimate?.warnings.length}
		<div class={cn('space-y-1.5', divided)}>
			{#each estimate.warnings as warning (warning)}
				<p class="flex items-start gap-1.5 text-xs text-warning">
					<TriangleAlertIcon class="mt-px size-3.5 shrink-0" />
					<span>{warning}</span>
				</p>
			{/each}
		</div>
	{/if}
{/snippet}

<Dialog.Root bind:open={() => open, requestOpen}>
	<Dialog.Content class="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-4xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title class="flex items-center gap-2">
				<FileTextIcon class="size-4" />
				Generate report
			</Dialog.Title>
			{#if subject}
				<Dialog.Description>Report on {subject}.</Dialog.Description>
			{/if}
		</Dialog.Header>

		<div class="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] md:grid-cols-[minmax(0,1fr)_16rem]">
			<ScrollArea class="min-h-0 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(90vh-13rem)]">
				<div class="flex flex-col gap-4 px-6 py-5">
					{#if !fixed}
						<FormField label="Report on">
							{#snippet children({ id })}
								<div class="flex gap-2">
									<ToggleGroup.Root
										type="single"
										variant="outline"
										size="lg"
										bind:value={
											() => subjectKind,
											(v) => {
												if (v) subjectKind = v as 'scan' | 'target';
											}
										}
									>
										<ToggleGroup.Item value="scan" class="px-3">Scan</ToggleGroup.Item>
										<ToggleGroup.Item value="target" class="px-3">Target</ToggleGroup.Item>
									</ToggleGroup.Root>
									{#if subjectKind === 'scan'}
										<Select.Root type="single" bind:value={pickedScan}>
											<Select.Trigger {id} class="min-w-0 flex-1">
												{#if pickedScan}
													{@const picked = scanOptions.find((o) => o.id === pickedScan)}
													{picked
														? `${picked.execution_config.target_value} · ${formatShortDate(picked.created_at)}`
														: 'Select a scan'}
												{:else}
													Select a scan
												{/if}
											</Select.Trigger>
											<Select.Content class="max-h-72">
												{#each scanOptions as option (option.id)}
													<Select.Item
														value={option.id}
														label={`${option.execution_config.target_value} · ${formatShortDate(option.created_at)}`}
													>
														<span class="truncate">{option.execution_config.target_value}</span>
														<span class="ml-auto shrink-0 pl-3 text-xs text-muted-foreground">
															{formatShortDate(option.created_at)}
														</span>
													</Select.Item>
												{/each}
											</Select.Content>
										</Select.Root>
									{:else}
										<Select.Root type="single" bind:value={pickedTarget}>
											<Select.Trigger {id} class="min-w-0 flex-1">
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
							{/snippet}
						</FormField>
					{/if}

					<FormField
						label="Template"
						description={templatesFailed ? undefined : 'Changes below apply to this report only.'}
					>
						{#snippet children({ id })}
							{#if templatesFailed}
								<div
									class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2"
								>
									<p class="flex min-w-0 items-start gap-1.5 text-sm text-destructive">
										<TriangleAlertIcon class="mt-0.5 size-3.5 shrink-0" />
										<span>Templates not loaded. {reportsStore.templatesError}</span>
									</p>
									<LoadingButton
										variant="outline"
										size="sm"
										loading={reportsStore.templatesLoading}
										loadingLabel="Retrying"
										onclick={() => reportsStore.fetchTemplates(projectId, true)}
										>Retry</LoadingButton
									>
								</div>
							{:else}
								<Select.Root type="single" bind:value={templateId}>
									<Select.Trigger {id} class="w-full">
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
							{/if}
						{/snippet}
					</FormField>

					<FormField label="Title">
						{#snippet children({ id })}
							<Input {id} bind:value={title} class="h-9" />
						{/snippet}
					</FormField>

					<div class="space-y-3">
						<div class="flex flex-wrap items-baseline justify-between gap-x-3 border-b pb-1.5">
							<span class="text-sm font-medium">Contents</span>
							<span class="text-xs text-muted-foreground">
								{plan.enabledContentCount}
								{plan.enabledContentCount === 1 ? 'section' : 'sections'}{#if plan.furniture.length}
									&nbsp;· cover, contents and reference sections included{/if}
							</span>
						</div>

						{#each groups as group (group.key)}
							{@const inGroup = plan.content.filter((s) => s.group === group.key)}
							{#if inGroup.length}
								<div class="space-y-1.5">
									<p class="text-2xs tracking-wide text-muted-foreground uppercase">
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
													<SectionConfigPopover {section} {plan} />
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
						<div class="overflow-hidden rounded-lg border">
							<div class="flex items-center justify-between gap-3 border-b bg-muted/25 px-4 py-2.5">
								<span class="text-sm font-medium">{section.title}</span>
								{#if changed.length}
									<span class="flex shrink-0 items-center gap-1">
										<span
											class="rounded-full bg-primary/10 px-2 py-0.5 text-2xs font-medium text-primary"
										>
											This report only
										</span>
										<Button
											variant="ghost"
											size="sm"
											class="h-6 px-1.5 text-xs text-muted-foreground"
											onclick={() => plan.resetSection(section.name)}
										>
											<RotateCcwIcon class="size-3" /> Reset
										</Button>
									</span>
								{/if}
							</div>
							<div class="divide-y divide-border px-4">
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

					<div class="space-y-3">
						<Label>Theme</Label>
						<ScrollArea orientation="horizontal" class="-mx-1" scrollbarXClasses="h-1.5">
							<div class="flex gap-2 px-1 pb-2">
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
										<span class="mt-1.5 block truncate text-2xs leading-tight">{option.name}</span>
									</button>
								{/each}
							</div>
						</ScrollArea>
					</div>

					<div class="space-y-3">
						<Label>Formats</Label>
						<ToggleGroup.Root
							type="multiple"
							variant="outline"
							size="sm"
							bind:value={
								() => formats,
								(v) => {
									if (Array.isArray(v) && v.length) formats = v;
								}
							}
							class="justify-start"
						>
							{#each Object.entries(FORMAT_LABELS) as [value, label] (value)}
								<ToggleGroup.Item {value} aria-label={label} class="px-3">{label}</ToggleGroup.Item>
							{/each}
						</ToggleGroup.Root>
					</div>

					<div class="space-y-3 rounded-lg border p-4">
						<div class="flex items-start justify-between gap-4">
							<div class="space-y-0.5">
								<Label for="{uid}-ai">Draft the narrative with AI</Label>
								<p class="text-xs text-muted-foreground">
									{aiAvailable
										? 'The model receives a summary of the findings.'
										: 'Connect a provider on the AI page.'}
								</p>
							</div>
							<Switch
								id="{uid}-ai"
								checked={useAi && aiAvailable}
								disabled={!aiAvailable}
								onCheckedChange={(v) => (useAi = v)}
							/>
						</div>

						{#if useAi && aiAvailable}
							<div class="flex items-start justify-between gap-4 border-t pt-3">
								<div class="space-y-0.5">
									<Label for="{uid}-explain">Explain each finding</Label>
									<p class="text-xs text-muted-foreground">
										One paragraph per check, written once and cached.
									</p>
								</div>
								<Switch
									id="{uid}-explain"
									checked={explainFindings}
									onCheckedChange={(v) => (explainFindings = v)}
								/>
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

					{@render estimateBlock('border-t pt-4')}
				</div>
			</aside>
		</div>

		<div class="space-y-3 border-t bg-muted/25 px-6 py-3 md:hidden">
			{@render estimateBlock('')}
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
				<Button variant="outline" disabled={busy} onclick={() => guard.close()}>Cancel</Button>
				<LoadingButton loading={busy} loadingLabel="Generating" disabled={!ready} onclick={start}
					>Generate</LoadingButton
				>
			</div>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
