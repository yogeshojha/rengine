<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';
	import PlayIcon from '@lucide/svelte/icons/play';
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
	let generateOpen = $state(false);
	let leaveTo = $state<string | null>(null);

	$effect(() => {
		const id = projectId;
		if (!id) return;
		void reportsStore.fetchTemplates(id);
		void reportCatalog.fetch();
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
		breadcrumbStore.set(found.id, found.name);
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

	function toggleFormat(value: string) {
		formats = formats.includes(value) ? formats.filter((f) => f !== value) : [...formats, value];
	}

	async function save() {
		if (!template || !style || !branding || !narrative) return;
		if (!formats.length) {
			toast.error('Choose at least one output format.');
			return;
		}
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
		if (ok) toast.success('Saved.');
	}

	async function saveAsCopy() {
		if (!template || !style || !branding || !narrative) return;
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
		if (created) {
			toast.success(`${created.name} is ready to edit.`);
			void goto(ROUTES.reportTemplate(created.id));
		}
	}
</script>

<svelte:head><title>{name || 'Report template'} · reNgine</title></svelte:head>

{#if !template}
	<div class="space-y-4">
		<Skeleton class="h-9 w-64" />
		<Skeleton class="h-64 w-full" />
	</div>
{:else if style && branding && narrative}
	<div class="space-y-5">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="min-w-0 space-y-1">
				<Button
					variant="ghost"
					size="sm"
					class="-ml-2 h-7 text-xs"
					href={ROUTES.reports('templates')}
				>
					<ArrowLeftIcon class="mr-1 size-3" />
					Templates
				</Button>
				<div class="flex flex-wrap items-center gap-2">
					<h1 class="text-2xl font-semibold tracking-tight">{name}</h1>
					{#if template.is_builtin}<Badge variant="outline">Shipped</Badge>{/if}
				</div>
				<p class="text-sm text-muted-foreground">{description}</p>
			</div>
			<div class="flex items-center gap-2">
				<Button variant="outline" onclick={() => (generateOpen = true)}>
					<PlayIcon class="mr-1.5 size-3.5" />
					Generate
				</Button>
				{#if template.is_builtin}
					<Button onclick={saveAsCopy}>Duplicate to edit</Button>
				{:else}
					<LoadingButton loading={saving} disabled={!dirty} onclick={save}>Save</LoadingButton>
				{/if}
			</div>
		</div>

		{#if template.is_builtin}
			<Card.Root class="border-dashed py-3">
				<div class="px-4 text-sm text-muted-foreground">
					This is a shipped template. Duplicate it to change anything.
				</div>
			</Card.Root>
		{/if}

		<Tabs.Root value="sections">
			<Tabs.List>
				<Tabs.Trigger value="sections">Sections</Tabs.Trigger>
				<Tabs.Trigger value="look">Look</Tabs.Trigger>
				<Tabs.Trigger value="branding">Branding</Tabs.Trigger>
				<Tabs.Trigger value="narrative">Narrative</Tabs.Trigger>
				<Tabs.Trigger value="document">Document</Tabs.Trigger>
			</Tabs.List>

			<div
				class="mt-5"
				class:pointer-events-none={template.is_builtin}
				class:opacity-70={template.is_builtin}
			>
				<Tabs.Content value="sections"><SectionList bind:sections /></Tabs.Content>
				<Tabs.Content value="look"><LookPanel bind:style /></Tabs.Content>
				<Tabs.Content value="branding"><BrandingPanel bind:branding /></Tabs.Content>
				<Tabs.Content value="narrative"><NarrativePanel bind:narrative /></Tabs.Content>
				<Tabs.Content value="document">
					<div class="max-w-xl space-y-4">
						<div class="space-y-1.5">
							<Label class="text-xs">Template name</Label>
							<Input bind:value={name} class="h-9" />
						</div>
						<div class="space-y-1.5">
							<Label class="text-xs">What this template is for</Label>
							<Input bind:value={description} class="h-9" />
						</div>
						<div class="space-y-1.5">
							<Label class="text-xs">Document title</Label>
							<Input bind:value={title} class="h-9" placeholder="Security Assessment Report" />
						</div>
						<div class="space-y-1.5">
							<Label class="text-xs">Document subtitle</Label>
							<Input bind:value={subtitle} class="h-9" />
						</div>
						<div class="space-y-1.5">
							<Label class="text-xs">Formats produced</Label>
							<div class="flex flex-wrap gap-2">
								{#each Object.entries(FORMAT_LABELS) as [value, label] (value)}
									<button
										type="button"
										class="rounded-md border px-2.5 py-1.5 text-xs transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
										data-active={formats.includes(value)}
										onclick={() => toggleFormat(value)}
									>
										{label}
									</button>
								{/each}
							</div>
						</div>
					</div>
				</Tabs.Content>
			</div>
		</Tabs.Root>
	</div>

	<GenerateDialog bind:open={generateOpen} {projectId} />
	<UnsavedChangesDialog
		open={leaveTo !== null}
		onOpenChange={(v) => {
			if (!v) leaveTo = null;
		}}
		onConfirm={() => {
			const to = leaveTo;
			leaveTo = null;
			if (to) void goto(to);
		}}
	/>
{/if}
