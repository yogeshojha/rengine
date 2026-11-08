<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { PROJECT_NAME_MAX } from '$lib/constants';

	interface Props {
		input?: HTMLInputElement | null;
		oncreated?: () => void;
		actions: Snippet<[{ submitting: boolean; valid: boolean }]>;
	}

	let { input = $bindable(null), oncreated, actions }: Props = $props();

	let name = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

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
				name = '';
				oncreated?.();
			} else {
				error = projectsStore.error || 'Project not created';
			}
		} finally {
			isSubmitting = false;
		}
	}
</script>

<form onsubmit={handleSubmit} class="space-y-4">
	<div class="space-y-2">
		<Label for="project-name">Project name</Label>
		<Input
			id="project-name"
			bind:ref={input}
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
			<span class="ml-auto {isOverLimit ? 'text-destructive' : 'text-muted-foreground'}">
				{name.length}/{PROJECT_NAME_MAX}
			</span>
		</div>
	</div>

	{@render actions({ submitting: isSubmitting, valid: isValid })}
</form>
