<script lang="ts">
	import { untrack } from 'svelte';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Select from '$lib/components/ui/select';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import CodeBlock from '$lib/components/code-block.svelte';
	import LadderPick from '$lib/components/access/ladder-pick.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { SELECT_NONE } from '$lib/constants';
	import { CONNECT_POLL_MS, callsOf, parseClient } from '$lib/utilities/mcp';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import {
		MCP_CAPABILITIES,
		MCP_DEFAULT_GRANTS,
		MCP_EXPIRY_CHOICES,
		ceilingKeys,
		grantsUpTo,
		ladderLevel,
		regrant,
		type McpStatus,
		type McpToken,
		type McpTokenCreated
	} from '$lib/types/mcp';
	import type { CodeLang } from '$lib/utilities/code-highlight';

	interface Props {
		open: boolean;
		status: McpStatus;
		editing: McpToken | null;
		titles: Map<string, string>;
	}

	let { open = $bindable(), status, editing, titles }: Props = $props();

	const DEFAULT_EXPIRY = '30';
	const DEFAULT_LEVEL = ladderLevel(MCP_DEFAULT_GRANTS);

	let client = $state('');
	let name = $state('');
	let named = $state(false);
	let projectId = $state<string>(SELECT_NONE);
	let level = $state(DEFAULT_LEVEL);
	let expiry = $state(DEFAULT_EXPIRY);
	let saving = $state(false);
	let created = $state<McpTokenCreated | null>(null);
	let shownClient = $state('');

	const allowed = $derived(ceilingKeys(status));
	const defaultClient = $derived(status.clients[0]?.key ?? '');
	const clientsId = $props.id();
	const projects = $derived(projectsStore.projects ?? []);
	const projectLabel = $derived(
		projectId === SELECT_NONE
			? 'Every project'
			: (projects.find((p) => p.id === projectId)?.name ?? 'Select a project')
	);
	const expiryLabel = $derived(
		MCP_EXPIRY_CHOICES.find((c) => String(c.value ?? 'never') === expiry)?.label ?? ''
	);
	const top = $derived(status.capabilities.find((c) => c.key === MCP_CAPABILITIES[level]));
	const touches = $derived(
		status.capabilities.some((c) => c.touches_targets && grantsUpTo(level, allowed).includes(c.key))
	);

	const live = $derived(created ? mcp.tokens.find((t) => t.id === created!.token.id) : null);
	const connectedClient = $derived(
		live?.last_used_at && live.last_client ? parseClient(live.last_client) : null
	);
	const firstCall = $derived.by(() => {
		if (!live) return null;
		const own = callsOf(mcp.calls, live);
		return own.length ? own[own.length - 1] : null;
	});
	const snippet = $derived(created?.clients.find((c) => c.key === shownClient) ?? null);
	const dirty = $derived.by(() => {
		if (created) return false;
		if (editing) {
			return (
				projectId !== (editing.project_id ?? SELECT_NONE) ||
				level !== ladderLevel(editing.capabilities)
			);
		}
		return (
			client !== defaultClient ||
			name.trim() !== defaultClient.replaceAll('_', '-') ||
			projectId !== SELECT_NONE ||
			level !== DEFAULT_LEVEL ||
			expiry !== DEFAULT_EXPIRY
		);
	});
	const guard = new DiscardGuard(() => dirty, close);

	$effect(() => {
		if (!open || editing || created) return;
		const first = defaultClient;
		untrack(() => {
			if (!client && !named && first) pickClient(first);
		});
	});

	$effect(() => {
		if (!open) return;
		if (editing) {
			projectId = editing.project_id ?? SELECT_NONE;
			level = ladderLevel(editing.capabilities);
		}
	});

	$effect(() => {
		if (!open || !created || connectedClient) return;
		const id = setInterval(() => {
			void mcp.loadTokens(true);
			void mcp.loadCalls(true);
		}, CONNECT_POLL_MS);
		return () => clearInterval(id);
	});

	function pickClient(key: string) {
		client = key;
		if (!named) name = key.replaceAll('_', '-');
	}

	function reset() {
		client = '';
		name = '';
		named = false;
		projectId = SELECT_NONE;
		level = DEFAULT_LEVEL;
		expiry = DEFAULT_EXPIRY;
		created = null;
		shownClient = '';
	}

	function close() {
		open = false;
		reset();
	}

	async function submit() {
		saving = true;
		const project = projectId === SELECT_NONE ? null : projectId;
		if (editing) {
			const ok = await mcp.updateToken(editing.id, {
				project_id: project,
				capabilities: regrant(level, editing.capabilities, allowed)
			});
			saving = false;
			if (ok) close();
			return;
		}
		created = await mcp.createToken({
			name: name.trim(),
			project_id: project,
			capabilities: grantsUpTo(level, allowed),
			expires_in_days: expiry === 'never' ? null : Number(expiry)
		});
		shownClient = client || (created?.clients[0]?.key ?? '');
		saving = false;
	}
