<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import CapabilityPicker from './capability-picker.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { usersApi, type UserAccount } from '$lib/api/users';
	import { SvelteSet } from 'svelte/reactivity';
	import { untrack } from 'svelte';
	import { MCP_DEFAULT_GRANTS, type McpCapability } from '$lib/types/mcp';
	import { allowedKeys, type ChannelStatus, type PairingRequest } from '$lib/types/remote-control';

	interface Props {
		status: ChannelStatus;
		request: PairingRequest | null;
		onOpenChange: (open: boolean) => void;
	}

	let { status, request, onOpenChange }: Props = $props();

	let accounts = $state<UserAccount[]>([]);
	let userId = $state<string>('');
	let projectId = $state<string>('');
	const granted = new SvelteSet<string>(MCP_DEFAULT_GRANTS);
	let approving = $state(false);

	const open = $derived(request !== null);
	const projectList = $derived(projectsStore.projects ?? []);
	const account = $derived(accounts.find((a) => a.id === userId) ?? null);
	const accountLabel = $derived(account?.username ?? 'Select an account');
	const projectLabel = $derived(
		projectList.find((p) => p.id === projectId)?.name ?? 'Select a project'
	);
	const aboveRead = $derived([...granted].some((c) => c !== 'read'));

	$effect(() => {
		if (!open) return;
		userId = auth.user?.id ?? '';
		projectId = projectsStore.activeProject?.id ?? '';
		const allowed = untrack(() => allowedKeys(status));
		granted.clear();
		for (const key of MCP_DEFAULT_GRANTS) if (allowed.has(key)) granted.add(key);
		void usersApi
			.list()
			.then((rows) => (accounts = rows.filter((r) => r.is_active)))
			.catch(() => (accounts = []));
	});

	async function approve() {
		if (!request || !userId || !projectId) return;
		approving = true;
		const chat = await remoteControl.approve(request.code, {
			user_id: userId,
			project_id: projectId,
			capabilities: [...granted].filter((c) => allowedKeys(status).has(c)) as McpCapability[]
		});
		approving = false;
		if (chat) onOpenChange(false);
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Approve pairing</Dialog.Title>
			{#if request}
				<Dialog.Description>
					{request.display}
					<span class="font-mono text-xs">{request.external_id}</span>
				</Dialog.Description>
			{/if}
		</Dialog.Header>

		<div class="flex flex-col gap-4">
			<FormField label="Account" description="The chat acts as this account">
				{#snippet children({ id })}
					<Select.Root type="single" bind:value={userId}>
						<Select.Trigger {id} class="w-full">{accountLabel}</Select.Trigger>
						<Select.Content>
							{#each accounts as row (row.id)}
								<Select.Item value={row.id} label={row.username}>
									<span class="flex items-center gap-2">
										{row.username}
										{#if !row.totp_enabled}
											<span class="text-2xs text-muted-foreground">no authenticator</span>
										{/if}
									</span>
								</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>

			<FormField label="Project" description="Switched from the chat with /project">
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

			{#if account && !account.totp_enabled && aboveRead}
				<div
					class="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/6 px-3 py-2.5 text-xs"
				>
					<Badge variant="warning" class="shrink-0 text-2xs">Read only</Badge>
					<span>
						{account.username} has no authenticator enrolled. Capabilities above read apply once one is
						enrolled.
					</span>
				</div>
			{/if}
		</div>

		<div class="flex justify-end gap-2">
			<Button variant="ghost" onclick={() => onOpenChange(false)}>Cancel</Button>
			<LoadingButton
				loading={approving}
				loadingLabel="Approving"
				disabled={!userId || !projectId}
				onclick={approve}
			>
				Approve
			</LoadingButton>
		</div>
	</Dialog.Content>
</Dialog.Root>
