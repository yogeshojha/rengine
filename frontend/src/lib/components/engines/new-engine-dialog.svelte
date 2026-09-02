<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import * as RadioGroup from '$lib/components/ui/radio-group';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '@/components/loading-button.svelte';
	import type { EnginePreset } from '$lib/types/scan-engine';

	interface Props {
		open: boolean;
		presets: EnginePreset[];
		isCreating: boolean;
		onOpenChange: (open: boolean) => void;
		onCreate: (name: string, preset: EnginePreset) => void;
	}

	let { open, presets, isCreating, onOpenChange, onCreate }: Props = $props();

	let name = $state('');
	let selected = $state('');

	$effect(() => {
		if (open) {
			name = '';
			selected = presets[0]?.name ?? '';
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
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>New scan engine</Dialog.Title>
			<Dialog.Description>Pick a starting point — you can change anything after.</Dialog.Description
			>
		</Dialog.Header>

		<div class="space-y-4 py-1">
			<div class="space-y-1.5">
				<Label for="engine-name">Name</Label>
				<Input
					id="engine-name"
					bind:value={name}
					placeholder="e.g. Deep Recon"
					autocomplete="off"
					onkeydown={(e) => e.key === 'Enter' && submit()}
				/>
			</div>

			<RadioGroup.Root bind:value={selected} class="gap-2">
				{#each presets as p (p.name)}
					<Label
						for="preset-{p.name}"
						class="flex cursor-pointer items-start gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-muted/40 has-[[data-state=checked]]:border-foreground/25 has-[[data-state=checked]]:bg-muted/50"
					>
						<RadioGroup.Item value={p.name} id="preset-{p.name}" class="mt-0.5" />
						<span class="flex flex-col gap-0.5">
							<span class="text-sm font-medium">{p.title}</span>
							<span class="text-xs font-normal text-muted-foreground">{p.description}</span>
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
