<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import type { ConnectorCreated, ConnectorKind } from '$lib/types/connector';

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
				project_id: projectId
			});
			connectors.upsert(created.connector, true);
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
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>New connector</Dialog.Title>
			<Dialog.Description>
				{spec?.description ?? 'Receives traffic from a web proxy.'}
			</Dialog.Description>
		</Dialog.Header>

		<div class="space-y-4">
			{#if specs.length > 1}
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
			{:else if spec}
				<p class="text-sm">
					{spec.title}
					<span class="text-muted-foreground">· {spec.vendor}</span>
				</p>
			{/if}

			<FormField label="Name">
				{#snippet children({ id })}
					<Input {id} bind:value={name} placeholder="Burp Suite" />
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
