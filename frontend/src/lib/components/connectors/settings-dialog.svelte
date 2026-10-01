<script lang="ts">
	import { untrack } from 'svelte';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Switch } from '$lib/components/ui/switch';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { INGESTED_TOOLS, SOURCE_TOOL_LABELS } from '$lib/config/connectors';
	import { SELECT_NONE } from '$lib/constants';
	import type { Connector, ConnectorSpec, SourceTool } from '$lib/types/connector';

	interface Props {
		open: boolean;
		spec: ConnectorSpec;
		connector: Connector;
		projectId: string;
	}

	let { open = $bindable(), spec, connector, projectId }: Props = $props();

	const switches = [
		{ key: 'only_known_hosts', label: 'Target hosts only', help: '' },
		{ key: 'include_static', label: 'Static content', help: 'Images, stylesheets, fonts' },
		{ key: 'capture_bodies', label: 'Request samples', help: 'First request per shape' },
		{ key: 'scan_safe_methods_only', label: 'Safe methods only', help: 'GET, HEAD, OPTIONS' },
		{ key: 'restore_credentials', label: 'Restore masked headers', help: '' }
	] as const;

	type Key = (typeof switches)[number]['key'];

	let tools = $state<SourceTool[]>([]);
	let flags = $state<Record<Key, boolean>>({
		only_known_hosts: false,
		include_static: false,
		capture_bodies: false,
		scan_safe_methods_only: false,
		restore_credentials: false
	});
	let contextId = $state<string>(SELECT_NONE);
	let saving = $state(false);
	let error = $state<string | null>(null);

	const contexts = $derived(scanContextsStore.contexts);
	const contextName = $derived(contexts.find((c) => c.id === contextId)?.name ?? 'None');

	$effect(() => {
		if (!open) return;
		const id = projectId;
		untrack(() => {
			tools = [...connector.ingest_tools];
			for (const row of switches) flags[row.key] = connector[row.key];
			contextId = connector.context_id ?? SELECT_NONE;
			error = null;
			if (scanContextsStore.fetchedProjectId !== id) void scanContextsStore.fetchContexts(id);
		});
	});

	async function save() {
		saving = true;
		error = null;
		try {
			connectors.upsert(
				await connectorsApi.update(connector.id, projectId, {
					...flags,
					ingest_tools: tools,
					context_id: contextId === SELECT_NONE ? null : contextId
				})
			);
			open = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Settings not saved.';
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="gap-0 p-0 sm:max-w-lg">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{spec.title} settings</Dialog.Title>
		</Dialog.Header>

		<div class="flex flex-col gap-5 px-6 py-5">
			<div class="flex items-center justify-between gap-4">
				<span class="text-sm font-medium">Tools</span>
				<ToggleGroup.Root
					type="multiple"
					size="sm"
					variant="outline"
					value={tools}
					onValueChange={(v) => v.length && (tools = v as SourceTool[])}
				>
					{#each INGESTED_TOOLS as tool (tool)}
						<ToggleGroup.Item value={tool} class="h-7 px-2.5 text-xs">
							{SOURCE_TOOL_LABELS[tool]}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
			</div>

			{#each switches as row (row.key)}
				<div class="flex items-center justify-between gap-4">
					<div class="flex min-w-0 flex-col">
						<span class="text-sm font-medium">{row.label}</span>
						{#if row.help}
							<span class="text-xs text-muted-foreground">{row.help}</span>
						{/if}
					</div>
					<Switch bind:checked={flags[row.key]} />
				</div>
			{/each}

			<div class="flex items-center justify-between gap-4">
				<span class="text-sm font-medium">Scan context</span>
				<Select.Root type="single" bind:value={contextId}>
					<Select.Trigger class="w-44">{contextName}</Select.Trigger>
					<Select.Content>
						<Select.Item value={SELECT_NONE}>None</Select.Item>
						{#each contexts as context (context.id)}
							<Select.Item value={context.id}>{context.name}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>

			{#if error}
				<p class="text-xs text-destructive">{error}</p>
			{/if}
		</div>

		<div class="flex justify-end gap-2 border-t bg-muted/30 px-6 py-3.5">
			<Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
			<LoadingButton loading={saving} onclick={save}>Save</LoadingButton>
		</div>
	</Dialog.Content>
</Dialog.Root>
