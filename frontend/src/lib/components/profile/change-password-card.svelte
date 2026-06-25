<script lang="ts">
	import { authApi } from '$lib/api/auth';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { toast } from 'svelte-sonner';
	import LockIcon from '@lucide/svelte/icons/lock';
	import CheckIcon from '@lucide/svelte/icons/check';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import { formatDate } from '$lib/utilities';

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let isChangingPassword = $state(false);
	let passwordDirty = $state({ current: false, next: false, confirm: false });
	let showCurrentPassword = $state(false);
	let showNewPassword = $state(false);
	let showConfirmPassword = $state(false);
	let passwordSavedAt = $state<Date | null>(null);

	const newPasswordError = $derived(
		passwordDirty.next && newPassword.length > 0 && newPassword.length < 8
			? 'At least 8 characters'
			: ''
	);
	const confirmPasswordError = $derived(
		passwordDirty.confirm && confirmPassword.length > 0 && confirmPassword !== newPassword
			? 'Passwords do not match'
			: ''
	);
	const passwordValid = $derived(
		!!currentPassword &&
			newPassword.length >= 8 &&
			confirmPassword === newPassword &&
			confirmPassword.length > 0
	);

	const handlePasswordChange = async () => {
		passwordDirty = { current: true, next: true, confirm: true };
		if (!currentPassword || !newPassword || !confirmPassword) {
			toast.error('All password fields are required');
			return;
		}
		if (newPassword !== confirmPassword) {
			toast.error('New passwords do not match');
			return;
		}
		if (newPassword.length < 8) {
			toast.error('Password must be at least 8 characters long');
			return;
		}

		isChangingPassword = true;
		try {
			await authApi.changePassword({
				current_password: currentPassword,
				new_password: newPassword
			});
			toast.success('Password changed successfully');
			passwordSavedAt = new Date();
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
			passwordDirty = { current: false, next: false, confirm: false };
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Failed to change password');
		} finally {
			isChangingPassword = false;
		}
	};
</script>

<Card.Root>
	<Card.Header>
		<div class="flex items-center gap-2">
			<div class="p-2 rounded-lg bg-primary/10">
				<LockIcon class="w-5 h-5 text-primary" />
			</div>
			<div>
				<Card.Title>Change Password</Card.Title>
				<Card.Description>Update your password</Card.Description>
			</div>
		</div>
	</Card.Header>
	<form
		onsubmit={(e) => {
			e.preventDefault();
			handlePasswordChange();
		}}
	>
		<Card.Content class="space-y-4">
			<div class="space-y-2">
				<Label for="current-password">Current Password</Label>
				<div class="relative">
					<Input
						id="current-password"
						type={showCurrentPassword ? 'text' : 'password'}
						bind:value={currentPassword}
						placeholder="Enter current password"
						disabled={isChangingPassword}
						class="pr-10"
					/>
					<button
						type="button"
						onclick={() => (showCurrentPassword = !showCurrentPassword)}
						class="absolute right-0 top-0 h-full px-3 py-2"
						aria-label={showCurrentPassword ? 'Hide password' : 'Show password'}
					>
						{#if showCurrentPassword}
							<EyeOffIcon class="h-4 w-4 text-muted-foreground" />
						{:else}
							<EyeIcon class="h-4 w-4 text-muted-foreground" />
						{/if}
					</button>
				</div>
			</div>

			<Separator />

			<div class="space-y-2">
				<Label for="new-password">New Password</Label>
				<div class="relative">
					<Input
						id="new-password"
						type={showNewPassword ? 'text' : 'password'}
						bind:value={newPassword}
						placeholder="Enter new password"
						disabled={isChangingPassword}
						class="pr-10"
						aria-invalid={!!newPasswordError}
						onblur={() => (passwordDirty.next = true)}
					/>
					<button
						type="button"
						onclick={() => (showNewPassword = !showNewPassword)}
						class="absolute right-0 top-0 h-full px-3 py-2"
						aria-label={showNewPassword ? 'Hide password' : 'Show password'}
					>
						{#if showNewPassword}
							<EyeOffIcon class="h-4 w-4 text-muted-foreground" />
						{:else}
							<EyeIcon class="h-4 w-4 text-muted-foreground" />
						{/if}
					</button>
				</div>
				{#if newPasswordError}
					<p class="text-xs text-destructive">{newPasswordError}</p>
				{:else}
					<p class="text-xs text-muted-foreground">8+ characters</p>
				{/if}
			</div>

			<div class="space-y-2">
				<Label for="confirm-password">Confirm New Password</Label>
				<div class="relative">
					<Input
						id="confirm-password"
						type={showConfirmPassword ? 'text' : 'password'}
						bind:value={confirmPassword}
						placeholder="Confirm new password"
						disabled={isChangingPassword}
						class="pr-10"
						aria-invalid={!!confirmPasswordError}
						onblur={() => (passwordDirty.confirm = true)}
					/>
					<button
						type="button"
						onclick={() => (showConfirmPassword = !showConfirmPassword)}
						class="absolute right-0 top-0 h-full px-3 py-2"
						aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
					>
						{#if showConfirmPassword}
							<EyeOffIcon class="h-4 w-4 text-muted-foreground" />
						{:else}
							<EyeIcon class="h-4 w-4 text-muted-foreground" />
						{/if}
					</button>
				</div>
				{#if confirmPasswordError}
					<p class="text-xs text-destructive">{confirmPasswordError}</p>
				{/if}
			</div>

			{#if passwordSavedAt}
				<p class="flex items-center gap-1.5 text-xs text-muted-foreground">
					<CheckIcon class="size-3.5 text-foreground" />
					Password updated · {formatDate(passwordSavedAt.toISOString())}
				</p>
			{/if}
		</Card.Content>
		<Card.Footer class="pt-2">
			<LoadingButton
				class="w-full"
				type="submit"
				loading={isChangingPassword}
				loadingLabel="Updating..."
				disabled={!passwordValid}
			>
				Update Password
			</LoadingButton>
		</Card.Footer>
	</form>
</Card.Root>
