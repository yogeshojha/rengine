<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import IssuePreview from './issue-preview.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import DestinationPicker from './destination-picker.svelte';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { auth } from '$lib/stores/auth.svelte';
	import { issueTrackersApi } from '$lib/api/issue-trackers';
	import { issueTrackers } from '$lib/stores/issue-trackers.svelte';
	import { SELECT_NONE } from '$lib/constants';
	import {
		GROUPING_LABELS,
		Grouping,
		MAX_FILE_CHECKS,
		TRACKERS_BY_KIND
	} from '$lib/config/issue-trackers';
	import { ROUTES } from '$lib/config/routes';
	import { plural, pluralLabel } from '$lib/utilities/strings';
	import type { FilingPlan, FilingResult } from '$lib/types/issue-tracker';

	interface Props {
		open: boolean;
		projectId: string;
		scanId: string;
		fingerprints?: string[];
		templateIds?: string[];
		onFiled?: (result: FilingResult) => void;
	}

	let {
		open = $bindable(),
		projectId,
		scanId,
		fingerprints = [],
		templateIds = [],
		onFiled
	}: Props = $props();

	const PLAN_DELAY_MS = 200;
	const SHOWN_ISSUES = 50;

	let trackerId = $state<string>(SELECT_NONE);
	let destination = $state('');
	let grouping = $state<Grouping>(Grouping.AUTO);
	let title = $state('');
	let planTitle = $state('');
	let plan = $state<FilingPlan | null>(null);
	let planning = $state(false);
	let failure = $state<string | null>(null);
	let filing = $state(false);
	let req = 0;

	const trackers = $derived(issueTrackers.active);
	const admin = $derived(auth.user?.is_superuser ?? false);
	const tooMany = $derived(templateIds.length > MAX_FILE_CHECKS);
	const pickedDestination = $derived(
		trackerId === SELECT_NONE || !admin ? null : destination.trim() || null
	);
	const chosen = $derived(trackers.find((t) => t.id === trackerId) ?? null);
	const spec = $derived(chosen ? TRACKERS_BY_KIND[chosen.kind] : null);
	const single = $derived(plan?.new_issues === 1 && plan.attached === 0);
	const several = $derived(fingerprints.length + templateIds.length > 1 || templateIds.length > 0);
	const ready = $derived(
		!!plan && !plan.refusal && plan.new_issues + plan.attached > 0 && !planning
	);
	const trackerLabel = $derived(
		chosen?.name ?? (plan?.tracker_name ? `By route · ${plan.tracker_name}` : 'By route')
	);
	const dirty = $derived(
		trackerId !== SELECT_NONE || grouping !== Grouping.AUTO || title.trim() !== planTitle.trim()
	);
	const guard = new DiscardGuard(
		() => dirty,
		() => (open = false)
	);

	$effect(() => {
		if (!open) return;
		untrack(() => void issueTrackers.load());
		trackerId = SELECT_NONE;
		destination = '';
		grouping = Grouping.AUTO;
		title = '';
		planTitle = '';
		plan = null;
		failure = null;
	});

	$effect(() => {
		if (!open) return;
		const body = {
			fingerprints,
			template_ids: templateIds,
			tracker_id: trackerId === SELECT_NONE ? null : trackerId,
			destination: pickedDestination,
			grouping
		};
		if (tooMany) return;
		const my = ++req;
		planning = true;
		const timer = setTimeout(async () => {
			try {
				const next = await issueTrackersApi.plan(projectId, scanId, body);
				if (my !== req) return;
				plan = next;
				failure = null;
				if (next.new_issues === 1 && next.issues[0] && !title) {
					title = next.issues[0].title;
					planTitle = title;
				}
			} catch (e) {
				if (my === req) failure = e instanceof Error ? e.message : 'Preview not loaded';
			} finally {
				if (my === req) planning = false;
			}
		}, PLAN_DELAY_MS);
		return () => clearTimeout(timer);
	});

	function pickTracker(id: string) {
		trackerId = id;
		destination = trackers.find((t) => t.id === id)?.destination ?? '';
	}

	async function file() {
		if (!plan) return;
		filing = true;
		try {
			const result = await issueTrackersApi.file(projectId, scanId, {
				fingerprints,
				template_ids: templateIds,
				tracker_id: trackerId === SELECT_NONE ? null : trackerId,
				destination: pickedDestination,
				grouping,
				title: single ? title.trim() || null : null
			});
			const parts = [];
			if (result.new_issues)
				parts.push(`${plural(result.new_issues, 'issue', 'issues')} queued for filing`);
			if (result.attached)
				parts.push(`${plural(result.attached, 'location', 'locations')} added to open issues`);
			toast.success(parts.join(' · ') || 'No findings to file');
			void issueTrackers.loadProject(projectId, true);
			onFiled?.(result);
			open = false;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Issues not filed');
		} finally {
			filing = false;
		}
	}
</script>

