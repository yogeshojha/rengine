<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { formatShortDate } from '$lib/utilities/dates';
	import { SvelteSet } from 'svelte/reactivity';
	import { SELECT_NONE } from '$lib/constants';
	import {
		MCP_EXPIRY_CHOICES,
		TOUCHES_TARGETS,
		type McpCapability,
		type McpTokenCreated
	} from '$lib/types/mcp';

	interface Props {
		open: boolean;
		onOpenChange: (open: boolean) => void;
	}

	let { open, onOpenChange }: Props = $props();

	let name = $state('');
	let projectId = $state<string>(SELECT_NONE);
	const granted = new SvelteSet<string>(['read', 'plan']);
	let expiry = $state<string>('30');
	let creating = $state(false);
	let created = $state<McpTokenCreated | null>(null);
	let copied = $state('');

	const status = $derived(mcp.status);
	const capabilities = $derived(status?.capabilities ?? []);
	const ceiling = $derived(status?.ceiling ?? {});
	const projectList = $derived(projectsStore.projects ?? []);
	const willTouchTargets = $derived(
		[...granted].some((c) => TOUCHES_TARGETS.includes(c as McpCapability))
	);

	const projectLabel = $derived(
		projectId === SELECT_NONE
			? 'Every project'
			: (projectList.find((entry) => entry.id === projectId)?.name ?? 'Select a project')
	);
	const expiryLabel = $derived(
		MCP_EXPIRY_CHOICES.find((c) => String(c.value ?? 'never') === expiry)?.label ?? 'In 30 days'
	);

	function reset() {
		name = '';
		projectId = SELECT_NONE;
		granted.clear();
		granted.add('read');
		granted.add('plan');
		expiry = '30';
		created = null;
		copied = '';
	}

	function toggle(key: string, value: boolean) {
		if (value) granted.add(key);
		else granted.delete(key);
		granted.add('read');
	}

	async function copy(value: string, key: string) {
		if (await writeClipboard(value)) {
			copied = key;
			setTimeout(() => (copied = copied === key ? '' : copied), 1600);
		}
	}

	async function create() {
		if (!name.trim()) return;
		creating = true;
		created = await mcp.createToken({
			name: name.trim(),
			project_id: projectId === SELECT_NONE ? null : projectId,
			capabilities: [...granted],
			expires_in_days: expiry === 'never' ? null : Number(expiry)
		});
		creating = false;
	}

	function close(value: boolean) {
		onOpenChange(value);
		if (!value) reset();
	}
</script>

