<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Spinner } from '$lib/components/ui/spinner';

	let { open = $bindable(false) }: { open: boolean } = $props();

	let name = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	const MAX_LENGTH = 50;
	let nameLength = $derived(name.length);
	let isValid = $derived(name.trim().length > 0 && name.length <= MAX_LENGTH);
	let isOverLimit = $derived(name.length > MAX_LENGTH);

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
				error = projectsStore.error || 'Failed to create project';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'An unexpected error occurred';
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
			<Dialog.Title>Create New Project</Dialog.Title>
			<Dialog.Description>
				Projects provide isolated workspaces for organizing targets, scans, and findings by
				engagement.
			</Dialog.Description>
		</Dialog.Header>

		<form onsubmit={handleSubmit} class="space-y-4">
			<div class="space-y-2">
				<Label for="project-name">Project Name</Label>
				<Input
					id="project-name"
					bind:value={name}
					placeholder="e.g., Example Corp Pentest"
					disabled={isSubmitting}
					class={isOverLimit ? 'border-destructive focus-visible:ring-destructive' : ''}
				/>
				<div class="flex justify-between text-xs">
					{#if error}
						<span class="text-destructive">{error}</span>
					{:else if isOverLimit}
						<span class="text-destructive">Name is too long</span>
					{:else}
						<span class="text-muted-foreground">A URL-friendly slug will be auto-generated</span>
					{/if}
					<span class={nameLength > MAX_LENGTH ? 'text-destructive' : 'text-muted-foreground'}>
						{nameLength}/{MAX_LENGTH}
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
				<Button type="submit" disabled={!isValid || isSubmitting}>
					{#if isSubmitting}
						<Spinner class="mr-2 size-4" />
						Creating...
					{:else}
						Create Project
					{/if}
				</Button>
			</Dialog.Footer>
		</form>
	</Dialog.Content>
</Dialog.Root>
