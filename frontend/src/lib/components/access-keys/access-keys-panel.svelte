<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { accessKeysApi } from '$lib/api/access-keys';
	import type { AccessKey } from '$lib/types/access-key';
	import { activeKeys } from '$lib/utilities/access-keys';
	import AccessKeysTable from './access-keys-table.svelte';
	import CreateKeyDialog from './create-key-dialog.svelte';
	import { ACCESS_KEY_SKELETON } from './columns';

	interface Props {
		userId?: string | null;
		creating?: boolean;
		count?: number;
	}

	let { userId = null, creating = $bindable(false), count = $bindable(0) }: Props = $props();

	let keys = $state<AccessKey[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let revoking = $state<AccessKey | null>(null);
	let busy = $state(false);

	$effect(() => {
		count = activeKeys(keys);
	});

	async function load() {
		loading = true;
		loadError = null;
		try {
			keys = userId ? await accessKeysApi.listFor(userId) : await accessKeysApi.list();
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Access keys not loaded';
		} finally {
			loading = false;
		}
	}

	onMount(() => void load());

	async function revoke() {
		const key = revoking;
		if (!key) return;
		busy = true;
		try {
			if (userId) await accessKeysApi.revokeFor(userId, key.id);
			else await accessKeysApi.revoke(key.id);
			keys = keys.filter((k) => k.id !== key.id);
			toast.success(`Access key ${key.name} revoked`);
			revoking = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Access key not revoked');
		} finally {
			busy = false;
		}
	}
</script>

{#if loading}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="@container/access-keys w-full">
			<TableSkeleton lead={ACCESS_KEY_SKELETON} rows={3} actions={false} />
		</div>
	</Card.Root>
{:else if loadError}
	<EmptyState
		compact
		icon={TriangleAlertIcon}
		title="Access keys not loaded"
		description={loadError}
	>
		<Button variant="outline" size="sm" onclick={load}>
			<RotateCwIcon class="size-3.5" />
			Retry
		</Button>
	</EmptyState>
{:else if keys.length === 0}
	<EmptyState compact icon={KeyRoundIcon} title="No access keys" />
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<AccessKeysTable {keys} onRevoke={(key) => (revoking = key)} />
	</Card.Root>
{/if}

{#if !userId}
	<CreateKeyDialog bind:open={creating} oncreated={(key) => (keys = [key, ...keys])} />
{/if}

<ConfirmDialog
	open={revoking !== null}
	title="Revoke access key"
	description={revoking ? `Access key ${revoking.name} is revoked.` : ''}
	confirmLabel="Revoke"
	loadingLabel="Revoking"
	destructive
	loading={busy}
	onOpenChange={(open) => {
		if (!open) revoking = null;
	}}
	onConfirm={revoke}
/>
