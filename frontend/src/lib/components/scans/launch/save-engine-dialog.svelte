<script lang="ts">
	import { tick } from 'svelte';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { ScanEngine } from '$lib/types/scan-engine';
	import { diffStages } from '$lib/utilities/launch-plan';
	import type { LaunchState } from './launch-state.svelte';

	interface Props {
		open: boolean;
		launch: LaunchState;
		suggestedName: string;
		onSaved: (engine: ScanEngine) => void;
	}

	let { open = $bindable(), launch, suggestedName, onSaved }: Props = $props();

	let name = $state('');
	let description = $state('');
	let saving = $state(false);
	let nameEl = $state<HTMLInputElement | null>(null);

	$effect(() => {
		if (!open) return;
		name = suggestedName;
		description = '';
		tick().then(() => {
			nameEl?.focus();
			nameEl?.select();
		});
	});

	async function save() {
		const project = projectsStore.activeProject;
		const effective = launch.resolution?.effective;
		if (!project || !effective || !name.trim() || saving) return;
		saving = true;
		try {
			const created = await scanEnginesStore.createEngine(project.id, {
				name: name.trim(),
				description: description.trim() || null,
				intensity: launch.runIntensity,
				stages: diffStages(launch.defaults, effective)
			});
			if (created) {
				open = false;
				onSaved(created);
			}
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md" onkeydown={(e) => e.key === 'Enter' && e.stopPropagation()}>
		<Dialog.Header>
			<Dialog.Title>Save as scan engine</Dialog.Title>
			<Dialog.Description>
				Saves the selected stages and their settings as a scan engine that can be reused and
				scheduled.
			</Dialog.Description>
		</Dialog.Header>
		<div class="flex flex-col gap-4 py-1">
			<div class="flex flex-col gap-1.5">
				<Label for="save-engine-name">Name</Label>
				<Input
					id="save-engine-name"
					bind:ref={nameEl}
					bind:value={name}
					autocomplete="off"
					onkeydown={(e) => e.key === 'Enter' && save()}
				/>
			</div>
			<div class="flex flex-col gap-1.5">
				<Label for="save-engine-description">Description</Label>
				<Input
					id="save-engine-description"
					bind:value={description}
					placeholder="Optional"
					autocomplete="off"
					onkeydown={(e) => e.key === 'Enter' && save()}
				/>
			</div>
			{#if scanEnginesStore.error}
				<p class="text-xs text-destructive">{scanEnginesStore.error}</p>
			{/if}
		</div>
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (open = false)} disabled={saving}>Cancel</Button>
			<LoadingButton loading={saving} disabled={!name.trim()} onclick={save}>Save</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
