<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { untrack } from 'svelte';
	import { page } from '$app/state';
	import { beforeNavigate, goto } from '$app/navigation';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';
	import PlayIcon from '@lucide/svelte/icons/play';
	import FileX from '@lucide/svelte/icons/file-x';
	import ListOrderedIcon from '@lucide/svelte/icons/list-ordered';
	import PaletteIcon from '@lucide/svelte/icons/palette';
	import StampIcon from '@lucide/svelte/icons/stamp';
	import PenLineIcon from '@lucide/svelte/icons/pen-line';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import SectionList from '$lib/components/reports/builder/section-list.svelte';
	import LookPanel from '$lib/components/reports/builder/look-panel.svelte';
	import BrandingPanel from '$lib/components/reports/builder/branding-panel.svelte';
	import NarrativePanel from '$lib/components/reports/builder/narrative-panel.svelte';
	import GenerateDialog from '$lib/components/reports/generate-dialog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { reports as reportsStore } from '$lib/stores/reports.svelte';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { FORMAT_LABELS } from '$lib/config/reports';
	import { ROUTES } from '$lib/config/routes';
	import { toast } from 'svelte-sonner';
	import type {
		NarrativeOptions,
		ReportBranding,
		ReportStyle,
		ReportTemplate,
		SectionEntry
	} from '$lib/types/report';

	const templateId = $derived(page.params.id ?? '');
	const projectId = $derived(projectsStore.activeProject?.id ?? '');
	const template = $derived<ReportTemplate | undefined>(
		reportsStore.templates.find((t) => t.id === templateId)
	);

	let name = $state('');
	let description = $state('');
	let title = $state('');
	let subtitle = $state('');
	let formats = $state<string[]>([]);
	let sections = $state<SectionEntry[]>([]);
	let style = $state<ReportStyle | null>(null);
	let branding = $state<ReportBranding | null>(null);
	let narrative = $state<NarrativeOptions | null>(null);
	let loadedId = $state('');
	let saving = $state(false);
	let duplicating = $state(false);
	let generateOpen = $state(false);
	let leaveTo = $state<string | null>(null);
	let allowNav = false;

	beforeNavigate((nav) => {
		if (allowNav) {
			allowNav = false;
			return;
		}
		if (!dirty || saving || !nav.to) return;
		nav.cancel();
		leaveTo = nav.to.url.pathname + nav.to.url.search;
	});

	$effect(() => {
		function onBeforeUnload(e: BeforeUnloadEvent) {
			if (!dirty || saving) return;
			e.preventDefault();
		}
		window.addEventListener('beforeunload', onBeforeUnload);
		return () => window.removeEventListener('beforeunload', onBeforeUnload);
	});

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => {
			void reportsStore.fetchTemplates(id);
			void reportCatalog.fetch();
		});
	});

	$effect(() => {
		const found = template;
		if (!found || loadedId === found.id) return;
		loadedId = found.id;
		name = found.name;
		description = found.description;
		title = found.title;
		subtitle = found.subtitle;
		formats = [...found.formats];
		sections = found.sections.map((s) => ({ ...s, config: { ...s.config } }));
		style = { ...found.style, theme: found.theme || found.style.theme };
		branding = {
			...found.branding,
			distribution: [...found.branding.distribution],
			revisions: found.branding.revisions.map((r) => ({ ...r }))
		};
		narrative = { ...found.narrative };
	});

	$effect(() => {
		const current = template;
		if (!current) return;
		breadcrumbStore.set(current.id, current.name);
		return () => breadcrumbStore.remove(current.id);
	});

	const dirty = $derived(
		Boolean(
			template &&
			style &&
			branding &&
			narrative &&
			JSON.stringify({
				name,
				description,
				title,
				subtitle,
				formats,
				sections,
				style,
				branding,
				narrative
			}) !==
				JSON.stringify({
					name: template.name,
					description: template.description,
					title: template.title,
					subtitle: template.subtitle,
					formats: template.formats,
					sections: template.sections,
					style: { ...template.style, theme: template.theme || template.style.theme },
					branding: template.branding,
					narrative: template.narrative
				})
		)
	);

	async function save() {
		if (!template || !style || !branding || !narrative || !formats.length) return;
		saving = true;
		const ok = await reportsStore.saveTemplate(projectId, template.id, {
			name,
			description,
			title,
			subtitle,
			sections,
			theme: style.theme,
			style,
			branding,
			narrative,
			formats
		});
		saving = false;
		if (ok) toast.success('Template saved');
	}

	async function saveAsCopy() {
		if (!template || !style || !branding || !narrative) return;
		duplicating = true;
		const created = await reportsStore.createTemplate(projectId, {
			name: `${name} copy`,
			description,
			title,
			subtitle,
			scope: template.scope,
			sections,
			theme: style.theme,
			style,
			branding,
			narrative,
			formats
		});
		duplicating = false;
		if (created) {
			toast.success(`Template ${created.name} created`);
			allowNav = true;
			void goto(ROUTES.reportTemplate(created.id));
		}
	}
</script>

<svelte:head><title>{pageTitle(name || 'Report template')}</title></svelte:head>

