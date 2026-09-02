<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '@/components/loading-button.svelte';
	import StageList from './stage-list.svelte';
	import FootprintMeter from './footprint-meter.svelte';
	import { summarize } from '$lib/utilities/engine-summary';
	import type { EnginePreset, StageCatalogEntry } from '$lib/types/scan-engine';

	interface Props {
		open: boolean;
		presets: EnginePreset[];
		stages: StageCatalogEntry[];
		isCreating: boolean;
		initialPreset?: string | null;
		onOpenChange: (open: boolean) => void;
		onCreate: (name: string, preset: EnginePreset) => void;
	}

	let {
		open,
		presets,
		stages,
		isCreating,
		initialPreset = null,
		onOpenChange,
		onCreate
	}: Props = $props();

	let name = $state('');
	let selected = $state('');

	$effect(() => {
		if (open) {
			name = '';
			selected = initialPreset ?? presets[0]?.name ?? '';
		}
	});

	const preset = $derived(presets.find((p) => p.name === selected));
	const canCreate = $derived(name.trim().length > 0 && preset !== undefined);

	function submit() {
		if (!canCreate || !preset) return;
		onCreate(name.trim(), preset);
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="sm:max-w-xl">
		<Dialog.Header>
			<Dialog.Title>New scan engine</Dialog.Title>
			<Dialog.Description>
				Choose a preset to start from. Every stage and setting can be changed later.
			</Dialog.Description>
		</Dialog.Header>

		<div class="space-y-4 py-1">
			<div class="space-y-1.5">
				<Label for="engine-name">Name</Label>
				<Input
					id="engine-name"
					bind:value={name}
					placeholder={preset ? `e.g. ${preset.title}` : 'e.g. Deep Recon'}
					autocomplete="off"
					onkeydown={(e) => e.key === 'Enter' && submit()}
				/>
			</div>

			<RadioGroup.Root bind:value={selected} class="grid gap-2 sm:grid-cols-2">
				{#each presets as p (p.name)}
					{@const summary = summarize(p.stages, stages, 'normal')}
					<Label
						for="preset-{p.name}"
						class="flex cursor-pointer flex-col gap-2.5 rounded-lg border border-border p-3 transition-colors hover:bg-muted/40 has-[[data-state=checked]]:border-primary/50 has-[[data-state=checked]]:bg-primary/5"
					>
						<span class="flex items-start gap-2.5">
							<RadioGroup.Item value={p.name} id="preset-{p.name}" class="mt-0.5" />
							<span class="flex min-w-0 flex-col gap-0.5">
								<span class="text-sm font-medium">{p.title}</span>
								<span class="text-xs font-normal text-muted-foreground">{p.description}</span>
							</span>
						</span>
						<span class="flex flex-col gap-1.5 pl-6">
							<StageList {stages} config={p.stages} variant="inline" max={4} />
							<span class="flex items-center justify-between gap-2 text-[11px] font-normal">
								<span class="text-muted-foreground tabular-nums">
									{summary.activeStages} of {summary.totalStages} stages
								</span>
								<FootprintMeter
									footprint={summary.footprint}
									requestsPerSecond={summary.requestsPerSecond}
									class="text-[11px]"
								/>
							</span>
						</span>
					</Label>
				{/each}
			</RadioGroup.Root>
		</div>

		<Dialog.Footer>
			<Button variant="outline" onclick={() => onOpenChange(false)}>Cancel</Button>
			<LoadingButton loading={isCreating} disabled={!canCreate} onclick={submit}>
				Create engine
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
