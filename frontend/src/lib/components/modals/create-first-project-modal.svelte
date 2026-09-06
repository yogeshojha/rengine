<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Spinner } from '$lib/components/ui/spinner';
	import AlertCircleIcon from '@lucide/svelte/icons/alert-circle';
	import FolderPlusIcon from '@lucide/svelte/icons/folder-plus';
	import { tick } from 'svelte';

	let { open }: { open: boolean } = $props();

	let nameInput = $state<HTMLInputElement | null>(null);
	let name = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	const MAX_LENGTH = 80;
	let nameLength = $derived(name.length);
	let isValid = $derived(name.trim().length > 0 && name.length <= MAX_LENGTH);
	let isOverLimit = $derived(name.length > MAX_LENGTH);

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
				error = projectsStore.error || 'Project could not be created';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'An unexpected error occurred';
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
				<Dialog.Title class="leading-none">Create your first project</Dialog.Title>
			</div>
			<Dialog.Description>
				A project keeps its targets, scans and findings separate.
			</Dialog.Description>
		</Dialog.Header>

		<Alert.Root>
			<AlertCircleIcon class="size-4" />
			<Alert.Title>Project required</Alert.Title>
			<Alert.Description>At least one project is required.</Alert.Description>
		</Alert.Root>

		<form onsubmit={handleSubmit} class="space-y-4">
			<div class="space-y-2">
				<Label for="project-name">Project name</Label>
				<Input
					id="project-name"
					bind:ref={nameInput}
					bind:value={name}
					placeholder="e.g. Example Corp Pentest"
					disabled={isSubmitting}
					class={isOverLimit ? 'border-destructive focus-visible:ring-destructive' : ''}
				/>
				<div class="flex justify-between text-xs">
					{#if error}
						<span class="text-destructive">{error}</span>
					{:else if isOverLimit}
						<span class="text-destructive">Name is too long</span>
					{:else}
						<span class="text-muted-foreground">Name this engagement</span>
					{/if}
					<span class={nameLength > MAX_LENGTH ? 'text-destructive' : 'text-muted-foreground'}>
						{nameLength}/{MAX_LENGTH}
					</span>
				</div>
			</div>

			<Button type="submit" class="w-full" disabled={!isValid || isSubmitting}>
				{#if isSubmitting}
					<Spinner class="mr-2 size-4" />
					Creating project…
				{:else}
					Create project
				{/if}
			</Button>
		</form>
	</Dialog.Content>
</Dialog.Root>
