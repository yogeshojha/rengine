<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import { SYNC_TRIGGERS, SYNC_TRIGGER_HELP, SYNC_TRIGGER_LABELS } from '$lib/config/connectors';
	import type { ConnectorCreated, ConnectorKind, SyncTrigger } from '$lib/types/connector';

	let {
		open = $bindable(false),
		projectId,
		oncreated
	}: {
		open: boolean;
		projectId: string;
		oncreated: (created: ConnectorCreated) => void;
	} = $props();

	let kind = $state<ConnectorKind>('burp');
	let name = $state('');
	let trigger = $state<SyncTrigger>('manual');
	let saving = $state(false);
	let error = $state<string | null>(null);

	const specs = $derived(connectors.catalog);
	const spec = $derived(specs.find((s) => s.kind === kind) ?? null);

	$effect(() => {
		if (open) void connectors.loadCatalog();
	});

	$effect(() => {
		if (open && !name && spec) name = spec.title;
	});

	async function submit() {
		if (!name.trim()) {
			error = 'Enter a name.';
			return;
		}
		saving = true;
		error = null;
		try {
			const created = await connectorsApi.create({
				name: name.trim(),
				kind,
				project_id: projectId,
				sync_trigger: trigger
			});
			connectors.upsert(created.connector);
			oncreated(created);
			open = false;
			name = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Connector not created.';
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>New connector</Dialog.Title>
			<Dialog.Description>Receive proxied traffic from Burp Suite.</Dialog.Description>
		</Dialog.Header>

		<div class="space-y-4">
			<div class="grid grid-cols-2 gap-2">
				{#each specs as candidate (candidate.kind)}
					<button
						type="button"
						class="rounded-lg border p-3 text-left transition-colors {kind === candidate.kind
							? 'border-primary bg-primary/5'
							: 'hover:bg-muted/50'}"
						onclick={() => (kind = candidate.kind)}
					>
						<p class="text-sm font-medium">{candidate.title}</p>
						<p class="text-muted-foreground text-xs">{candidate.vendor}</p>
					</button>
				{/each}
			</div>

			<FormField label="Name">
				{#snippet children({ id })}
					<Input {id} bind:value={name} placeholder="Burp Suite" />
				{/snippet}
			</FormField>

			<FormField label="Scan trigger" description={SYNC_TRIGGER_HELP[trigger]}>
				{#snippet children({ id })}
					<Select.Root type="single" bind:value={trigger}>
						<Select.Trigger {id}>{SYNC_TRIGGER_LABELS[trigger]}</Select.Trigger>
						<Select.Content>
							{#each SYNC_TRIGGERS as option (option)}
								<Select.Item value={option}>{SYNC_TRIGGER_LABELS[option]}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>

			{#if error}
				<p class="text-destructive text-xs">{error}</p>
			{/if}
		</div>

		<Dialog.Footer>
			<Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
			<LoadingButton loading={saving} onclick={submit}>Create connector</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
