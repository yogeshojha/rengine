<script lang="ts">
	import { Dialog as DialogPrimitive } from 'bits-ui';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import LoaderIcon from '@lucide/svelte/icons/loader';
	import AlertCircleIcon from '@lucide/svelte/icons/alert-circle';
	import FolderPlusIcon from '@lucide/svelte/icons/folder-plus';

	let { open }: { open: boolean } = $props();

	let name = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	const MAX_LENGTH = 80;
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
			} else {
				error = projectsStore.error || 'Failed to create project';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'An unexpected error occurred';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<DialogPrimitive.Root {open} onOpenChange={() => {}}>
	<DialogPrimitive.Portal>
		<DialogPrimitive.Overlay
			class="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/50"
		/>

		<DialogPrimitive.Content
			interactOutsideBehavior="ignore"
			class="bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border p-6 shadow-lg duration-200 sm:max-w-md"
		>
			<!-- Header -->
			<div class="flex flex-col gap-1.5 text-center sm:text-left">
				<div class="flex items-center gap-3">
					<div class="flex size-10 items-center justify-center rounded-full bg-primary/10">
						<FolderPlusIcon class="size-5 text-primary" />
					</div>
					<DialogPrimitive.Title class="text-lg font-semibold leading-none">
						Create Your First Project
					</DialogPrimitive.Title>
				</div>
				<DialogPrimitive.Description class="text-muted-foreground text-sm">
					Projects provide isolated workspaces for organizing targets, scans, and findings by engagement.
				</DialogPrimitive.Description>
			</div>

			<Alert.Root>
				<AlertCircleIcon class="size-4" />
				<Alert.Title>Project Required</Alert.Title>
				<Alert.Description>
					You need at least one project to start using reNgine.
				</Alert.Description>
			</Alert.Root>

			<form onsubmit={handleSubmit} class="space-y-4">
				<div class="space-y-2">
					<Label for="project-name">Project Name</Label>
					<Input
						id="project-name"
						bind:value={name}
						placeholder="e.g., Example Corp Pentest"
						disabled={isSubmitting}
						autofocus
						class={isOverLimit ? 'border-destructive focus-visible:ring-destructive' : ''}
					/>
					<div class="flex justify-between text-xs">
						{#if error}
							<span class="text-destructive">{error}</span>
						{:else if isOverLimit}
							<span class="text-destructive">Name is too long</span>
						{:else}
							<span class="text-muted-foreground">Choose a descriptive name for your engagement</span>
						{/if}
						<span class={nameLength > MAX_LENGTH ? 'text-destructive' : 'text-muted-foreground'}>
							{nameLength}/{MAX_LENGTH}
						</span>
					</div>
				</div>

				<Button type="submit" class="w-full" disabled={!isValid || isSubmitting}>
					{#if isSubmitting}
						<LoaderIcon class="mr-2 size-4 animate-spin" />
						Creating Project...
					{:else}
						Create Project & Get Started
					{/if}
				</Button>
			</form>
		</DialogPrimitive.Content>
	</DialogPrimitive.Portal>
</DialogPrimitive.Root>
