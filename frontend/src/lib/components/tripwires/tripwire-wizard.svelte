<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Check from '@lucide/svelte/icons/check';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import * as Select from '$lib/components/ui/select';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Switch } from '$lib/components/ui/switch';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import QueryBar from '$lib/components/scans/results/query-bar/query-bar.svelte';
	import { QUERY_SCHEMAS } from '$lib/stores/query-schema.svelte';
	import { loadTripwireFacets } from '$lib/utilities/tripwire-facets';
	import type { QueryError } from '$lib/types/asset-query';
	import type { Facet } from '$lib/utilities/scan-insights';
	import { tripwiresApi } from '$lib/api/tripwires';
	import { tripwiresStore } from '$lib/stores/tripwires.svelte';
	import {
		ActionKind,
		FireOn,
		MAX_NAME,
		MAX_RUNS_PER_DAY,
		ScopeKind,
		TripwireTrigger,
		actionLabel,
		dimensionSpec
	} from '$lib/config/tripwires';
	import { SurfaceDimension, type SurfaceDimension as Dimension } from '$lib/config/surface';
	import type {
		NotifyAction,
		ScanAction,
		Tripwire,
		TripwireAction,
		TripwireCreate,
		TripwireScope
	} from '$lib/types/tripwire';
	import BacktestPanel from './backtest-panel.svelte';
	import ChannelPicker from './channel-picker.svelte';
	import ConditionPreview from './condition-preview.svelte';
	import FireOnField from './fire-on-field.svelte';
	import FlowStrip, { type FlowAction, type FlowNode } from './flow-strip.svelte';
	import { withArticle } from '$lib/utilities/strings';
	import { defaultTripwireName, scopeText } from './format';
	import ScopeField from './scope-field.svelte';
	import StagePicker from './stage-picker.svelte';

	export interface TripwireDraft {
		name?: string;
		dimension?: string;
		query?: string;
		trigger?: string;
		fire_on?: string;
		scope?: TripwireScope;
		scopeLabels?: string[];
	}

	interface Props {
		open: boolean;
		projectId: string;
		projectSlug: string;
		tripwire: Tripwire | null;
		draft?: TripwireDraft | null;
		onOpenChange: (open: boolean) => void;
		onSaved: (tripwire: Tripwire) => void;
	}

	let {
		open,
		projectId,
		projectSlug,
		tripwire,
		draft = null,
		onOpenChange,
		onSaved
	}: Props = $props();

	const STEPS: { key: string; label: string; node: FlowNode | null }[] = [
		{ key: 'when', label: 'When', node: 'when' },
		{ key: 'if', label: 'If', node: 'if' },
		{ key: 'then', label: 'Then', node: 'then' },
		{ key: 'review', label: 'Review', node: null }
	];
	const HINTS: Record<string, string> = {
		[SurfaceDimension.WEB_ASSETS]: 'host:vpn-* status:200',
		[SurfaceDimension.ENDPOINTS]: 'path:/admin is:live',
		[SurfaceDimension.SERVICES]: 'service:ssh is:new',
		[SurfaceDimension.IPS]: 'is:open -is:cdn',
		[SurfaceDimension.VULNERABILITIES]: 'severity:critical',
		[SurfaceDimension.SOFTWARE]: 'is:kev',
		[SurfaceDimension.SECRETS]: 'is:exposed'
	};
	const CARD =
		'flex cursor-pointer items-start gap-2.5 rounded-lg border border-border p-3 transition-colors hover:bg-muted/40 has-[[data-state=checked]]:border-primary/50 has-[[data-state=checked]]:bg-primary/5';

	let step = $state(0);
	let reached = $state(0);
	let name = $state('');
	let dimension = $state<string>(SurfaceDimension.WEB_ASSETS);
	let query = $state('');
	let trigger = $state<string>(TripwireTrigger.ScanSettled);
	let fireOn = $state<string>(FireOn.Appears);
	let scope = $state<TripwireScope>({ kind: ScopeKind.All, ids: [] });
	let scopeLabels = $state<string[]>([]);
	let notifyOn = $state(true);
	let channelIds = $state<string[]>([]);
	let scanOn = $state(false);
	let stages = $state<string[]>([]);
	let enabled = $state(true);
	let saving = $state(false);
	let queryError = $state<QueryError | null>(null);
	let queryReady = $state(true);
	let previewBusy = $state(false);
	let facets = $state<Record<string, Facet[]>>({});
	let facetsFor = $state('');
	let nameError = $state('');
	let initial = $state('');
	let body = $state<HTMLElement | null>(null);

	let catalog = $derived(tripwiresStore.catalog);
	let isEdit = $derived(tripwire !== null);
	let spec = $derived(dimensionSpec(dimension));
	let dimensionLabel = $derived(
		catalog?.dimensions.find((d) => d.key === dimension)?.label ?? spec.label
	);
	let previewRequest = $derived({ dimension, query: query.trim(), fire_on: fireOn, scope });
	let scopeReady = $derived(scope.kind === ScopeKind.All || scope.ids.length > 0);
	let actionsReady = $derived(!scanOn || stages.length > 0);
	let queryOk = $derived(query.trim().length > 0 && queryReady && !queryError && !previewBusy);
	let stepReady = $derived([scopeReady, queryOk, actionsReady, name.trim().length > 0]);
	let blocker = $derived.by((): string | null => {
		if (step === 0 && !scopeReady) return 'Choose at least one target, organization or tag.';
		if (step === 1) {
			if (!query.trim()) return 'A query is required.';
			if (queryError) return 'The query has an error.';
			if (!queryReady) return 'The query is incomplete.';
			if (previewBusy) return 'Evaluating the query.';
		}
		if (step === 2 && !actionsReady) return 'Choose at least one stage.';
		if (step === 3 && !name.trim()) return 'Name is required.';
		return null;
	});
	let queryStore = $derived(QUERY_SCHEMAS[dimension as Dimension]);
	let canSave = $derived(!saving && stepReady.every(Boolean));
	let scopeLine = $derived(scopeText(scope, scopeLabels));
	let stageTitles = $derived(stages.map((s) => tripwiresStore.stageTitle(s)));
	let channelNames = $derived(
		channelIds.map((id) => tripwiresStore.channelName(id)).filter((n): n is string => !!n)
	);
	let dirty = $derived(snapshot() !== initial);
	const guard = new DiscardGuard(
		() => dirty,
		() => onOpenChange(false)
	);

	function snapshot(): string {
		return JSON.stringify([
			name.trim(),
			dimension,
			query.trim(),
			trigger,
			fireOn,
			scope,
			notifyOn,
			channelIds,
			scanOn,
			stages,
			enabled
		]);
	}

	let actionLines = $derived.by((): FlowAction[] => {
		const out: FlowAction[] = [];
		if (notifyOn) {
			out.push({
				label: actionLabel(ActionKind.Notify),
				detail: channelNames.length ? channelNames.join(', ') : 'Channels subscribed to Tripwires'
			});
		}
		if (scanOn) {
			out.push({
				label: actionLabel(ActionKind.Scan),
				detail: stageTitles.length ? stageTitles.join(', ') : 'No stage chosen'
			});
		}
		return out;
	});

	$effect(() => {
		if (!open) return;
		const row = tripwire;
		const seed = draft;
		untrack(() => {
			void tripwiresStore.loadCatalog();
			step = 0;
			reached = row ? STEPS.length - 1 : 0;
			name = row?.name ?? seed?.name ?? '';
			dimension = row?.dimension ?? seed?.dimension ?? SurfaceDimension.WEB_ASSETS;
			query = row?.query ?? seed?.query ?? '';
			trigger = row?.trigger ?? seed?.trigger ?? TripwireTrigger.ScanSettled;
			fireOn = row?.fire_on ?? seed?.fire_on ?? FireOn.Appears;
			scope = row
				? { kind: row.scope.kind, ids: [...row.scope.ids] }
				: (seed?.scope ?? { kind: ScopeKind.All, ids: [] });
			scopeLabels = row ? [...row.scope.labels] : (seed?.scopeLabels ?? []);
			const notify = row?.actions.find((a) => a.kind === ActionKind.Notify) as
				| NotifyAction
				| undefined;
			const scan = row?.actions.find((a) => a.kind === ActionKind.Scan) as ScanAction | undefined;
			notifyOn = row ? Boolean(notify) : true;
			channelIds = notify ? [...notify.channel_ids] : [];
			scanOn = Boolean(scan);
			stages = scan ? [...scan.stages] : [];
			enabled = row?.enabled ?? true;
			queryError = null;
			queryReady = true;
			previewBusy = false;
			facets = {};
			facetsFor = '';
			nameError = '';
			initial = snapshot();
		});
	});

	$effect(() => {
		if (!open || step !== 1) return;
		const key = `${dimension}|${JSON.stringify(scope)}`;
		const project = projectId;
		if (facetsFor === key || !project) return;
		untrack(() => {
			facetsFor = key;
			facets = {};
			void loadTripwireFacets(dimension, project, scope).then((loaded) => {
				if (facetsFor === key) facets = loaded;
			});
		});
	});

	function setDimension(next: string) {
		if (!next || next === dimension) return;
		dimension = next;
		queryError = null;
		queryReady = true;
		if (scanOn && stages.length === 0) stages = defaultStages(next);
	}

	function defaultStages(key: string): string[] {
		return tripwiresStore.dimension(key)?.default_stages ?? [];
	}

	function setScanOn(on: boolean) {
		scanOn = on;
		if (on && stages.length === 0) stages = defaultStages(dimension);
	}

	/** Focus the step's first field: the query on If, the checked choice on When. */
	function focusStep() {
		const root = body;
		if (!root) return;
		const field =
			root.querySelector<HTMLElement>('[data-step-focus] input') ??
			root.querySelector<HTMLElement>(
				'[role="radio"][data-state="checked"], input:not([type="hidden"]):not(:disabled), button:not(:disabled)'
			);
		field?.focus({ preventScroll: true });
	}

	function show(index: number) {
		step = index;
		void tick().then(focusStep);
	}

	function goTo(index: number) {
		if (index > reached) return;
		show(index);
	}

	function next() {
		if (!stepReady[step]) return;
		if (step === STEPS.length - 2 && !name.trim()) name = defaultTripwireName(spec, query);
		show(Math.min(step + 1, STEPS.length - 1));
		reached = Math.max(reached, step);
	}

	function back() {
		show(Math.max(step - 1, 0));
	}

	function actions(): TripwireAction[] {
		const out: TripwireAction[] = [];
		if (notifyOn) out.push({ kind: ActionKind.Notify, channel_ids: channelIds });
		if (scanOn) out.push({ kind: ActionKind.Scan, stages });
		return out;
	}

	async function save() {
		nameError = name.trim() ? '' : 'Name is required';
		if (nameError || !canSave) return;
		const body: TripwireCreate = {
			name: name.trim(),
			dimension,
			query: query.trim(),
			trigger,
			fire_on: fireOn,
			scope,
			actions: actions(),
			enabled
		};
		saving = true;
		try {
			const saved = isEdit
				? await tripwiresApi.update(tripwire!.id, projectId, body)
				: await tripwiresApi.create(projectId, body);
			toast.success(isEdit ? `${saved.name} saved` : `${saved.name} created`);
			onSaved(saved);
			onOpenChange(false);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Tripwire not saved');
		} finally {
			saving = false;
		}
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key !== 'Enter' || event.shiftKey) return;
		const target = event.target as HTMLElement | null;
		if (target?.getAttribute('role') === 'combobox') return;
		if (step < STEPS.length - 1) {
			event.preventDefault();
			next();
		}
	}
