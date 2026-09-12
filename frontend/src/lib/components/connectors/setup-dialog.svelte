<script lang="ts">
	import DownloadIcon from '@lucide/svelte/icons/download';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { ingestEndpoint } from '$lib/config/connectors';
	import type { ConnectorCreated } from '$lib/types/connector';

	let { open = $bindable(false), created }: { open: boolean; created: ConnectorCreated | null } =
		$props();

	const endpoint = $derived(open ? ingestEndpoint() : '');
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Connect {created?.connector.name ?? 'the proxy'}</Dialog.Title>
			<Dialog.Description>Shown once. Only a hash is stored.</Dialog.Description>
		</Dialog.Header>

		{#if created}
			<div class="space-y-5">
				<div class="grid gap-2 sm:grid-cols-[7rem_minmax(0,1fr)_auto] sm:items-center">
					<span class="text-muted-foreground text-xs">Endpoint</span>
					<code class="bg-code-surface truncate rounded-md px-3 py-2 font-mono text-xs"
						>{endpoint}</code
					>
					<CopyButton value={endpoint} />

					<span class="text-muted-foreground text-xs">Token</span>
					<code class="bg-code-surface truncate rounded-md px-3 py-2 font-mono text-xs"
						>{created.secret}</code
					>
					<CopyButton value={created.secret} />
				</div>

				<ol class="space-y-4">
					{#each created.setup.steps as step, index (step.title)}
						<li class="flex gap-3">
							<span
								class="bg-muted text-muted-foreground mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-2xs font-medium"
								>{index + 1}</span
							>
							<div class="min-w-0 flex-1 space-y-2">
								<p class="text-sm font-medium">{step.title}</p>
								<p class="text-muted-foreground text-xs">{step.detail}</p>
								{#if index === 0 && created.setup.download_url}
									<Button
										variant="outline"
										size="sm"
										href={created.setup.download_url}
										download={created.setup.client_file}
									>
										<DownloadIcon class="size-3.5" />
										{created.setup.client_file}
									</Button>
								{/if}
							</div>
						</li>
					{/each}
				</ol>
			</div>
		{/if}

		<Dialog.Footer>
			<Button onclick={() => (open = false)}>Done</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
