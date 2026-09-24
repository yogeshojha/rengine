<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import CapabilityPicker from './capability-picker.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { allowedKeys, type ChannelChat, type ChannelStatus } from '$lib/types/remote-control';

	interface Props {
		status: ChannelStatus;
		chat: ChannelChat | null;
		onOpenChange: (open: boolean) => void;
	}

	let { status, chat, onOpenChange }: Props = $props();

	let projectId = $state<string>('');
	const granted = new SvelteSet<string>();
	let saving = $state(false);

	const open = $derived(chat !== null);
	const projectList = $derived(projectsStore.projects ?? []);
	const projectLabel = $derived(
		projectList.find((p) => p.id === projectId)?.name ?? 'Select a project'
	);

	$effect(() => {
		if (!chat) return;
		projectId = chat.project_id ?? '';
		granted.clear();
		for (const key of chat.capabilities) granted.add(key);
	});

	async function save() {
		if (!chat) return;
		saving = true;
		const ok = await remoteControl.updateChat(chat.id, {
			project_id: projectId || undefined,
			capabilities: [...granted].filter((c) => allowedKeys(status).has(c))
		});
		saving = false;
		if (ok) onOpenChange(false);
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Edit chat</Dialog.Title>
			{#if chat}
				<Dialog.Description>
					{chat.display}
					{#if chat.username}
						· account {chat.username}
					{/if}
				</Dialog.Description>
			{/if}
		</Dialog.Header>

		<div class="flex flex-col gap-4">
			<FormField label="Project">
				{#snippet children({ id })}
					<Select.Root type="single" bind:value={projectId}>
						<Select.Trigger {id} class="w-full">{projectLabel}</Select.Trigger>
						<Select.Content>
							{#each projectList as project (project.id)}
								<Select.Item value={project.id} label={project.name}>{project.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>

			<CapabilityPicker {status} {granted} />
		</div>

		<div class="flex justify-end gap-2">
			<Button variant="ghost" onclick={() => onOpenChange(false)}>Cancel</Button>
			<LoadingButton loading={saving} loadingLabel="Saving" onclick={save}>Save</LoadingButton>
		</div>
	</Dialog.Content>
</Dialog.Root>
