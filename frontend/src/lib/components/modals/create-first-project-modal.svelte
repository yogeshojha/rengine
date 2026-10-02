<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Spinner } from '$lib/components/ui/spinner';
	import { PROJECT_NAME_MAX } from '$lib/constants';
	import AlertCircleIcon from '@lucide/svelte/icons/alert-circle';
	import FolderPlusIcon from '@lucide/svelte/icons/folder-plus';
	import { tick } from 'svelte';

	let { open }: { open: boolean } = $props();

	let nameInput = $state<HTMLInputElement | null>(null);
	let name = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	let nameLength = $derived(name.length);
	let isValid = $derived(name.trim().length > 0 && name.length <= PROJECT_NAME_MAX);
	let isOverLimit = $derived(name.length > PROJECT_NAME_MAX);

	$effect(() => {
		if (open) {
			tick().then(() => nameInput?.focus());
		}
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!isValid || isSubmitting) return;

		isSubmitting = true;
		error = null;

		try {
			const newProject = await projectsStore.createProject(name.trim());

			if (newProject) {
				projectsStore.setActiveProject(newProject);
			} else {
				error = projectsStore.error || 'Project not created';
			}
		} finally {
			isSubmitting = false;
		}
	}
</script>

<Dialog.Root {open} onOpenChange={() => {}}>
	<Dialog.Content
		showCloseButton={false}
		interactOutsideBehavior="ignore"
		escapeKeydownBehavior="ignore"
		class="sm:max-w-md"
	>
		<Dialog.Header class="text-center sm:text-left">
			<div class="flex items-center gap-3">
				<div class="flex size-10 items-center justify-center rounded-full bg-primary/10">
					<FolderPlusIcon class="size-5 text-primary" />
				</div>
				<Dialog.Title class="leading-none">Create a project</Dialog.Title>
			</div>
		</Dialog.Header>

		<Alert.Root>
			<AlertCircleIcon class="size-4" />
			<Alert.Title>At least one project is required</Alert.Title>
		</Alert.Root>

		<form onsubmit={handleSubmit} class="space-y-4">
			<div class="space-y-2">
				<Label for="project-name">Project name</Label>
				<Input
					id="project-name"
					bind:ref={nameInput}
					bind:value={name}
					placeholder="Example Corp"
					disabled={isSubmitting}
					class={isOverLimit ? 'border-destructive focus-visible:ring-destructive' : ''}
				/>
				<div class="flex justify-between text-xs">
					{#if error}
						<span class="text-destructive">{error}</span>
					{:else if isOverLimit}
						<span class="text-destructive">Name is too long</span>
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

			<Button type="submit" class="w-full" disabled={!isValid || isSubmitting}>
				{#if isSubmitting}
					<Spinner class="mr-2 size-4" />
					Creating
				{:else}
					Create project
				{/if}
			</Button>
		</form>
	</Dialog.Content>
</Dialog.Root>
