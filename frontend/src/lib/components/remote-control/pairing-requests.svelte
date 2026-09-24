<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import SectionHead from '$lib/components/section-head.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import ApproveDialog from './approve-dialog.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import type { ChannelStatus, PairingRequest } from '$lib/types/remote-control';

	interface Props {
		status: ChannelStatus;
		requests: PairingRequest[];
		now: number;
	}

	let { status, requests, now }: Props = $props();

	let approving = $state<PairingRequest | null>(null);
	let blocking = $state<PairingRequest | null>(null);

	function expiresIn(request: PairingRequest): string {
		const ms = new Date(request.expires_at).getTime() - now;
		if (ms <= 0) return 'expired';
		const minutes = Math.ceil(ms / 60_000);
		return `expires in ${minutes} min`;
	}

	async function block() {
		if (!blocking) return;
		const code = blocking.code;
		blocking = null;
		await remoteControl.block(code);
	}
</script>

<section class="flex flex-col gap-3 py-5">
	<SectionHead title="Pairing requests" count={requests.length} />
	<div class="divide-y rounded-md border">
		{#each requests as request (request.code)}
			<div class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
				<div class="min-w-0 flex-1">
					<div class="flex flex-wrap items-center gap-x-2 leading-5">
						<span class="text-sm font-medium">{request.display}</span>
						<span class="font-mono text-xs text-muted-foreground">{request.external_id}</span>
					</div>
					<div class="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
						<span>code <span class="font-mono text-foreground/80">{request.code}</span></span>
						<span>requested {relativeTime(request.requested_at)}</span>
						<span>{expiresIn(request)}</span>
					</div>
				</div>
				<div class="flex shrink-0 items-center gap-2">
					<Button
						variant="ghost"
						size="sm"
						class="text-muted-foreground"
						onclick={() => (blocking = request)}
					>
						Block
					</Button>
					<Button size="sm" onclick={() => (approving = request)}>Approve</Button>
				</div>
			</div>
		{/each}
	</div>
</section>

<ApproveDialog
	{status}
	request={approving}
	onOpenChange={(v) => {
		if (!v) approving = null;
	}}
/>

<ConfirmDialog
	open={blocking !== null}
	title="Block chat"
	description={blocking ? `Chat ${blocking.display} is blocked. Its messages are ignored.` : ''}
	confirmLabel="Block"
	destructive
	onOpenChange={(v) => {
		if (!v) blocking = null;
	}}
	onConfirm={block}
/>
