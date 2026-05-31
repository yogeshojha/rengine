<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { LoaderCircle, Rocket } from 'lucide-svelte';

	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import { Separator } from '$lib/components/ui/separator';
	import ExecutionPreview from './execution-preview.svelte';

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansApi } from '$lib/api/scans';
	import { targetsApi } from '$lib/api/targets';
	import type { Target } from '$lib/types/target';
	import type { ScanPreview } from '$lib/types/scan';

	interface Props {
		open: boolean;
		targetId?: string;
		onClose?: () => void;
	}

	let { open = $bindable(), targetId, onClose }: Props = $props();

	const NONE_CONTEXT = '__none__';

	let engineId = $state<string>('');
	let contextId = $state<string>(NONE_CONTEXT);
	let selectedTargetId = $state<string>('');

	let targets = $state<Target[]>([]);
	let preview = $state<ScanPreview | null>(null);
	let previewLoading = $state(false);
	let launching = $state(false);

	let previewDebounce: ReturnType<typeof setTimeout>;
	let previewSeq = 0;

	let engineLabel = $derived(
		scanEnginesStore.engines.find((e) => e.id === engineId)?.name ?? 'Select engine'
	);
	let contextLabel = $derived(
		contextId === NONE_CONTEXT
			? 'None — engine defaults'
			: (scanContextsStore.contexts.find((c) => c.id === contextId)?.name ?? 'Select context')
	);
	let targetLabel = $derived(
		targets.find((t) => t.id === selectedTargetId)?.target_value ?? 'Select target'
	);

	let canLaunch = $derived(!!engineId && !!selectedTargetId && !launching);

	$effect(() => {
		if (!open) return;
		const project = projectsStore.activeProject;
		if (!project) return;
		untrack(() => {
			if (!scanEnginesStore.hasFetched) scanEnginesStore.fetchEngines(project.id);
			if (!scanContextsStore.hasFetched) scanContextsStore.fetchContexts(project.id);
			loadTargets(project.slug);
			if (targetId) selectedTargetId = targetId;
		});
	});

	async function loadTargets(projectSlug: string) {
		try {
			const res = await targetsApi.list({ project_slug: projectSlug, size: 100 });
			targets = res.items;
		} catch {
			toast.error('Failed to load targets');
		}
	}

	// Debounced preview on any selection change.
	$effect(() => {
		const eng = engineId;
		const ctx = contextId;
		const tgt = selectedTargetId;
		const project = projectsStore.activeProject;

		clearTimeout(previewDebounce);
		if (!eng || !tgt || !project) {
			preview = null;
			previewLoading = false;
			return;
		}

		previewLoading = true;
		const seq = ++previewSeq;
		previewDebounce = setTimeout(async () => {
			try {
				const result = await scansApi.preview(project.id, {
					engine_id: eng,
					context_id: ctx === NONE_CONTEXT ? null : ctx,
					target_id: tgt
				});
				if (seq === previewSeq) preview = result;
			} catch (e) {
				if (seq === previewSeq) {
					preview = null;
					toast.error(e instanceof Error ? e.message : 'Failed to preview scan');
				}
			} finally {
				if (seq === previewSeq) previewLoading = false;
			}
		}, 350);
	});

	async function handleLaunch() {
		const project = projectsStore.activeProject;
		if (!project || !engineId || !selectedTargetId) return;
		launching = true;
		try {
			const created = await scansStore.launchScan(project.id, {
				engine_id: engineId,
				context_id: contextId === NONE_CONTEXT ? null : contextId,
				target_id: selectedTargetId
			});
			if (created) {
				toast.success('Scan launched — config recorded');
				handleOpenChange(false);
				goto('/automation/scans');
			} else {
				toast.error(scansStore.error ?? 'Failed to launch scan');
			}
		} finally {
			launching = false;
		}
	}

	function reset() {
		engineId = '';
		contextId = NONE_CONTEXT;
		selectedTargetId = '';
		preview = null;
		previewLoading = false;
		clearTimeout(previewDebounce);
	}

	function handleOpenChange(isOpen: boolean) {
		open = isOpen;
		if (!isOpen) {
			reset();
			onClose?.();
		}
	}
</script>

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content class="max-h-[90vh] gap-0 overflow-hidden p-0 sm:max-w-[760px]">
		<Dialog.Header class="p-6 pb-4">
			<Dialog.Title>New Scan</Dialog.Title>
			<Dialog.Description>
				Combine a scan engine with an optional context, preview the resolved plan, then launch.
			</Dialog.Description>
		</Dialog.Header>

		<Separator />

		<div class="grid max-h-[60vh] grid-cols-1 gap-0 overflow-hidden md:grid-cols-2">
			<!-- Selections -->
			<div class="space-y-4 overflow-y-auto p-6">
				<div class="space-y-2">
					<Label for="scan-engine-select">Engine <span class="text-destructive">*</span></Label>
					<Select.Root type="single" bind:value={engineId}>
						<Select.Trigger id="scan-engine-select" class="w-full">{engineLabel}</Select.Trigger>
						<Select.Content>
							{#each scanEnginesStore.engines as engine (engine.id)}
								<Select.Item value={engine.id} label={engine.name}>{engine.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>

				<div class="space-y-2">
					<Label for="scan-context-select">Context</Label>
					<Select.Root type="single" bind:value={contextId}>
						<Select.Trigger id="scan-context-select" class="w-full">{contextLabel}</Select.Trigger>
						<Select.Content>
							<Select.Item value={NONE_CONTEXT} label="None — engine defaults">
								None — engine defaults
							</Select.Item>
							{#each scanContextsStore.contexts as context (context.id)}
								<Select.Item value={context.id} label={context.name}>{context.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>

				<div class="space-y-2">
					<Label for="scan-target-select">Target <span class="text-destructive">*</span></Label>
					<Select.Root type="single" bind:value={selectedTargetId}>
						<Select.Trigger id="scan-target-select" class="w-full">{targetLabel}</Select.Trigger>
						<Select.Content>
							{#each targets as target (target.id)}
								<Select.Item value={target.id} label={target.target_value}>
									{target.target_value}
								</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				</div>
			</div>

			<!-- Preview -->
			<div class="overflow-y-auto border-t bg-muted/20 p-6 md:border-t-0 md:border-l">
				<ExecutionPreview {preview} loading={previewLoading} />
			</div>
		</div>

		<Separator />

		<div class="flex items-center justify-end gap-2 bg-muted/30 p-4">
			<Button variant="outline" onclick={() => handleOpenChange(false)} disabled={launching}>
				Cancel
			</Button>
			<Button onclick={handleLaunch} disabled={!canLaunch} class="gap-2">
				{#if launching}
					<LoaderCircle class="h-4 w-4 animate-spin" />
					Launching...
				{:else}
					<Rocket class="h-4 w-4" />
					Launch Scan
				{/if}
			</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>
