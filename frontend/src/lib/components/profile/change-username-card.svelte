<script lang="ts">
	import { auth } from '$lib/stores/auth.svelte';
	import { authApi } from '$lib/api/auth';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { toast } from 'svelte-sonner';
	import UserIcon from '@lucide/svelte/icons/user';
	import CheckIcon from '@lucide/svelte/icons/check';
	import { formatDate } from '$lib/utilities';

	let newUsername = $state('');
	let isChangingUsername = $state(false);
	let usernameDirty = $state(false);
	let usernameSavedAt = $state<Date | null>(null);

	const usernameError = $derived.by(() => {
		if (!usernameDirty || !newUsername) return '';
		if (newUsername.length < 3) return 'At least 3 characters';
		if (newUsername === auth.user?.username) return 'Same as current username';
		return '';
	});
	const usernameValid = $derived(
		!!newUsername && newUsername.length >= 3 && newUsername !== auth.user?.username
	);

	const handleUsernameChange = async () => {
		usernameDirty = true;
		if (!newUsername) {
			toast.error('Username is required');
			return;
		}
		if (newUsername === auth.user?.username) {
			toast.error('New username matches the current username');
			return;
		}
		if (newUsername.length < 3) {
			toast.error('Username must be at least 3 characters');
			return;
		}

		isChangingUsername = true;
		try {
			await authApi.changeUsername({ new_username: newUsername });
			await auth.checkAuth();
			toast.success('Username changed');
			usernameSavedAt = new Date();
			newUsername = '';
			usernameDirty = false;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Username could not be changed');
		} finally {
			isChangingUsername = false;
		}
	};
</script>

<Card.Root>
	<Card.Header>
		<div class="flex items-center gap-2">
			<div class="p-2 rounded-lg bg-primary/10">
				<UserIcon class="w-5 h-5 text-primary" />
			</div>
			<div>
				<Card.Title>Change username</Card.Title>
				<Card.Description>Update your username</Card.Description>
			</div>
		</div>
	</Card.Header>
	<form
		onsubmit={(e) => {
			e.preventDefault();
			handleUsernameChange();
		}}
	>
		<Card.Content class="space-y-4">
			<div class="space-y-2">
				<Label for="current-username">Current username</Label>
				<Input
					id="current-username"
					type="text"
					value={auth.user?.username ?? ''}
					disabled
					class="bg-muted"
				/>
			</div>

			<div class="space-y-2">
				<Label for="new-username">New username</Label>
				<Input
					id="new-username"
					type="text"
					bind:value={newUsername}
					placeholder="Enter new username"
					disabled={isChangingUsername}
					aria-invalid={!!usernameError}
					onblur={() => (usernameDirty = true)}
				/>
				{#if usernameError}
					<p class="text-xs text-destructive">{usernameError}</p>
				{:else}
					<p class="text-xs text-muted-foreground">3+ characters</p>
				{/if}
			</div>

			{#if usernameSavedAt}
				<p class="flex items-center gap-1.5 text-xs text-muted-foreground">
					<CheckIcon class="size-3.5 text-foreground" />
					Username updated · {formatDate(usernameSavedAt.toISOString())}
				</p>
			{/if}
		</Card.Content>
		<Card.Footer class="pt-2">
			<LoadingButton
				class="w-full"
				type="submit"
				loading={isChangingUsername}
				loadingLabel="Updating…"
				disabled={!usernameValid}
			>
				Update username
			</LoadingButton>
		</Card.Footer>
	</form>
</Card.Root>
