<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { PROJECT_NAME_MAX } from '$lib/constants';

	let { open = $bindable(false) }: { open: boolean } = $props();

	let name = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	let nameLength = $derived(name.length);
	let isValid = $derived(name.trim().length > 0 && name.length <= PROJECT_NAME_MAX);
	let isOverLimit = $derived(name.length > PROJECT_NAME_MAX);

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!isValid || isSubmitting) return;

		isSubmitting = true;
		error = null;

		try {
			const newProject = await projectsStore.createProject(name.trim());

			if (newProject) {
				projectsStore.setActiveProject(newProject);
				resetForm();
				open = false;
			} else {
				error = projectsStore.error || 'Project not created';
			}
		} finally {
			isSubmitting = false;
		}
	}

	function resetForm() {
		name = '';
		error = null;
	}

	$effect(() => {
		if (!open) {
			resetForm();
		}
	});
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Create project</Dialog.Title>
		</Dialog.Header>

		<form onsubmit={handleSubmit} class="space-y-4">
			<div class="space-y-2">
				<Label for="project-name">Project name</Label>
				<Input
					id="project-name"
					bind:value={name}
					placeholder="Example Corp"
					disabled={isSubmitting}
					aria-invalid={isOverLimit || !!error}
				/>
				<div class="flex justify-between text-xs">
					{#if error}
						<span role="alert" class="text-destructive">{error}</span>
					{:else if isOverLimit}
						<span role="alert" class="text-destructive">Name is too long</span>
					{/if}
					<span
						class="ml-auto {nameLength > PROJECT_NAME_MAX
							? 'text-destructive'
							: 'text-muted-foreground'}"
					>
						{nameLength}/{PROJECT_NAME_MAX}
					</span>
				</div>
			</div>

			<Dialog.Footer>
				<Button
					type="button"
					variant="outline"
					onclick={() => (open = false)}
					disabled={isSubmitting}
				>
					Cancel
				</Button>
				<LoadingButton
					type="submit"
					loading={isSubmitting}
					loadingLabel="Creating"
					disabled={!isValid}
				>
					Create project
				</LoadingButton>
			</Dialog.Footer>
		</form>
	</Dialog.Content>
</Dialog.Root>