{#if !template && projectId && reportsStore.templatesProjectId === projectId}
	<EmptyState icon={FileX} title="Template not found">
		<Button variant="outline" size="sm" href={ROUTES.reports('templates')}>
			<ArrowLeftIcon class="size-3.5" />
			Templates
		</Button>
	</EmptyState>
{:else if !template && reportsStore.templatesError && !reportsStore.templatesLoading}
	<EmptyState
		icon={TriangleAlertIcon}
		title="Template not loaded"
		description={reportsStore.templatesError}
	>
		<Button
			variant="outline"
			size="sm"
			onclick={() => reportsStore.fetchTemplates(projectId, true)}
		>
			Retry
		</Button>
	</EmptyState>
{:else if !template}
	<div class="space-y-4">
		<Skeleton class="h-9 w-64" />
		<Skeleton class="h-64 w-full" />
	</div>
{:else if style && branding && narrative}
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div class="min-w-0 space-y-1">
				<Button
					variant="ghost"
					size="sm"
					class="-ml-2 h-7 text-xs"
					href={ROUTES.reports('templates')}
				>
					<ArrowLeftIcon class="size-3" />
					Templates
				</Button>
				<div class="flex flex-wrap items-center gap-2">
					<h1 class="text-2xl font-semibold tracking-tight">{name}</h1>
					{#if template.is_builtin}<Badge variant="outline">Default</Badge>{/if}
				</div>
				<p class="text-sm text-muted-foreground">{description}</p>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<Button variant="outline" size="sm" onclick={() => (generateOpen = true)}>
					<PlayIcon class="size-3.5" />
					Generate report
				</Button>
				{#if template.is_builtin}
					<LoadingButton
						size="sm"
						loading={duplicating}
						loadingLabel="Duplicating"
						onclick={saveAsCopy}>Duplicate template</LoadingButton
					>
				{:else}
					<LoadingButton
						size="sm"
						loading={saving}
						loadingLabel="Saving"
						disabled={!dirty || !formats.length}
						onclick={save}>Save</LoadingButton
					>
				{/if}
			</div>
		</div>

		{#if template.is_builtin}
			<Card.Root class="border-dashed py-3">
				<div class="px-4 text-sm text-muted-foreground">Default templates are read-only.</div>
			</Card.Root>
		{/if}

		<Tabs.Root value="sections">
			<ScrollArea orientation="horizontal" class="w-full max-w-full sm:w-fit">
				<Tabs.List>
					<Tabs.Trigger value="sections" class="gap-1.5">
						<ListOrderedIcon class="size-4" />
						Sections
					</Tabs.Trigger>
					<Tabs.Trigger value="look" class="gap-1.5">
						<PaletteIcon class="size-4" />
						Look
					</Tabs.Trigger>
					<Tabs.Trigger value="branding" class="gap-1.5">
						<StampIcon class="size-4" />
						Branding
					</Tabs.Trigger>
					<Tabs.Trigger value="narrative" class="gap-1.5">
						<PenLineIcon class="size-4" />
						Narrative
					</Tabs.Trigger>
					<Tabs.Trigger value="document" class="gap-1.5">
						<FileTextIcon class="size-4" />
						Document
					</Tabs.Trigger>
				</Tabs.List>
			</ScrollArea>

			<div
				class="mt-6"
				class:pointer-events-none={template.is_builtin}
				class:opacity-70={template.is_builtin}
			>
				<Tabs.Content value="sections"><SectionList bind:sections /></Tabs.Content>
				<Tabs.Content value="look"><LookPanel bind:style /></Tabs.Content>
				<Tabs.Content value="branding"><BrandingPanel bind:branding /></Tabs.Content>
				<Tabs.Content value="narrative"><NarrativePanel bind:narrative /></Tabs.Content>
				<Tabs.Content value="document">
					<div class="flex max-w-xl flex-col gap-4">
						<FormField label="Template name">
							{#snippet children({ id })}
								<Input {id} bind:value={name} class="h-9" />
							{/snippet}
						</FormField>
						<FormField label="Description">
							{#snippet children({ id })}
								<Input {id} bind:value={description} class="h-9" />
							{/snippet}
						</FormField>
						<FormField label="Document title">
							{#snippet children({ id })}
								<Input
									{id}
									bind:value={title}
									class="h-9"
									placeholder="Security Assessment Report"
								/>
							{/snippet}
						</FormField>
						<FormField label="Document subtitle">
							{#snippet children({ id })}
								<Input {id} bind:value={subtitle} class="h-9" />
							{/snippet}
						</FormField>
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
									<ToggleGroup.Item {value} aria-label={label} class="px-3"
										>{label}</ToggleGroup.Item
									>
								{/each}
							</ToggleGroup.Root>
						</div>
					</div>
				</Tabs.Content>
			</div>
		</Tabs.Root>
	</div>

	<GenerateDialog bind:open={generateOpen} {projectId} template={template.id} />
	<UnsavedChangesDialog
		open={leaveTo !== null}
		onOpenChange={(v) => {
			if (!v) leaveTo = null;
		}}
		onConfirm={() => {
			const to = leaveTo;
			leaveTo = null;
			if (!to) return;
			allowNav = true;
			void goto(to);
		}}
	/>
{/if}
