<script lang="ts">
	import { untrack } from 'svelte';
	import { Label } from '$lib/components/ui/label';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Switch } from '$lib/components/ui/switch';
	import * as Select from '$lib/components/ui/select';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { NO_CONTEXT_LABEL } from '$lib/types/scan-context';
	import { SELECT_NONE } from '$lib/constants';
	import {
		decodeSelection,
		defaultSelection,
		encodeSelection,
		readQuickScanPrefs,
		rememberQuickScanToggle,
		type QuickScanSelection
	} from '$lib/utilities/quick-scan';

	interface Props {
		id: string;
		title: string;
		description: string;
		fallbackNote: string;
		storageKey: string;
		enabled: boolean;
		selection: QuickScanSelection | null;
		contextId: string;
		armed?: boolean;
		pending?: boolean;
		disabled?: boolean;
	}

	let {
		id,
		title,
		description,
		fallbackNote,
		storageKey,
		enabled = $bindable(),
		selection = $bindable(),
		contextId = $bindable(),
		armed = $bindable(false),
		pending = $bindable(false),
		disabled = false
	}: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? null);
	let presets = $derived(engineCatalogStore.presets);
	let engines = $derived(scanEnginesStore.engines);
	let catalogReady = $derived(engineCatalogStore.hasFetched || !!engineCatalogStore.error);
	let enginesReady = $derived(
		(scanEnginesStore.fetchedProjectId === projectId || !!scanEnginesStore.error) &&
			!scanEnginesStore.isLoading
	);
	let contextsReady = $derived(
		(scanContextsStore.fetchedProjectId === projectId || !!scanContextsStore.error) &&
			!scanContextsStore.isLoading
	);
	let error = $derived(engineCatalogStore.error);
	let ready = $derived(catalogReady && enginesReady && contextsReady);

	let selectionValid = $derived.by(() => {
		const s = selection;
		if (!s) return false;
		return s.kind === 'recipe'
			? presets.some((p) => p.name === s.preset)
			: engines.some((e) => e.id === s.engineId);
	});
	let armedNow = $derived(enabled && !error && ready && selectionValid);
	let pendingNow = $derived(enabled && !error && !armedNow);

	let selectionLabel = $derived.by(() => {
		const s = selection;
		if (!s) return 'Select configuration';
		if (s.kind === 'recipe')
			return presets.find((p) => p.name === s.preset)?.title ?? 'Select configuration';
		return engines.find((e) => e.id === s.engineId)?.name ?? 'Select configuration';
	});
	let contextLabel = $derived(
		contextId === SELECT_NONE
			? NO_CONTEXT_LABEL
			: (scanContextsStore.contexts.find((c) => c.id === contextId)?.name ?? 'Select context')
	);

	$effect(() => {
		armed = armedNow;
	});

	$effect(() => {
		pending = pendingNow;
	});

	let attempted: string | null = null;
	$effect(() => {
		if (!enabled || !projectId) return;
		const pid = projectId;
		untrack(() => {
			if (attempted === pid) return;
			attempted = pid;
			if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
			if (scanEnginesStore.fetchedProjectId !== pid) scanEnginesStore.fetchEngines(pid);
			if (scanContextsStore.fetchedProjectId !== pid) scanContextsStore.fetchContexts(pid);
		});
	});

	let restored = false;
	$effect(() => {
		if (restored) return;
		restored = true;
		untrack(() => {
			enabled = readQuickScanPrefs(storageKey, []).enabled;
		});
	});

	$effect(() => {
		if (!enabled || !ready) return;
		const currentPresets = presets;
		const currentEngines = engines;
		const contexts = scanContextsStore.contexts;
		untrack(() => {
			if (!selectionValid) {
				const prefs = readQuickScanPrefs(storageKey, currentPresets);
				const stored = prefs.selection;
				const storedValid =
					!!stored &&
					(stored.kind === 'recipe'
						? currentPresets.some((p) => p.name === stored.preset)
						: currentEngines.some((e) => e.id === stored.engineId));
				selection = storedValid ? stored : defaultSelection(currentPresets);
				if (prefs.contextId && contexts.some((c) => c.id === prefs.contextId)) {
					contextId = prefs.contextId;
				}
			}
			if (contextId !== SELECT_NONE && !contexts.some((c) => c.id === contextId)) {
				contextId = SELECT_NONE;
			}
		});
	});

	function toggle(value: boolean) {
		enabled = value;
		rememberQuickScanToggle(storageKey, value);
	}
</script>

<div class="space-y-3 px-6 py-4">
	<div class="flex items-start justify-between gap-4">
		<div class="space-y-0.5">
			<Label for={id}>{title}</Label>
			<p class="text-xs text-muted-foreground">{description}</p>
		</div>
		<span class="flex h-5 shrink-0 items-center">
			<Switch {id} checked={enabled} onCheckedChange={toggle} {disabled} />
		</span>
	</div>

	{#if enabled}
		{#if error}
			<p class="text-xs text-destructive">{error} {fallbackNote}</p>
		{:else if !ready}
			<div class="grid gap-3 sm:grid-cols-2">
				<Skeleton class="h-9 w-full rounded-md" />
				<Skeleton class="h-9 w-full rounded-md" />
			</div>
		{:else}
			<div class="grid gap-3 sm:grid-cols-2">
				<div class="space-y-1.5">
					<Label for="{id}-plan" class="text-xs text-muted-foreground">Configuration</Label>
					<Select.Root
						type="single"
						value={selection ? encodeSelection(selection) : ''}
						onValueChange={(v) => (selection = decodeSelection(v))}
						{disabled}
					>
						<Select.Trigger id="{id}-plan" class="w-full">{selectionLabel}</Select.Trigger>
						<Select.Content>
							<Select.Group>
								<Select.Label>Presets</Select.Label>
								{#each presets as preset (preset.name)}
									<Select.Item value="recipe:{preset.name}" label={preset.title}>
										{preset.title}
									</Select.Item>
								{/each}
							</Select.Group>
							{#if engines.length}
								<Select.Group>
									<Select.Label>Scan engines</Select.Label>
									{#each engines as engine (engine.id)}
										<Select.Item value="engine:{engine.id}" label={engine.name}>
											{engine.name}
										</Select.Item>
									{/each}
								</Select.Group>
							{/if}
						</Select.Content>
					</Select.Root>
				</div>
				<div class="space-y-1.5">
					<Label for="{id}-context" class="text-xs text-muted-foreground">Context</Label>
					<Select.Root type="single" bind:value={contextId} {disabled}>
						<Select.Trigger id="{id}-context" class="w-full">{contextLabel}</Select.Trigger>
						<Select.Content>
							<Select.Item value={SELECT_NONE} label={NO_CONTEXT_LABEL}>
								{NO_CONTEXT_LABEL}
							</Select.Item>
							{#each scanContextsStore.contexts as context (context.id)}
								<Select.Item value={context.id} label={context.name}>{context.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
			</div>
		{/if}
	{/if}
</div>
