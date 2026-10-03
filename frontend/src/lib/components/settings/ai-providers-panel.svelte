<script lang="ts">
	import { toast } from 'svelte-sonner';
	import CpuIcon from '@lucide/svelte/icons/cpu';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import AiProviderDialog from './ai-provider-dialog.svelte';
	import CheckStatus from './check-status.svelte';
	import { BODY_ROW, CONNECTION_COL, HEAD_ROW } from './columns';
	import { checkState, type CheckState } from './status';
	import { ai } from '$lib/stores/ai.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { settingsActions } from '$lib/stores/settings-actions.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import type { AiConnection } from '$lib/types/ai';

	const STATUS_LABEL: Record<CheckState, string> = {
		ok: 'Passed',
		failed: 'Failed',
		untested: 'Not tested',
		off: 'Not tested'
	};

	let dialogOpen = $state(false);
	let editing = $state<AiConnection | null>(null);
	let removing = $state<AiConnection | null>(null);
	let deleting = $state(false);
	let switching = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const status = $derived(ai.status);
	const rows = $derived(ai.connections);
	const inUse = $derived(rows.find((c) => c.in_use) ?? null);

	function kind(row: AiConnection): string {
		return ai.provider(row.provider)?.label ?? row.provider;
	}

	function keyText(row: AiConnection): string {
		if (row.key_masked) return row.key_masked;
		return ai.provider(row.provider)?.key_optional ? 'No key' : 'Not set';
	}

	function openDialog(row: AiConnection | null) {
		editing = row;
		dialogOpen = true;
	}

	async function use(id: string) {
		const row = rows.find((c) => c.id === id);
		if (!row || row.in_use || !isAdmin) return;
		if (await ai.use(id)) toast.success(`${row.name} in use`);
	}

	function useKey(e: KeyboardEvent, id: string) {
		if (e.key !== ' ') return;
		e.preventDefault();
		void use(id);
	}

	async function test(row: AiConnection) {
		const result = await ai.testConnection(row.id);
		if (!result) return;
		if (result.success) toast.success(result.message);
		else toast.error(result.message);
	}

	async function remove() {
		const row = removing;
		if (!row) return;
		deleting = true;
		try {
			if (await ai.remove(row.id)) {
				toast.success('Provider removed');
				removing = null;
			}
		} finally {
			deleting = false;
		}
	}

	async function setEnabled(value: boolean) {
		switching = true;
		try {
			if (await ai.save({ enabled: value })) toast.success(value ? 'AI enabled' : 'AI disabled');
		} finally {
			switching = false;
		}
	}

	$effect(() => {
		if (!isAdmin) return;
		settingsActions.set(addAction);
		return () => settingsActions.clear(addAction);
	});
</script>

