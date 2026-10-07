<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import Zap from '@lucide/svelte/icons/zap';
	import { toast } from 'svelte-sonner';
	import * as Popover from '$lib/components/ui/popover';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { scansApi } from '$lib/api/scans';
	import { targetsApi } from '$lib/api/targets';
	import { tripwiresApi } from '$lib/api/tripwires';
	import { tripwiresStore } from '$lib/stores/tripwires.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import {
		MAX_NAME,
		ActionKind,
		dimensionSpec,
		FireOn,
		SCOPE_LABELS,
		ScopeKind,
		TripwireTrigger
	} from '$lib/config/tripwires';
	import { ROUTES } from '$lib/config/routes';
	import type { Tripwire, TripwireScope } from '$lib/types/tripwire';
	import { withArticle } from '$lib/utilities/strings';
	import { defaultTripwireName } from './format';
	import QueryChip from './query-chip.svelte';
	import TripwireWizard, { type TripwireDraft } from './tripwire-wizard.svelte';

	interface Props {
		dimension: string;
		query: string;
		projectId?: string;
		scanId?: string | null;
		class?: string;
	}

	let { dimension, query, projectId = '', scanId = null, class: klass = '' }: Props = $props();

	const SCOPES = [
		{ key: 'target', label: 'This target' },
		{ key: ScopeKind.All, label: SCOPE_LABELS[ScopeKind.All] }
	];

	let open = $state(false);
	let name = $state('');
	let fireOn = $state<string>(FireOn.Appears);
	let scopeChoice = $state<string>('target');
	let targetId = $state<string | null>(null);
	let targetValue = $state('');
	let saving = $state(false);
	let wizardOpen = $state(false);
	let draft = $state<TripwireDraft | null>(null);
	let seededFor: string | null = null;

	let spec = $derived(dimensionSpec(dimension));
	let text = $derived(query.trim());
	let pid = $derived(projectId || projectsStore.activeProject?.id || '');
	let slug = $derived(projectsStore.activeProject?.slug ?? '');
	let modes = $derived(tripwiresStore.catalog?.fire_modes ?? []);
	let scope = $derived<TripwireScope>(
		scopeChoice === 'target' && targetId
			? { kind: ScopeKind.Targets, ids: [targetId] }
			: { kind: ScopeKind.All, ids: [] }
	);

	$effect(() => {
		if (!open) return;
		const sid = scanId;
		const project = pid;
		const key = [dimension, text, sid ?? '', project].join('\n');
		untrack(() => {
			void tripwiresStore.loadCatalog();
			if (key === seededFor) {
				if (sid && project && !targetId) void loadTarget(sid, project);
				return;
			}
			seededFor = key;
			name = defaultTripwireName(spec, text);
			fireOn = FireOn.Appears;
			scopeChoice = sid ? 'target' : ScopeKind.All;
			targetId = null;
			targetValue = '';
			if (sid && project) void loadTarget(sid, project);
		});
	});

	async function loadTarget(sid: string, project: string) {
		try {
			const scan = await scansApi.get(sid, project);
			const target = await targetsApi.get(scan.target_id);
			targetId = target.id;
			targetValue = target.target_value;
		} catch {
			targetId = null;
			scopeChoice = ScopeKind.All;
		}
	}

	async function create() {
		if (!pid || !name.trim()) return;
		saving = true;
		try {
			const saved = await tripwiresApi.create(pid, {
				name: name.trim(),
				dimension,
				query: text,
				trigger: TripwireTrigger.ScanSettled,
				fire_on: fireOn,
				scope,
				actions: [{ kind: ActionKind.Notify, channel_ids: [] }],
				enabled: true
			});
			tripwiresStore.upsert(saved);
			seededFor = null;
			open = false;
			toast.success(`${saved.name} created`, {
				action: {
					label: 'Open',
					onClick: () => void goto(ROUTES.tripwires({ tripwire: saved.id }))
				}
			});
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Tripwire not created');
		} finally {
			saving = false;
		}
	}

	function moreOptions() {
		draft = {
			name: name.trim(),
			dimension,
			query: text,
			fire_on: fireOn,
			scope,
			scopeLabels: scopeChoice === 'target' && targetId ? [targetValue] : []
		};
		open = false;
		wizardOpen = true;
	}

	function saved(tripwire: Tripwire) {
		tripwiresStore.upsert(tripwire);
		seededFor = null;
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" class={klass} aria-label="Tripwire on this query">
				<Zap class="h-4 w-4" />
				<span class="hidden sm:inline">Tripwire</span>
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-[min(24rem,calc(100vw-2rem))] p-0" align="end">
		<div class="flex flex-col gap-4 p-4">
			<div class="flex flex-col gap-1.5">
				<span class="text-sm font-medium">Tripwire on this query</span>
				<QueryChip {dimension} query={text} wrap />
			</div>
			<FormField label="Name">
				{#snippet children({ id })}
					<Input {id} bind:value={name} maxlength={MAX_NAME} class="h-8" />
				{/snippet}
			</FormField>
			<FormField label="Fires when {withArticle(spec.noun)}">
				{#snippet children({ id })}
					<ToggleGroup.Root
						{id}
						type="single"
						variant="outline"
						size="sm"
						value={fireOn}
						onValueChange={(v) => v && (fireOn = v)}
						class="justify-start"
					>
						{#each modes as mode (mode.key)}
							<ToggleGroup.Item value={mode.key}>{mode.label}</ToggleGroup.Item>
						{/each}
					</ToggleGroup.Root>
				{/snippet}
			</FormField>
			<FormField label="Scope">
				{#snippet children({ id })}
					<ToggleGroup.Root
						{id}
						type="single"
						variant="outline"
						size="sm"
						value={scopeChoice}
						onValueChange={(v) => v && (scopeChoice = v)}
						class="justify-start"
					>
						{#each SCOPES as choice (choice.key)}
							{#if choice.key !== 'target' || targetId}
								<ToggleGroup.Item value={choice.key}>
									{choice.key === 'target' && targetValue ? targetValue : choice.label}
								</ToggleGroup.Item>
							{/if}
						{/each}
					</ToggleGroup.Root>
				{/snippet}
			</FormField>
			{#if text}
				<p class="text-xs text-muted-foreground">
					Checked after each scan. Sent to the channels subscribed to Tripwires.
				</p>
			{:else}
				<p class="text-xs text-destructive">
					A query is required. Type one in the search bar first.
				</p>
			{/if}
		</div>
		<div class="flex items-center justify-between gap-2 border-t bg-muted/30 px-4 py-3">
			<Button variant="ghost" size="sm" onclick={moreOptions}>More options</Button>
			<LoadingButton
				size="sm"
				loading={saving}
				loadingLabel="Creating"
				disabled={!text || !name.trim() || !pid}
				onclick={create}
			>
				Create tripwire
			</LoadingButton>
		</div>
	</Popover.Content>
</Popover.Root>

<TripwireWizard
	open={wizardOpen}
	projectId={pid}
	projectSlug={slug}
	tripwire={null}
	{draft}
	onOpenChange={(v) => (wizardOpen = v)}
	onSaved={saved}
/>
