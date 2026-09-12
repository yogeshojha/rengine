<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import CodeBlock from '$lib/components/code-block.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import type { CodeLang } from '$lib/utilities/code-highlight';
	import type { ConnectorCreated } from '$lib/types/connector';

	let { open = $bindable(false), created }: { open: boolean; created: ConnectorCreated | null } =
		$props();
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Connection details</Dialog.Title>
			<Dialog.Description>The token is shown once and cannot be retrieved later.</Dialog.Description
			>
		</Dialog.Header>

		{#if created}
			<div class="space-y-4">
				<div class="border-warning/25 bg-warning/10 flex gap-2 rounded-lg border p-3">
					<TriangleAlertIcon class="text-warning mt-0.5 size-4 shrink-0" />
					<p class="text-muted-foreground text-xs">
						Only a hash of the token is stored. If it is lost, rotate the connector to issue a new
						one.
					</p>
				</div>

				<div class="flex items-center gap-2">
					<code class="bg-code-surface flex-1 truncate rounded-md px-3 py-2 font-mono text-xs"
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
								{#if step.code}
									<CodeBlock
										code={step.code}
										lang={(step.lang ?? 'shell') as CodeLang}
										maxLines={8}
									/>
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
