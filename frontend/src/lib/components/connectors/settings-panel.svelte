<script lang="ts">
	import { untrack } from 'svelte';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { SOURCE_TOOL_LABELS } from '$lib/config/connectors';
	import { SELECT_NONE } from '$lib/constants';
	import type { Connector, ConnectorCreated, SourceTool } from '$lib/types/connector';

	let {
		connector,
		projectId,
		onrotated
	}: { connector: Connector; projectId: string; onrotated: (created: ConnectorCreated) => void } =
		$props();

	let saving = $state(false);
	let rotating = $state(false);
	let confirmDelete = $state(false);
	let error = $state<string | null>(null);

	const tools: SourceTool[] = ['proxy', 'repeater'];
	const contexts = $derived(scanContextsStore.contexts);
	const contextName = $derived(contexts.find((c) => c.id === connector.context_id)?.name ?? 'None');

	const traffic = [
		{
			key: 'only_known_hosts',
			label: 'Only record hosts that belong to a target',
			help: 'Requests to other hosts are discarded.'
		},
		{
			key: 'include_static',
			label: 'Include static content',
			help: 'Images, stylesheets and fonts.'
		},
		{
			key: 'capture_bodies',
			label: 'Keep a request sample',
			help: 'The first request recorded for each shape. Samples may contain credentials.'
		}
	] as const;

	$effect(() => {
		const id = projectId;
		untrack(() => {
			if (scanContextsStore.fetchedProjectId !== id) void scanContextsStore.fetchContexts(id);
		});
	});

	async function patch(body: Parameters<typeof connectorsApi.update>[2]) {
		saving = true;
		error = null;
		try {
			connectors.upsert(await connectorsApi.update(connector.id, projectId, body));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Change not saved.';
		} finally {
			saving = false;
		}
	}

	async function rotate() {
		rotating = true;
		try {
			const created = await connectorsApi.rotate(connector.id, projectId);
			connectors.upsert(created.connector);
			onrotated(created);
		} finally {
			rotating = false;
		}
	}

	async function remove() {
		await connectorsApi.remove(connector.id, projectId);
		connectors.drop(connector.id);
		confirmDelete = false;
	}

	function toggleTool(tool: SourceTool) {
		const next = connector.ingest_tools.includes(tool)
			? connector.ingest_tools.filter((t) => t !== tool)
			: [...connector.ingest_tools, tool];
		void patch({ ingest_tools: next.length ? next : [tool] });
	}
</script>

<div class="space-y-4">
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Traffic" />

		<div class="space-y-4 px-5 py-4">
			<div class="space-y-2">
				<p class="text-sm font-medium">Burp tools</p>
				<div class="flex flex-wrap gap-2">
					{#each tools as tool (tool)}
						<Button
							variant={connector.ingest_tools.includes(tool) ? 'secondary' : 'outline'}
							size="sm"
							onclick={() => toggleTool(tool)}>{SOURCE_TOOL_LABELS[tool]}</Button
						>
					{/each}
				</div>
				<p class="text-muted-foreground text-xs">Intruder and Scanner traffic is not recorded.</p>
			</div>
		</div>

		<div class="divide-y border-t">
			{#each traffic as row (row.key)}
				<div class="flex items-start justify-between gap-4 px-5 py-3.5">
					<div class="min-w-0">
						<p class="text-sm">{row.label}</p>
						<p class="text-muted-foreground text-xs">{row.help}</p>
					</div>
					<Switch checked={connector[row.key]} onCheckedChange={(v) => patch({ [row.key]: v })} />
				</div>
			{/each}
		</div>
	</Card.Root>

	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Scans" />

		<div class="px-5 py-4">
			<FormField
				label="Scan context"
				description="Session, headers and rate limits for scans of the queue."
			>
				{#snippet children({ id })}
					<Select.Root
						type="single"
						value={connector.context_id ?? SELECT_NONE}
						onValueChange={(v) => patch({ context_id: v && v !== SELECT_NONE ? v : null })}
					>
						<Select.Trigger {id}>{contextName}</Select.Trigger>
						<Select.Content>
							<Select.Item value={SELECT_NONE}>None</Select.Item>
							{#each contexts as context (context.id)}
								<Select.Item value={context.id}>{context.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>
		</div>

		<div class="flex items-start justify-between gap-4 border-t px-5 py-3.5">
			<div class="min-w-0">
				<p class="text-sm">Safe methods only</p>
				<p class="text-muted-foreground text-xs">
					Recorded DELETE, PUT and PATCH requests are excluded from scans.
				</p>
			</div>
			<Switch
				checked={connector.scan_safe_methods_only}
				onCheckedChange={(v) => patch({ scan_safe_methods_only: v })}
			/>
		</div>
	</Card.Root>

	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Connection">
			{#if saving}<span>Saving</span>{/if}
		</PanelHead>
		<div class="flex flex-wrap items-center gap-3 px-5 py-4">
			<code class="bg-muted rounded px-2 py-1 font-mono text-xs">{connector.token_prefix}…</code>
			<LoadingButton loading={rotating} variant="outline" size="sm" onclick={rotate}>
				<KeyRoundIcon class="size-3.5" />
				Rotate token
			</LoadingButton>
			<Button
				variant="ghost"
				size="sm"
				class="text-destructive hover:text-destructive"
				onclick={() => (confirmDelete = true)}
			>
				<Trash2Icon class="size-3.5" />
				Delete connector
			</Button>
		</div>
		{#if error}
			<p class="text-destructive border-t px-5 py-2.5 text-xs">{error}</p>
		{/if}
	</Card.Root>
</div>

<DeleteConfirmationDialog
	bind:open={confirmDelete}
	title="Delete {connector.name}"
	description="The connector, its token and its request shapes are removed. Recorded endpoints are kept."
	onOpenChange={(value) => (confirmDelete = value)}
	onConfirm={remove}
/>