{#snippet addAction()}
	<Button size="sm" onclick={() => openDialog(null)}>
		<PlusIcon class="size-4" />
		Add provider
	</Button>
{/snippet}

<div id="ai-connection" class="scroll-mt-20"></div>
<PanelHead title="Providers" class="px-4">
	{#if rows.length && !inUse}
		<span class="text-warning">No provider in use</span>
	{/if}
	<label class="flex items-center gap-2 text-sm text-foreground" for="ai-enabled">
		Enabled
		<Switch
			id="ai-enabled"
			checked={status?.enabled ?? false}
			disabled={!isAdmin || switching || (!status?.enabled && !status?.configured)}
			onCheckedChange={setEnabled}
		/>
	</label>
</PanelHead>

{#if rows.length === 0}
	<EmptyState
		compact
		icon={CpuIcon}
		title="No providers"
		class="rounded-none border-0 bg-transparent"
	>
		{#if isAdmin}
			<Button size="sm" onclick={() => openDialog(null)}>
				<PlusIcon class="size-4" />
				Add provider
			</Button>
		{/if}
	</EmptyState>
{:else}
	<div class="@container/ai w-full">
		<div class={HEAD_ROW} aria-hidden="true">
			<div class={CONNECTION_COL.use}></div>
			<div class={CONNECTION_COL.provider}>Provider</div>
			<div class={CONNECTION_COL.model}>Model</div>
			<div class={CONNECTION_COL.key}>Key</div>
			<div class={CONNECTION_COL.status}>Status</div>
			<div class={CONNECTION_COL.actions}></div>
		</div>
		<RadioGroup.Root
			value={inUse?.id ?? ''}
			readonly
			disabled={!isAdmin}
			aria-label="Provider in use"
			class="gap-0"
		>
			{#each rows as row (row.id)}
				{@const check = checkState(true, row.last_test_ok)}
				{@const busy = ai.isTesting(row.id)}
				<div class={BODY_ROW}>
					<div class={CONNECTION_COL.use}>
						<RadioGroup.Item
							value={row.id}
							id="ai-use-{row.id}"
							aria-label={row.name}
							onclick={() => void use(row.id)}
							onkeydown={(e: KeyboardEvent) => useKey(e, row.id)}
						/>
						{#if row.in_use}
							<label
								for="ai-use-{row.id}"
								class="hidden text-xs text-muted-foreground @md/ai:inline"
							>
								In use
							</label>
						{/if}
					</div>
					<div class="{CONNECTION_COL.provider} flex flex-col">
						<span class="text-sm leading-5 font-medium wrap-anywhere">{row.name}</span>
						{#if kind(row) !== row.name}
							<span class="text-2xs text-muted-foreground">{kind(row)}</span>
						{/if}
						<span class="font-mono text-2xs text-muted-foreground wrap-anywhere @lg/ai:hidden">
							{row.model}
						</span>
					</div>
					<div class="{CONNECTION_COL.model} font-mono text-xs wrap-anywhere">{row.model}</div>
					<div class={CONNECTION_COL.key}>
						<code class="font-mono text-xs text-muted-foreground">{keyText(row)}</code>
					</div>
					<div class="{CONNECTION_COL.status} flex flex-col">
						<CheckStatus
							{check}
							label={STATUS_LABEL[check]}
							message={check === 'failed' ? row.last_test_message : null}
							{busy}
							busyLabel="Testing"
							muted={check !== 'ok' && check !== 'failed'}
						/>
						{#if row.last_test_at && !busy}
							<span class="pl-4 text-2xs text-muted-foreground tabular-nums">
								{relativeTime(row.last_test_at)}
							</span>
						{/if}
					</div>
					<div class={CONNECTION_COL.actions}>
						{#if isAdmin}
							<DropdownMenu.Root>
								<DropdownMenu.Trigger>
									{#snippet child({ props })}
										<Button
											{...props}
											variant="ghost"
											size="icon"
											class="size-7"
											aria-label="{row.name} actions"
										>
											<EllipsisIcon class="size-4" />
										</Button>
									{/snippet}
								</DropdownMenu.Trigger>
								<DropdownMenu.Content align="end">
									<DropdownMenu.Item disabled={row.in_use} onSelect={() => use(row.id)}>
										Use
									</DropdownMenu.Item>
									<DropdownMenu.Item onSelect={() => openDialog(row)}>Edit</DropdownMenu.Item>
									<DropdownMenu.Item disabled={busy} onSelect={() => test(row)}>
										Test
									</DropdownMenu.Item>
									<DropdownMenu.Separator />
									<DropdownMenu.Item variant="destructive" onSelect={() => (removing = row)}>
										Remove
									</DropdownMenu.Item>
								</DropdownMenu.Content>
							</DropdownMenu.Root>
						{/if}
					</div>
				</div>
			{/each}
		</RadioGroup.Root>
	</div>
{/if}

<AiProviderDialog bind:open={dialogOpen} connection={editing} />

<ConfirmDialog
	open={removing !== null}
	title="Remove provider"
	description={removing ? `Provider ${removing.name} is removed.` : ''}
	confirmLabel="Remove"
	loadingLabel="Removing"
	destructive
	loading={deleting}
	onOpenChange={(open) => {
		if (!open) removing = null;
	}}
	onConfirm={remove}
/>
