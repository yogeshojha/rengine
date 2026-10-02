<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import LadderPick from '$lib/components/access/ladder-pick.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ceilingKeys, ladderLevel, regrant } from '$lib/types/mcp';
	import type { ChannelChat, ChannelStatus } from '$lib/types/remote-control';

	interface Props {
		status: ChannelStatus;
		chat: ChannelChat | null;
		onOpenChange: (open: boolean) => void;
	}

	let { status, chat, onOpenChange }: Props = $props();

	let projectId = $state('');
	let level = $state(0);
	let saving = $state(false);

	const open = $derived(chat !== null);
	const allowed = $derived(ceilingKeys(status));
	const projects = $derived(projectsStore.projects ?? []);

	$effect(() => {
		if (!chat) return;
		projectId = chat.project_id ?? '';
		level = ladderLevel(chat.capabilities);
	});

	async function save() {
		if (!chat) return;
		saving = true;
		const ok = await remoteControl.updateChat(chat.id, {
			project_id: projectId || undefined,
			capabilities: regrant(level, chat.capabilities, allowed)
		});
		saving = false;
		if (ok) onOpenChange(false);
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Edit chat</Dialog.Title>
			{#if chat}
				<Dialog.Description>
					{chat.display}{chat.username ? ` · ${chat.username}` : ''}
				</Dialog.Description>
			{/if}
		</Dialog.Header>

		<div class="flex flex-col gap-4">
			<FormField label="Project">
				{#snippet children({ id })}
					<Select.Root type="single" bind:value={projectId}>
						<Select.Trigger {id} class="w-full">
							{projects.find((p) => p.id === projectId)?.name ?? 'Select a project'}
						</Select.Trigger>
						<Select.Content>
							{#each projects as project (project.id)}
								<Select.Item value={project.id} label={project.name}>{project.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>
			<div class="flex flex-col gap-2">
				<span class="text-sm font-medium">Capabilities</span>
				<LadderPick {level} {allowed} onChange={(v) => (level = v)} />
			</div>
		</div>

		<div class="flex justify-end gap-2">
			<Button variant="ghost" onclick={() => onOpenChange(false)}>Cancel</Button>
			<LoadingButton loading={saving} loadingLabel="Saving" onclick={save}>Save</LoadingButton>
		</div>
	</Dialog.Content>
</Dialog.Root>
