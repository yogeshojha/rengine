<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ProjectNameForm from './project-name-form.svelte';
	import AlertCircleIcon from '@lucide/svelte/icons/alert-circle';
	import FolderPlusIcon from '@lucide/svelte/icons/folder-plus';

	let { open }: { open: boolean } = $props();

	let nameInput = $state<HTMLInputElement | null>(null);
</script>

<Dialog.Root {open} onOpenChange={() => {}}>
	<Dialog.Content
		showCloseButton={false}
		interactOutsideBehavior="ignore"
		escapeKeydownBehavior="ignore"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			nameInput?.focus();
		}}
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

		<ProjectNameForm bind:input={nameInput}>
			{#snippet actions({ submitting, valid })}
				<LoadingButton
					type="submit"
					class="w-full"
					loading={submitting}
					loadingLabel="Creating"
					disabled={!valid}
				>
					Create project
				</LoadingButton>
			{/snippet}
		</ProjectNameForm>
	</Dialog.Content>
</Dialog.Root>