<Dialog.Root bind:open={() => open, (next) => (next ? (open = true) : !filing && guard.close())}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-4 sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>{several ? 'File issues' : 'File issue'}</Dialog.Title>
		</Dialog.Header>

		{#if issueTrackers.loaded && !trackers.length}
			<p class="text-sm text-muted-foreground">
				{issueTrackers.trackers.length
					? 'All issue trackers are disabled.'
					: 'No issue tracker connected.'}
				<a href={ROUTES.issueTrackers('trackers')} class="text-primary">Issue trackers</a>
			</p>
		{:else if tooMany}
			<p class="text-sm text-destructive" role="alert">Select up to {MAX_FILE_CHECKS} checks.</p>
		{:else}
			<div class="grid gap-3 sm:grid-cols-2">
				<FormField label="Tracker">
					{#snippet children({ id })}
						<Select.Root type="single" value={trackerId} onValueChange={pickTracker}>
							<Select.Trigger {id} class="w-full">{trackerLabel}</Select.Trigger>
							<Select.Content>
								<Select.Item value={SELECT_NONE}>By route</Select.Item>
								{#each trackers as option (option.id)}
									<Select.Item value={option.id}>{option.name}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					{/snippet}
				</FormField>
				{#if spec && admin}
					<FormField label={spec.destinationLabel}>
						{#snippet children({ id })}
							<DestinationPicker
								{id}
								{trackerId}
								bind:value={destination}
								placeholder={spec.destinationPlaceholder}
								searchLabel={`Search ${pluralLabel(spec.destinationLabel).toLowerCase()}`}
							/>
						{/snippet}
					</FormField>
				{:else if plan?.destination}
					<div class="flex flex-col gap-2">
						<span class="text-sm font-medium">
							{TRACKERS_BY_KIND[plan.tracker_kind ?? '']?.destinationLabel ?? 'Destination'}
						</span>
						<div class="flex h-9 items-center font-mono text-sm">{plan.destination}</div>
					</div>
				{/if}
			</div>

			{#if several}
				<ToggleGroup.Root
					type="single"
					size="sm"
					variant="outline"
					class="w-fit"
					value={grouping}
					onValueChange={(v) => v && (grouping = v as Grouping)}
				>
					{#each [Grouping.AUTO, Grouping.SEPARATE] as option (option)}
						<ToggleGroup.Item value={option} class="h-7 px-2.5 text-xs">
							{GROUPING_LABELS[option]}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
			{/if}

			{#if failure}
				<p class="text-sm text-destructive" role="alert">{failure}</p>
			{:else if plan?.refusal}
				<p class="text-sm text-destructive" role="alert">{plan.refusal}</p>
			{:else if !plan}
				<div class="flex flex-col gap-2">
					<Skeleton class="h-5 w-1/2" />
					<Skeleton class="h-24 w-full" />
				</div>
			{:else}
				<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
					<span class="font-medium">{plural(plan.new_issues, 'new issue', 'new issues')}</span>
					{#if plan.attached}
						<span class="text-muted-foreground">
							{plural(plan.attached, 'location', 'locations')} added to open issues
						</span>
					{/if}
					{#if plan.not_filed}
						<span class="text-destructive">
							{plural(plan.not_filed, 'finding', 'findings')} not filed ·
							<a href={ROUTES.issueTrackers('issues')} class="text-primary">View</a>
						</span>
					{/if}
					{#if plan.already_filed}
						<span class="text-muted-foreground">
							{plural(plan.already_filed, 'finding', 'findings')} already filed
						</span>
					{/if}
				</div>

				{#if single}
					<FormField label="Title">
						{#snippet children({ id })}
							<Input {id} bind:value={title} maxlength={255} />
						{/snippet}
					</FormField>
					{#if plan.preview}
						<IssuePreview blocks={plan.preview} />
					{/if}
				{:else if plan.issues.length}
					<ScrollArea
						class="min-h-0 flex-1 rounded-lg border [&_[data-slot=scroll-area-viewport]]:max-h-80"
					>
						<div class="divide-y">
							{#each plan.issues.slice(0, SHOWN_ISSUES) as issue, i (i)}
								<div class="flex items-start gap-3 px-3 py-2">
									<span class="flex h-5 w-20 shrink-0 items-center">
										<SeverityMark severity={issue.severity} />
									</span>
									<div class="min-w-0 flex-1">
										<div class="text-sm leading-5 wrap-anywhere">{issue.title}</div>
										<div class="text-2xs text-muted-foreground">
											{#if issue.attach_to}
												Added to <span class="font-mono">{issue.attach_to}</span> ·
											{/if}
											{plural(issue.findings, 'location', 'locations')}
										</div>
									</div>
								</div>
							{/each}
						</div>
					</ScrollArea>
					{#if plan.issues.length > SHOWN_ISSUES}
						<p class="text-xs text-muted-foreground">
							{(plan.issues.length - SHOWN_ISSUES).toLocaleString()} more issues
						</p>
					{/if}
				{/if}
			{/if}
		{/if}

		<Dialog.Footer>
			<Button variant="outline" disabled={filing} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton loading={filing} loadingLabel="Filing" disabled={!ready} onclick={file}>
				{plan && plan.new_issues > 1
					? `File ${plan.new_issues} issues`
					: several
						? 'File issues'
						: 'File issue'}
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
