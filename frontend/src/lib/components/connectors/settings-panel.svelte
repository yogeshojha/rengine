<script lang="ts">
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import {
		SOURCE_TOOL_LABELS,
		SYNC_TRIGGERS,
		SYNC_TRIGGER_HELP,
		SYNC_TRIGGER_LABELS
	} from '$lib/config/connectors';
	import type { Connector, ConnectorCreated, SourceTool, SyncTrigger } from '$lib/types/connector';

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

	async function patch(body: Parameters<typeof connectorsApi.update>[2]) {
		saving = true;
		error = null;
		try {
			connectors.upsert(await connectorsApi.update(connector.id, projectId, body));
		} catch (e) {
			error = e instanceof Error ? e.message : 'The change could not be saved.';
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
		<PanelHead title="Traffic" description="Hosts and tools the connector is permitted to send" />

		<div class="space-y-4 px-5 py-4">
			<div class="space-y-2">
				<p class="text-sm font-medium">Source tools</p>
				<div class="flex flex-wrap gap-2">
					{#each tools as tool (tool)}
						<Button
							variant={connector.ingest_tools.includes(tool) ? 'secondary' : 'outline'}
							size="sm"
							onclick={() => toggleTool(tool)}>{SOURCE_TOOL_LABELS[tool]}</Button
						>
					{/each}
				</div>
				<p class="text-muted-foreground text-xs">Fuzzer and scanner traffic is never ingested.</p>
			</div>
		</div>

		<div class="divide-y border-t">
			{#each [{ key: 'only_known_hosts', label: 'Only record hosts that belong to a target', help: 'Requests to any other host are discarded on receipt and cannot be recovered later.' }, { key: 'include_static', label: 'Include static content', help: 'Images, stylesheets and fonts are excluded by default.' }, { key: 'capture_bodies', label: 'Keep a request sample', help: 'Stores the first request recorded for each shape. Samples may contain credentials.' }, { key: 'capture_sessions', label: 'Session records', help: 'Groups traffic into sessions. Only in-scope hostnames are stored.' }] as row (row.key)}
				<div class="flex items-start justify-between gap-4 px-5 py-3.5">
					<div class="min-w-0">
						<p class="text-sm">{row.label}</p>
						<p class="text-muted-foreground text-xs">{row.help}</p>
					</div>
					<Switch
						checked={connector[row.key as 'include_static']}
						onCheckedChange={(v) => patch({ [row.key]: v })}
					/>
				</div>
			{/each}
		</div>
	</Card.Root>

	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Scan trigger" description="Conditions under which the queue is scanned" />

		<div class="space-y-4 px-5 py-4">
			<FormField label="Trigger" description={SYNC_TRIGGER_HELP[connector.sync_trigger]}>
				{#snippet children({ id })}
					<Select.Root
						type="single"
						value={connector.sync_trigger}
						onValueChange={(v) => v && patch({ sync_trigger: v as SyncTrigger })}
					>
						<Select.Trigger {id}>{SYNC_TRIGGER_LABELS[connector.sync_trigger]}</Select.Trigger>
						<Select.Content>
							{#each SYNC_TRIGGERS as option (option)}
								<Select.Item value={option}>{SYNC_TRIGGER_LABELS[option]}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>

			{#if connector.sync_trigger !== 'manual'}
				<div class="grid gap-4 sm:grid-cols-2">
					<FormField label="Quiet period (minutes)">
						{#snippet children({ id })}
							<Input
								{id}
								type="number"
								min="1"
								max="120"
								value={connector.quiet_minutes}
								onchange={(e) => patch({ quiet_minutes: Number(e.currentTarget.value) })}
							/>
						{/snippet}
					</FormField>
					<FormField label="Queue size that triggers a scan">
						{#snippet children({ id })}
							<Input
								{id}
								type="number"
								min="1"
								max="1000"
								value={connector.queue_threshold}
								onchange={(e) => patch({ queue_threshold: Number(e.currentTarget.value) })}
							/>
						{/snippet}
					</FormField>
				</div>
			{/if}
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
			{#if saving}<span>Saving…</span>{/if}
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
	title="Delete {connector.name}?"
	description="Removes the connector, its token and the request shapes it has captured. Scans already launched from its queue are unaffected. This action cannot be undone."
	onOpenChange={(value) => (confirmDelete = value)}
	onConfirm={remove}
/>