</script>

<Sheet.Root
	bind:open={
		() => open,
		(next) => {
			if (next) open = true;
			else if (!saving) guard.close();
		}
	}
>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
		<Sheet.Header class="border-b px-5 py-4 pr-12">
			<Sheet.Title>
				{editing
					? `Edit access · ${editing.name}`
					: created
						? created.token.name
						: 'Connect an agent'}
			</Sheet.Title>
			{#if created}
				<Sheet.Description>Shown once. Only a hash is stored.</Sheet.Description>
			{/if}
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			{#if created}
				<div class="flex flex-col divide-y px-5">
					<section class="flex min-w-0 flex-col gap-3 py-5">
						<ToggleGroup.Root
							type="single"
							size="sm"
							variant="outline"
							class="flex-wrap"
							value={shownClient}
							onValueChange={(v) => v && (shownClient = v)}
						>
							{#each created.clients as c (c.key)}
								<ToggleGroup.Item value={c.key} class="h-7 px-2.5 text-xs"
									>{c.label}</ToggleGroup.Item
								>
							{/each}
						</ToggleGroup.Root>
						{#if snippet}
							<CodeBlock
								code={snippet.text}
								lang={snippet.lang as CodeLang}
								label={snippet.where}
								numbers={false}
								wrap
							/>
						{/if}
					</section>

					<section class="flex flex-col gap-3 py-5">
						{#if connectedClient}
							<div
								class="flex items-start gap-3 rounded-md border border-info/40 bg-info/8 px-3 py-3"
							>
								<span class="flex h-5 items-center">
									<span class="size-2 rounded-full bg-info" aria-hidden="true"></span>
								</span>
								<div class="flex min-w-0 flex-col gap-0.5">
									<span class="text-sm font-medium">
										Connected · {connectedClient.name}
										{#if connectedClient.version}
											<span class="font-mono text-xs font-normal">{connectedClient.version}</span>
										{/if}
									</span>
									{#if firstCall}
										<span class="text-xs text-muted-foreground wrap-anywhere">
											First call {titles.get(firstCall.tool) ??
												firstCall.tool}{#if firstCall.summary}
												· {firstCall.summary}{/if}
										</span>
									{/if}
								</div>
							</div>
						{:else if !status.enabled}
							<div
								class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-dashed px-3 py-3"
							>
								<span class="text-sm">Server stopped. Calls are refused.</span>
								<LoadingButton
									size="sm"
									loading={mcp.isSaving}
									loadingLabel="Starting"
									onclick={() => mcp.setRunning(true)}
								>
									Start server
								</LoadingButton>
							</div>
						{:else}
							<div class="flex items-center gap-3 rounded-md border border-dashed px-3 py-3">
								<span class="size-2 rounded-full bg-muted-foreground" aria-hidden="true"></span>
								<div class="flex flex-col">
									<span class="text-sm font-medium">Waiting for the first call</span>
									<span class="font-mono text-xs text-muted-foreground">
										{created.token.token_prefix}…
									</span>
								</div>
							</div>
						{/if}
					</section>
				</div>
			{:else}
				<div class="flex flex-col divide-y px-5">
					{#if !editing}
						<section class="flex flex-col gap-2.5 py-5">
							<p id="{clientsId}-label" class="text-sm leading-none font-medium">Client</p>
							<div
								class="grid grid-cols-2 gap-1.5 sm:grid-cols-3"
								role="group"
								aria-labelledby="{clientsId}-label"
							>
								{#each status.clients as c (c.key)}
									<button
										type="button"
										class="h-9 rounded-md border px-2 text-sm transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {client ===
										c.key
											? 'border-foreground/50 bg-muted font-medium'
											: 'hover:border-foreground/30'}"
										aria-pressed={client === c.key}
										onclick={() => pickClient(c.key)}
									>
										{c.label}
									</button>
								{/each}
							</div>
						</section>
					{/if}

					<section class="flex flex-col gap-4 py-5">
						{#if !editing}
							<FormField label="Name">
								{#snippet children({ id })}
									<Input
										{id}
										bind:value={name}
										oninput={() => (named = true)}
										placeholder="Agent name"
										maxlength={80}
									/>
								{/snippet}
							</FormField>
						{/if}

						<FormField label="Project">
							{#snippet children({ id })}
								<Select.Root type="single" bind:value={projectId}>
									<Select.Trigger {id} class="w-full">{projectLabel}</Select.Trigger>
									<Select.Content>
										<Select.Item value={SELECT_NONE}>Every project</Select.Item>
										{#each projects as project (project.id)}
											<Select.Item value={project.id}>{project.name}</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							{/snippet}
						</FormField>

						<div class="flex flex-col gap-2">
							<span class="text-sm font-medium">Access</span>
							<LadderPick {level} {allowed} onChange={(v) => (level = v)} />
						</div>

						{#if top}
							<p class="rounded-md border bg-muted/40 px-3 py-2.5 text-sm leading-snug">
								<span class={touches ? 'font-semibold text-warning' : ''}>{top.reach}</span>
								in
								<span class="font-semibold"
									>{projectLabel === 'Every project' ? 'every project' : projectLabel}</span
								>
								<span class="text-muted-foreground">·</span>
								{#if touches}
									<span class="font-semibold text-warning">Sends traffic to targets</span>
								{:else}
									Sends no traffic
								{/if}
							</p>
						{/if}

						{#if !editing}
							<FormField label="Key expires">
								{#snippet children({ id })}
									<Select.Root type="single" bind:value={expiry}>
										<Select.Trigger {id} class="w-full">{expiryLabel}</Select.Trigger>
										<Select.Content>
											{#each MCP_EXPIRY_CHOICES as choice (choice.label)}
												<Select.Item value={String(choice.value ?? 'never')}>
													{choice.label}
												</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
								{/snippet}
							</FormField>
						{/if}
					</section>
				</div>
			{/if}
		</ScrollArea>

		<Sheet.Footer class="flex-row items-center justify-end gap-2 border-t px-5 py-3">
			{#if !created && !editing && !name.trim()}
				<span class="mr-auto text-xs text-muted-foreground">Name is required.</span>
			{/if}
			{#if created}
				<Button size="sm" onclick={close}>Done</Button>
			{:else}
				<Button size="sm" variant="outline" disabled={saving} onclick={() => guard.close()}>
					Cancel
				</Button>
				<LoadingButton
					size="sm"
					loading={saving}
					loadingLabel={editing ? 'Saving' : 'Creating'}
					disabled={!editing && !name.trim()}
					onclick={submit}
				>
					{editing ? 'Save' : 'Create key'}
				</LoadingButton>
			{/if}
		</Sheet.Footer>
	</Sheet.Content>
</Sheet.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