</script>

<Dialog.Root
	bind:open={
		() => open,
		(next) => {
			if (next) onOpenChange(true);
			else if (!saving) guard.close();
		}
	}
>
	<Dialog.Content
		class="grid h-[min(90vh,52rem)] grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden p-0 sm:max-w-3xl"
		onkeydown={onKeydown}
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			void tick().then(focusStep);
		}}
	>
		<Dialog.Header class="gap-4 border-b py-4 pr-12 pl-6">
			<div class="flex items-start justify-between gap-4">
				<div class="flex flex-col gap-1">
					<Dialog.Title>{isEdit ? tripwire?.name : 'New tripwire'}</Dialog.Title>
					<Dialog.Description class="sr-only">
						Step {step + 1} of {STEPS.length} · {STEPS[step].label}
					</Dialog.Description>
				</div>
				<ol class="flex items-center gap-1" aria-label="Steps">
					{#each STEPS as item, index (item.key)}
						{@const done = index < step || (isEdit && index !== step)}
						{@const current = index === step}
						<li class="flex items-center gap-1">
							<button
								type="button"
								class="flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs transition-colors disabled:cursor-default {current
									? 'font-medium text-foreground'
									: index <= reached
										? 'text-muted-foreground hover:text-foreground'
										: 'text-muted-foreground/60'}"
								aria-current={current ? 'step' : undefined}
								disabled={index > reached}
								onclick={() => goTo(index)}
							>
								<span
									class="flex size-4 items-center justify-center rounded-full text-2xs font-semibold tabular-nums {current
										? 'bg-primary text-primary-foreground'
										: done
											? 'bg-success/15 text-success'
											: 'bg-muted text-muted-foreground'}"
								>
									{#if done && !current}<Check class="size-3" />{:else}{index + 1}{/if}
								</span>
								<span class="hidden md:inline">{item.label}</span>
							</button>
							{#if index < STEPS.length - 1}
								<span class="h-px w-3 bg-border" aria-hidden="true"></span>
							{/if}
						</li>
					{/each}
				</ol>
			</div>
			<FlowStrip
				current={STEPS[step].node}
				{trigger}
				scopeText={scopeLine}
				{dimension}
				{query}
				{fireOn}
				actions={actionLines}
			/>
		</Dialog.Header>

		<ScrollArea class="min-h-0" bind:viewportRef={body}>
			<div class="flex flex-col gap-5 px-6 py-5">
				{#if step === 0}
					<FormField label="Timing">
						{#snippet children({ id })}
							<RadioGroup.Root
								{id}
								value={trigger}
								onValueChange={(v) => v && (trigger = v)}
								class="grid gap-2 sm:grid-cols-2"
							>
								{#each catalog?.triggers ?? [] as choice (choice.key)}
									<Label for="trigger-{choice.key}" class={CARD}>
										<RadioGroup.Item value={choice.key} id="trigger-{choice.key}" class="mt-0.5" />
										<span class="flex flex-col gap-0.5">
											<span class="text-sm font-medium">{choice.label}</span>
											<span class="text-xs font-normal text-muted-foreground">{choice.help}</span>
										</span>
									</Label>
								{/each}
							</RadioGroup.Root>
						{/snippet}
					</FormField>
					<FormField label="Targets">
						{#snippet children({ id })}
							<ScopeField
								{projectSlug}
								{scope}
								labels={scopeLabels}
								onChange={(s, labels) => {
									scope = s;
									scopeLabels = labels;
								}}
								ids={{ kind: id, select: `${id}-value` }}
							/>
						{/snippet}
					</FormField>
				{:else if step === 1}
					<div class="grid gap-4 sm:grid-cols-[200px_minmax(0,1fr)]">
						<FormField label="Dimension">
							{#snippet children({ id })}
								<Select.Root type="single" value={dimension} onValueChange={setDimension}>
									<Select.Trigger {id} class="w-full">{dimensionLabel}</Select.Trigger>
									<Select.Content>
										{#each catalog?.dimensions ?? [] as d (d.key)}
											<Select.Item value={d.key} label={d.label}>{d.label}</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							{/snippet}
						</FormField>
						<FormField label="Query">
							{#snippet children({ id: _id })}
								<div class="[&>div]:rounded-xl" data-step-focus>
									<QueryBar
										store={queryStore}
										recentsKey={spec.recentsKey}
										hint={HINTS[dimension] ?? ''}
										placeholder="Condition, for example"
										value={query}
										{facets}
										busy={previewBusy}
										serverError={queryError}
										onChange={(v) => {
											query = v;
											queryError = null;
										}}
										onReady={(ready) => (queryReady = ready)}
										onSubmit={next}
									/>
								</div>
							{/snippet}
						</FormField>
					</div>
					<FormField label="Fires when {withArticle(spec.noun)}">
						{#snippet children({ id })}
							<FireOnField
								{id}
								modes={catalog?.fire_modes ?? []}
								value={fireOn}
								onChange={(v) => (fireOn = v)}
							/>
						{/snippet}
					</FormField>
					<p class="text-xs text-muted-foreground">A target's first scan does not fire.</p>
					<ConditionPreview
						{projectId}
						request={previewRequest}
						enabled={scopeReady && query.trim().length > 0 && queryReady}
						onError={(e) => (queryError = e)}
						onBusy={(b) => (previewBusy = b)}
					/>
				{:else if step === 2}
					<div class="flex flex-col gap-3 rounded-lg border p-4">
						<label class="flex items-center justify-between gap-4 text-sm">
							<span class="flex flex-col gap-0.5">
								<span class="font-medium">Notify</span>
								<span class="text-xs text-muted-foreground">One message per run.</span>
							</span>
							<Switch checked={notifyOn} onCheckedChange={(v) => (notifyOn = v)} />
						</label>
						{#if notifyOn}
							<ChannelPicker
								channels={catalog?.channels ?? []}
								selected={channelIds}
								onChange={(ids) => (channelIds = ids)}
							/>
						{/if}
					</div>
					<div class="flex flex-col gap-3 rounded-lg border p-4">
						<label class="flex items-center justify-between gap-4 text-sm">
							<span class="flex flex-col gap-0.5">
								<span class="font-medium">Focused scan</span>
								<span class="text-xs text-muted-foreground">
									Runs the chosen stages against the {spec.nounPlural} that fired. At most {catalog?.max_runs_per_day ??
										MAX_RUNS_PER_DAY} runs a day.
								</span>
							</span>
							<Switch checked={scanOn} onCheckedChange={setScanOn} />
						</label>
						{#if scanOn}
							<StagePicker
								stages={catalog?.stages ?? []}
								selected={stages}
								onChange={(s) => (stages = s)}
							/>
						{/if}
					</div>
				{:else}
					<FormField label="Name" error={nameError}>
						{#snippet children({ id })}
							<Input
								{id}
								bind:value={name}
								maxlength={MAX_NAME}
								aria-invalid={!!nameError}
								oninput={() => (nameError = '')}
							/>
						{/snippet}
					</FormField>
					<BacktestPanel {projectId} request={previewRequest} enabled={scopeReady && !queryError} />
					<label class="flex items-center justify-between gap-4 rounded-lg border p-4 text-sm">
						<span class="font-medium">Enabled</span>
						<Switch checked={enabled} onCheckedChange={(v) => (enabled = v)} />
					</label>
				{/if}
			</div>
		</ScrollArea>

		<div class="flex items-center gap-2 border-t bg-card px-6 py-4">
			{#if step > 0}
				<Button variant="ghost" onclick={back}>
					<ChevronLeft class="size-4" />
					Back
				</Button>
			{/if}
			<div class="min-w-0 flex-1 truncate text-xs text-muted-foreground" aria-live="polite">
				{blocker ?? ''}
			</div>
			<Button variant="outline" disabled={saving} onclick={() => guard.close()}>Cancel</Button>
			{#if step < STEPS.length - 1}
				<Button disabled={!stepReady[step]} onclick={next}>Continue</Button>
			{:else}
				<LoadingButton loading={saving} loadingLabel="Saving" disabled={!canSave} onclick={save}>
					{isEdit ? 'Save' : 'Create tripwire'}
				</LoadingButton>
			{/if}
		</div>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
