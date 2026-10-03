<script lang="ts">
	import { untrack } from 'svelte';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import StageList from './stage-list.svelte';
	import FootprintMeter from './footprint-meter.svelte';
	import { summarize } from '$lib/utilities/engine-summary';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import type { EnginePreset, StageCatalogEntry } from '$lib/types/scan-engine';

	interface Props {
		open: boolean;
		presets: EnginePreset[];
		stages: StageCatalogEntry[];
		isCreating: boolean;
		onOpenChange: (open: boolean) => void;
		onCreate: (name: string, preset: EnginePreset) => void;
	}

	let { open, presets, stages, isCreating, onOpenChange, onCreate }: Props = $props();

	let name = $state('');
	let selected = $state('');

	$effect(() => {
		if (!open) return;
		untrack(() => {
			name = '';
			selected = presets[0]?.name ?? '';
		});
	});

	$effect(() => {
		const first = presets[0]?.name;
		if (!open || !first) return;
		untrack(() => {
			if (!selected) selected = first;
		});
	});

	const preset = $derived(presets.find((p) => p.name === selected));
	const canCreate = $derived(name.trim().length > 0 && preset !== undefined);
	const dirty = $derived(
		name.trim() !== '' || (selected !== '' && selected !== (presets[0]?.name ?? ''))
	);
	const guard = new DiscardGuard(
		() => dirty,
		() => onOpenChange(false)
	);

	function submit() {
		if (!canCreate || !preset || isCreating) return;
		onCreate(name.trim(), preset);
	}

	function requestOpen(next: boolean) {
		if (next) onOpenChange(true);
		else if (!isCreating) guard.close();
	}
</script>

<Dialog.Root bind:open={() => open, requestOpen}>
	<Dialog.Content class="sm:max-w-xl">
		<Dialog.Header>
			<Dialog.Title>New engine</Dialog.Title>
		</Dialog.Header>

		<div class="flex flex-col gap-4 py-1">
			<FormField label="Name">
				{#snippet children({ id })}
					<Input
						{id}
						bind:value={name}
						placeholder="Engine name"
						autocomplete="off"
						onkeydown={(e) => e.key === 'Enter' && submit()}
					/>
				{/snippet}
			</FormField>

			<RadioGroup.Root bind:value={selected} class="grid gap-2 sm:grid-cols-2">
				{#each presets as p (p.name)}
					{@const summary = summarize(p.stages, stages, p.intensity)}
					<Label
						for="preset-{p.name}"
						class="flex cursor-pointer flex-col items-stretch gap-2.5 rounded-lg border border-border p-3 transition-colors hover:bg-muted/40 has-[[data-state=checked]]:border-primary/50 has-[[data-state=checked]]:bg-primary/5"
					>
						<span class="flex items-start gap-2.5">
							<RadioGroup.Item value={p.name} id="preset-{p.name}" class="mt-0.5" />
							<span class="flex min-w-0 flex-col gap-0.5">
								<span class="text-sm font-medium">{p.title}</span>
								<span class="text-xs font-normal text-muted-foreground">{p.description}</span>
							</span>
						</span>
						<span class="flex flex-col gap-1.5 pl-6">
							<StageList
								{stages}
								config={p.stages}
								intensity={p.intensity}
								variant="inline"
								max={4}
							/>
							<span class="flex items-center justify-between gap-2 text-2xs font-normal">
								<span class="text-muted-foreground tabular-nums">
									{summary.activeStages} of {summary.totalStages} stages
								</span>
								<FootprintMeter
									footprint={summary.footprint}
									requestsPerSecond={summary.requestsPerSecond}
									class="text-2xs"
								/>
							</span>
						</span>
					</Label>
				{/each}
			</RadioGroup.Root>
		</div>

		<Dialog.Footer>
			<Button variant="outline" disabled={isCreating} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton
				loading={isCreating}
				loadingLabel="Creating"
				disabled={!canCreate}
				onclick={submit}
			>
				Create engine
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
