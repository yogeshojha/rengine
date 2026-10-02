<script lang="ts">
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import LadderPick from '$lib/components/access/ladder-pick.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import type { UserAccount } from '$lib/api/users';
	import { MCP_DEFAULT_GRANTS, ceilingKeys, grantsUpTo, ladderLevel } from '$lib/types/mcp';
	import { relativeTime } from '$lib/utilities/dates';
	import type { ChannelStatus, PairingRequest } from '$lib/types/remote-control';

	interface Props {
		request: PairingRequest;
		status: ChannelStatus;
		accounts: UserAccount[];
		now: number;
		onBlock: (request: PairingRequest) => void;
	}

	let { request, status, accounts, now, onBlock }: Props = $props();

	let userId = $state(auth.user?.id ?? '');
	let projectId = $state(projectsStore.activeProject?.id ?? '');
	let level = $state(ladderLevel(MCP_DEFAULT_GRANTS));
	let approving = $state(false);

	const allowed = $derived(ceilingKeys(status));
	const projects = $derived(projectsStore.projects ?? []);
	const account = $derived(accounts.find((a) => a.id === userId) ?? null);
	const chars = $derived([...request.code]);
	const left = $derived(Math.max(0, new Date(request.expires_at).getTime() - now));
	const span = $derived(
		new Date(request.expires_at).getTime() - new Date(request.requested_at).getTime()
	);
	const clock = $derived(
		`${Math.floor(left / 60_000)}:${String(Math.floor((left % 60_000) / 1000)).padStart(2, '0')}`
	);

	async function approve() {
		if (!userId || !projectId) return;
		approving = true;
		await remoteControl.approve(request.code, {
			user_id: userId,
			project_id: projectId,
			capabilities: grantsUpTo(level, allowed)
		});
		approving = false;
	}
</script>

<div
	class="grid gap-4 border-b border-warning/30 bg-warning/5 px-4 py-4 md:grid-cols-[minmax(0,1fr)_auto]"
>
	<div class="flex min-w-0 flex-col gap-3">
		<div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
			<span class="text-sm font-medium">{request.display}</span>
			<span class="text-xs text-muted-foreground"
				>requests pairing · {relativeTime(request.requested_at)}</span
			>
		</div>

		<div class="flex flex-wrap items-center gap-x-5 gap-y-2">
			<div class="flex items-center gap-1" aria-label="Pairing code {request.code}">
				{#each chars as ch, i (i)}
					{#if ch === '-'}
						<span class="w-2 text-center text-muted-foreground">–</span>
					{:else}
						<span
							class="grid h-9 w-7 place-items-center rounded-md border border-warning/30 bg-card font-mono text-lg font-semibold"
							>{ch}</span
						>
					{/if}
				{/each}
			</div>
			<div class="flex w-36 flex-col gap-1">
				<div class="h-1 overflow-hidden rounded-full bg-warning/15">
					<div
						class="h-full rounded-full bg-warning transition-[width] duration-1000 ease-linear motion-reduce:transition-none"
						style="width: {span > 0 ? (left / span) * 100 : 0}%"
					></div>
				</div>
				<span class="font-mono text-2xs text-muted-foreground tabular-nums">
					{left ? `expires in ${clock}` : 'expired'}
				</span>
			</div>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<Select.Root type="single" bind:value={userId}>
				<Select.Trigger class="h-8 w-44" aria-label="Account">
					{account?.username ?? 'Account'}
				</Select.Trigger>
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
			<Select.Root type="single" bind:value={projectId}>
				<Select.Trigger class="h-8 w-44" aria-label="Project">
					{projects.find((p) => p.id === projectId)?.name ?? 'Project'}
				</Select.Trigger>
				<Select.Content>
					{#each projects as project (project.id)}
						<Select.Item value={project.id} label={project.name}>{project.name}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			<LadderPick {level} {allowed} onChange={(v) => (level = v)} />
		</div>
		{#if account && !account.totp_enabled && level > 0}
			<span class="text-xs text-warning">
				Read only until {account.username} enrols an authenticator.
			</span>
		{/if}
	</div>

	<div class="flex items-end justify-end gap-2">
		<Button variant="ghost" size="sm" onclick={() => onBlock(request)}>Block</Button>
		<LoadingButton
			size="sm"
			loading={approving}
			loadingLabel="Approving"
			disabled={!userId || !projectId || !left}
			onclick={approve}
		>
			Approve
		</LoadingButton>
	</div>
</div>