<Dialog.Root {open} onOpenChange={close}>
	<Dialog.Content class="flex max-h-[92vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg">
		{#if created}
			<Dialog.Header class="px-6 pt-6 pb-0">
				<Dialog.Title>Token created</Dialog.Title>
				<Dialog.Description>
					Copy it now. reNgine stores only a hash and cannot show it again.
				</Dialog.Description>
			</Dialog.Header>

			<ScrollArea
				class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(92vh-10rem)]"
			>
				<div class="flex min-w-0 flex-col gap-4 px-6 pt-5 pb-4">
					<div
						class="rounded-md border border-dashed bg-muted px-3 py-2.5 font-mono text-xs break-all"
					>
						{created.secret}
					</div>

					<div class="flex flex-wrap gap-2">
						<Button variant="outline" size="sm" onclick={() => copy(created!.secret, 'secret')}>
							{#if copied === 'secret'}
								<CheckIcon class="size-4" />Copied
							{:else}
								<CopyIcon class="size-4" />Copy token
							{/if}
						</Button>
						<Button
							variant="outline"
							size="sm"
							onclick={() => copy(created!.client_config, 'config')}
						>
							{#if copied === 'config'}
								<CheckIcon class="size-4" />Copied
							{:else}
								<CopyIcon class="size-4" />Copy client config
							{/if}
						</Button>
					</div>

					<div class="rounded-md border border-success/30 bg-success/8 px-3 py-2.5 text-xs">
						<span class="font-medium">{created.token.name}</span>
						may {created.token.capabilities.join(', ')} in
						<span class="font-medium">{created.token.project_name ?? 'every project'}</span>.
						{#if created.token.expires_at}
							It expires {formatShortDate(created.token.expires_at)}.
						{:else}
							It does not expire.
						{/if}
						You can revoke it at any time.
					</div>

					<div class="flex min-w-0 flex-col gap-1.5">
						<span class="text-xs font-medium">Paste this into your agent</span>
						<pre
							class="min-w-0 overflow-x-auto rounded-md border bg-muted px-3 py-2.5 font-mono text-xs">{created.client_config}</pre>
					</div>
				</div>
			</ScrollArea>

			<div class="flex justify-end gap-2 border-t bg-muted/30 px-6 py-4">
				<Button onclick={() => close(false)}>Done</Button>
			</div>
		{:else}
			<Dialog.Header class="px-6 pt-6 pb-0">
				<Dialog.Title>New service token</Dialog.Title>
				<Dialog.Description>
					Give an agent access with the smallest capability set that lets it do its job.
				</Dialog.Description>
			</Dialog.Header>

			<ScrollArea
				class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(92vh-11rem)]"
			>
				<div class="flex min-w-0 flex-col gap-4 px-6 pt-5 pb-4">
					<FormField label="Name" description="Shown in the session list and the activity trail.">
						{#snippet children({ id })}
							<Input {id} bind:value={name} placeholder="claude-desktop" maxlength={80} />
						{/snippet}
					</FormField>

					<FormField label="Project" description="What this agent is allowed to see.">
						{#snippet children({ id })}
							<Select.Root type="single" bind:value={projectId}>
								<Select.Trigger {id} class="w-full">{projectLabel}</Select.Trigger>
								<Select.Content>
									<Select.Item value={SELECT_NONE}>Every project</Select.Item>
									{#each projectList as project (project.id)}
										<Select.Item value={project.id}>{project.name}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						{/snippet}
					</FormField>

					<div class="flex flex-col gap-2">
						<span class="text-sm font-medium">May</span>
						<div class="flex flex-col gap-1.5">
							{#each capabilities as capability (capability.key)}
								{@const locked = capability.always}
								{@const blocked = !locked && !ceiling[capability.key]}
								{@const touches = TOUCHES_TARGETS.includes(capability.key)}
								<label
									class="flex items-start gap-2.5 rounded-md border px-3 py-2.5 {touches &&
									granted.has(capability.key)
										? 'border-warning/40 bg-warning/6'
										: ''} {blocked ? 'opacity-50' : ''}"
								>
									<Checkbox
										class="mt-0.5"
										checked={locked || granted.has(capability.key)}
										disabled={locked || blocked}
										onCheckedChange={(v) => toggle(capability.key, Boolean(v))}
									/>
									<span class="min-w-0">
										<span class="flex flex-wrap items-center gap-2 text-sm font-medium">
											{capability.label}
											{#if locked}
												<Badge variant="secondary" class="text-[10px]">Required</Badge>
											{:else if touches}
												<Badge variant="warning" class="gap-1 text-[10px]">
													<TriangleAlertIcon class="size-3" />
													Reaches targets
												</Badge>
											{/if}
											{#if blocked}
												<Badge variant="outline" class="text-[10px]">Off for this instance</Badge>
											{/if}
										</span>
										<span class="mt-0.5 block text-xs text-muted-foreground">{capability.help}</span
										>
									</span>
								</label>
							{/each}
						</div>
					</div>

					<FormField
						label="Expires"
						description={willTouchTargets
							? 'A token that can launch scans should be short-lived.'
							: 'A token stops working after this.'}
					>
						{#snippet children({ id })}
							<Select.Root type="single" bind:value={expiry}>
								<Select.Trigger {id} class="w-full">{expiryLabel}</Select.Trigger>
								<Select.Content>
									{#each MCP_EXPIRY_CHOICES as choice (choice.label)}
										<Select.Item value={String(choice.value ?? 'never')}>{choice.label}</Select.Item
										>
									{/each}
								</Select.Content>
							</Select.Root>
						{/snippet}
					</FormField>
				</div>
			</ScrollArea>

			<div class="flex justify-end gap-2 border-t bg-muted/30 px-6 py-4">
				<Button variant="ghost" onclick={() => close(false)}>Cancel</Button>
				<LoadingButton
					loading={creating}
					loadingLabel="Creating…"
					disabled={!name.trim()}
					onclick={create}
				>
					Create token
				</LoadingButton>
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>
