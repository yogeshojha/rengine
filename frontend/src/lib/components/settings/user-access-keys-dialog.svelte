<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import AccessKeysPanel from '$lib/components/access-keys/access-keys-panel.svelte';
	import type { UserAccount } from '$lib/api/users';
	import { PROFILE_TAB_LABELS } from '$lib/config/routes';

	interface Props {
		user: UserAccount | null;
		onclose: () => void;
	}

	let { user, onclose }: Props = $props();
</script>

<Dialog.Root open={user !== null} onOpenChange={(next) => !next && onclose()}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{PROFILE_TAB_LABELS['access-keys']}</Dialog.Title>
			<Dialog.Description class="wrap-anywhere">{user?.username}</Dialog.Description>
		</Dialog.Header>
		<ScrollArea
			class="min-h-0 flex-1 [&>[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-10rem)]"
		>
			<div class="px-6 py-5">
				{#if user}
					{#key user.id}
						<AccessKeysPanel userId={user.id} />
					{/key}
				{/if}
			</div>
		</ScrollArea>
		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" onclick={onclose}>Close</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
