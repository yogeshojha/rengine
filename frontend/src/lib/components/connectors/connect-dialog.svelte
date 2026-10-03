<script lang="ts">
	import DownloadIcon from '@lucide/svelte/icons/download';
	import CheckIcon from '@lucide/svelte/icons/check';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import CopyButton from '$lib/components/copy-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import { connectors } from '$lib/stores/connectors.svelte';
	import {
		CONNECT_POLL_MS,
		ONLINE_STATES,
		clientVersion,
		ingestEndpoint,
		isOutdated
	} from '$lib/config/connectors';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';
	import { plural } from '$lib/utilities/strings';
	import { safeHref } from '$lib/utilities/links';

	interface Props {
		open: boolean;
		projectId: string;
		spec: ConnectorSpec;
		connector: Connector;
		secret: string | null;
		onRotate: () => void;
	}

	let { open = $bindable(), projectId, spec, connector, secret, onRotate }: Props = $props();

	const CODE = 'min-w-0 flex-1 truncate rounded-md bg-code-surface px-3 py-2 font-mono text-xs';

	const endpoint = $derived(open ? ingestEndpoint() : '');
	const online = $derived(ONLINE_STATES.has(connector.state));
	const version = $derived(clientVersion(connector.last_client));
	const outdated = $derived(isOutdated(connector.last_client, spec.client_file));
	const receiving = $derived(connector.requests_seen > 0);

	let copied = $state(false);
	const guard = new DiscardGuard(
		() => !!secret && !copied,
		() => (open = false)
	);

	function finished(index: number): boolean {
		return index === spec.steps.length - 1 ? receiving : online || receiving;
	}

	$effect(() => {
		if (secret) copied = false;
	});

	$effect(() => {
		if (!open) return;
		const id = setInterval(() => void connectors.load(projectId, true), CONNECT_POLL_MS);
		return () => clearInterval(id);
	});
</script>

<Dialog.Root bind:open={() => open, (next) => (next ? (open = true) : guard.close())}>
	<Dialog.Content class="gap-0 p-0 sm:max-w-xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>Connect {spec.title}</Dialog.Title>
			{#if secret}
				<Dialog.Description>Token shown once.</Dialog.Description>
			{/if}
		</Dialog.Header>

		<ol class="flex flex-col gap-5 px-6 py-5">
			{#each spec.steps as step, index (step.title)}
				<li class="flex gap-3.5">
					{#if finished(index)}
						<span
							class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-success/15 text-success"
						>
							<CheckIcon class="size-3.5" />
						</span>
					{:else}
						<span
							class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-medium tabular-nums"
							>{index + 1}</span
						>
					{/if}
					<div class="flex min-w-0 flex-1 flex-col gap-2.5">
						<div>
							<p class="text-sm leading-6 font-medium">{step.title}</p>
							<p class="text-sm text-muted-foreground">{step.detail}</p>
						</div>
						{#if step.control === 'download' && spec.download_url}
							<Button
								variant="outline"
								size="sm"
								class="w-fit"
								href={safeHref(spec.download_url)}
								download={spec.client_file}
							>
								<DownloadIcon class="size-3.5" />
								{spec.client_file}
							</Button>
						{:else if step.control === 'credentials'}
							<div class="flex flex-col gap-2">
								<div class="flex items-center gap-2">
									<span class="w-16 shrink-0 text-xs text-muted-foreground">Endpoint</span>
									<code class={CODE}>{endpoint}</code>
									<CopyButton value={endpoint} />
								</div>
								<div class="flex items-center gap-2">
									<span class="w-16 shrink-0 text-xs text-muted-foreground">Token</span>
									{#if secret}
										<code class={CODE}>{secret}</code>
										<CopyButton value={secret} onCopied={() => (copied = true)} />
									{:else}
										<code class="{CODE} text-muted-foreground">{connector.token_prefix}…</code>
										<Button variant="outline" size="sm" class="h-8" onclick={onRotate}>
											Rotate
										</Button>
									{/if}
								</div>
							</div>
						{/if}
					</div>
				</li>
			{/each}
		</ol>

		<div class="flex items-center justify-between gap-4 border-t px-6 py-4">
			<div class="flex min-w-0 items-center gap-2.5 text-sm">
				{#if connector.paused}
					<span class="size-2 shrink-0 rounded-full bg-muted-foreground" aria-hidden="true"></span>
					<span>Paused</span>
				{:else if online}
					<span
						class="flex size-5 shrink-0 items-center justify-center rounded-full bg-success/15 text-success"
					>
						<CheckIcon class="size-3.5" />
					</span>
					<span class="font-medium">
						{receiving ? `Receiving · ${plural(connector.requests_seen, 'request')}` : 'Connected'}
					</span>
					{#if version}
						<span class="font-mono text-xs {outdated ? 'text-warning' : 'text-muted-foreground'}">
							extension {version}{outdated ? ` · ${clientVersion(spec.client_file)} available` : ''}
						</span>
					{/if}
				{:else}
					<Spinner class="size-4 shrink-0 text-muted-foreground" />
					<span class="text-muted-foreground">Waiting for {spec.title}</span>
				{/if}
			</div>
			<Button onclick={() => guard.close()}>Done</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>

<ConfirmDialog
	open={guard.asking}
	title="Close setup"
	description="The token is shown once. Rotate the token to issue a new one."
	confirmLabel="Close"
	cancelLabel="Keep open"
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
