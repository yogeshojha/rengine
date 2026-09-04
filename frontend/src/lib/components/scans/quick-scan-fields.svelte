<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import { untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Switch } from '$lib/components/ui/switch';
	import * as Select from '$lib/components/ui/select';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { NO_CONTEXT_LABEL } from '$lib/types/scan-context';
	import { SELECT_NONE } from '$lib/constants';
	import {
		pickDefaultEngine,
		readQuickScanPrefs,
		rememberQuickScanToggle
	} from '$lib/utilities/quick-scan';

	interface Props {
		id: string;
		title: string;
		description: string;
		fallbackNote: string;
		storageKey: string;
		enabled: boolean;
		engineId: string;
		contextId: string;
		armed?: boolean;
		pending?: boolean;
		disabled?: boolean;
		onCreateEngine?: () => void;
	}

	let {
		id,
		title,
		description,
		fallbackNote,
		storageKey,
		enabled = $bindable(),
		engineId = $bindable(),
		contextId = $bindable(),
		armed = $bindable(false),
		pending = $bindable(false),
		disabled = false,
		onCreateEngine
	}: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? null);
	let enginesReady = $derived(
		(scanEnginesStore.fetchedProjectId === projectId || !!scanEnginesStore.error) &&
			!scanEnginesStore.isLoading
	);
	let contextsReady = $derived(
		(scanContextsStore.fetchedProjectId === projectId || !!scanContextsStore.error) &&
			!scanContextsStore.isLoading
	);
	let engineError = $derived(scanEnginesStore.error);
	let noEngines = $derived(enginesReady && !engineError && scanEnginesStore.engines.length === 0);
	let ready = $derived(enginesReady && contextsReady);

	let armedNow = $derived(enabled && !engineError && !noEngines && ready && !!engineId);
	let pendingNow = $derived(enabled && !engineError && !noEngines && !armedNow);

	let engineLabel = $derived(
		scanEnginesStore.engines.find((e) => e.id === engineId)?.name ?? 'Select engine'
	);
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

	let restored = false;
	$effect(() => {
		if (restored) return;
		restored = true;
		const prefs = readQuickScanPrefs(storageKey);
		untrack(() => {
			enabled = prefs.enabled;
			if (!engineId) engineId = prefs.engineId;
			if (contextId === SELECT_NONE) contextId = prefs.contextId;
		});
	});

	let attempted: string | null = null;
	$effect(() => {
		if (!enabled || !projectId) return;
		const pid = projectId;
		const busy = scanEnginesStore.isLoading || scanContextsStore.isLoading;
		untrack(() => {
			if (busy || attempted === pid) return;
			attempted = pid;
			if (scanEnginesStore.fetchedProjectId !== pid) scanEnginesStore.fetchEngines(pid);
			if (scanContextsStore.fetchedProjectId !== pid) scanContextsStore.fetchContexts(pid);
		});
	});

	$effect(() => {
		if (!enabled) return;
		const engines = enginesReady ? scanEnginesStore.engines : null;
		const contexts = contextsReady ? scanContextsStore.contexts : null;
		untrack(() => {
			if (engines && !engines.some((e) => e.id === engineId)) engineId = pickDefaultEngine(engines);
			if (contexts && contextId !== SELECT_NONE && !contexts.some((c) => c.id === contextId))
				contextId = SELECT_NONE;
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
		{#if engineError}
			<p class="text-xs text-destructive">{engineError} {fallbackNote}</p>
		{:else if !ready}
			<div class="grid gap-3 sm:grid-cols-2">
				<Skeleton class="h-9 w-full rounded-md" />
				<Skeleton class="h-9 w-full rounded-md" />
			</div>
		{:else if noEngines}
			<div class="space-y-2 rounded-md border border-border bg-muted/20 px-3 py-3">
				<p class="text-xs text-muted-foreground">
					No scan engines yet. An engine defines what a scan runs.
				</p>
				<Button
					type="button"
					variant="outline"
					size="sm"
					class="h-7 gap-1 text-xs"
					onclick={() => onCreateEngine?.()}
				>
					<Plus class="h-3 w-3" /> Create a scan engine
				</Button>
			</div>
		{:else}
			<div class="grid gap-3 sm:grid-cols-2">
				<div class="space-y-1.5">
					<Label for="{id}-engine" class="text-xs text-muted-foreground">Engine</Label>
					<Select.Root type="single" bind:value={engineId} {disabled}>
						<Select.Trigger id="{id}-engine" class="w-full">{engineLabel}</Select.Trigger>
						<Select.Content>
							{#each scanEnginesStore.engines as engine (engine.id)}
								<Select.Item value={engine.id} label={engine.name}>{engine.name}</Select.Item>
							{/each}
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
