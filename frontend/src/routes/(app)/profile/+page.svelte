<script lang="ts">
	import { auth } from '$lib/stores/auth.svelte';
	import { authApi } from '$lib/api/auth';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Avatar from '$lib/components/ui/avatar/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { toast } from 'svelte-sonner';
	import ShieldIcon from 'lucide-svelte/icons/shield';
	import UserIcon from 'lucide-svelte/icons/user';
	import LockIcon from 'lucide-svelte/icons/lock';
	import MailIcon from 'lucide-svelte/icons/mail';
	import CalendarIcon from 'lucide-svelte/icons/calendar';
	import CheckCircleIcon from 'lucide-svelte/icons/check-circle';
	import { formatDate } from '$lib/utilities';
	import { getInitials } from '$lib/utilities';

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let isChangingPassword = $state(false);

	let newUsername = $state('');
	let isChangingUsername = $state(false);


	// Password change handler
	const handlePasswordChange = async () => {
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
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Failed to change password');
		} finally {
			isChangingPassword = false;
		}
	};

	const handleUsernameChange = async () => {
		if (!newUsername) {
			toast.error('Username is required');
			return;
		}

		if (newUsername === auth.user?.username) {
			toast.error('New username is the same as current username');
			return;
		}

		if (newUsername.length < 3) {
			toast.error('Username must be at least 3 characters long');
			return;
		}

		isChangingUsername = true;

		try {
			await authApi.changeUsername({
				new_username: newUsername
			});

			toast.success('Username changed successfully');
			await auth.checkAuth();
			newUsername = '';
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Failed to change username');
		} finally {
			isChangingUsername = false;
		}
	};
</script>

<div class="container max-w-5xl mx-auto space-y-6">
	<Card.Root class="overflow-hidden">
		<div class="h-32 bg-gradient-to-r from-primary/20 via-primary/10 to-background"></div>
		<Card.Content class="pt-0">
			<div class="flex flex-col sm:flex-row items-start sm:items-end gap-6 -mt-16 sm:-mt-12">
				<Avatar.Root class="size-24 sm:size-28 rounded-2xl border-4 border-background shadow-xl">
					<Avatar.Fallback class="rounded-2xl bg-primary text-primary-foreground text-3xl font-bold">
						{getInitials(auth.user?.username || 'U')}
					</Avatar.Fallback>
				</Avatar.Root>

				<div class="flex-1 space-y-2 pb-2">
					<div class="flex flex-wrap items-center gap-3">
						<h1 class="text-3xl font-bold tracking-tight">{auth.user?.username}</h1>
						{#if auth.user?.is_superuser}
							<Badge variant="secondary" class="bg-blue-500 text-white dark:bg-blue-600">
								<ShieldIcon class="w-3 h-3 mr-1" />
								Administrator
							</Badge>
						{/if}
						{#if auth.user?.is_active}
							<Badge variant="secondary" class="bg-green-500 text-white dark:bg-green-600">
								<CheckCircleIcon class="w-3 h-3 mr-1" />
								Active
							</Badge>
						{/if}
					</div>

					<div class="flex flex-wrap gap-4 text-sm text-muted-foreground">
						<div class="flex items-center gap-2">
							<MailIcon class="w-4 h-4" />
							<span>{auth.user?.email}</span>
						</div>
						{#if auth.user?.created_at}
							<div class="flex items-center gap-2">
								<CalendarIcon class="w-4 h-4" />
								<span>Joined {formatDate(auth.user.created_at)}</span>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</Card.Content>
	</Card.Root>

	<div class="grid gap-6 md:grid-cols-2">
		<Card.Root>
			<Card.Header>
				<div class="flex items-center gap-2">
					<div class="p-2 rounded-lg bg-primary/10">
						<UserIcon class="w-5 h-5 text-primary" />
					</div>
					<div>
						<Card.Title>Change Username</Card.Title>
						<Card.Description>Update your username</Card.Description>
					</div>
				</div>
			</Card.Header>
			<Card.Content class="space-y-4">
				<div class="space-y-2">
					<Label for="current-username">Current Username</Label>
					<Input
						id="current-username"
						type="text"
						value={auth.user?.username}
						disabled
						class="bg-muted"
					/>
				</div>

				<div class="space-y-2">
					<Label for="new-username">New Username</Label>
					<Input
						id="new-username"
						type="text"
						bind:value={newUsername}
						placeholder="Enter new username"
						disabled={isChangingUsername}
					/>
					<p class="text-xs text-muted-foreground">
						Must be at least 3 characters long
					</p>
				</div>
			</Card.Content>
			<Card.Footer>
				<Button
					class="w-full"
					onclick={handleUsernameChange}
					disabled={isChangingUsername || !newUsername}
				>
					{#if isChangingUsername}
						<Spinner class="mr-2" />
						Updating...
					{:else}
						Update Username
					{/if}
				</Button>
			</Card.Footer>
		</Card.Root>

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
			<Card.Content class="space-y-4">
				<div class="space-y-2">
					<Label for="current-password">Current Password</Label>
					<Input
						id="current-password"
						type="password"
						bind:value={currentPassword}
						placeholder="Enter current password"
						disabled={isChangingPassword}
					/>
				</div>

				<Separator />

				<div class="space-y-2">
					<Label for="new-password">New Password</Label>
					<Input
						id="new-password"
						type="password"
						bind:value={newPassword}
						placeholder="Enter new password"
						disabled={isChangingPassword}
					/>
				</div>

				<div class="space-y-2">
					<Label for="confirm-password">Confirm New Password</Label>
					<Input
						id="confirm-password"
						type="password"
						bind:value={confirmPassword}
						placeholder="Confirm new password"
						disabled={isChangingPassword}
					/>
					<p class="text-xs text-muted-foreground">
						Must be at least 8 characters long
					</p>
				</div>
			</Card.Content>
			<Card.Footer>
				<Button
					class="w-full"
					onclick={handlePasswordChange}
					disabled={isChangingPassword || !currentPassword || !newPassword || !confirmPassword}
				>
					{#if isChangingPassword}
						<Spinner class="mr-2" />
						Updating...
					{:else}
						Update Password
					{/if}
				</Button>
			</Card.Footer>
		</Card.Root>
	</div>

	<Card.Root>
		<Card.Header>
			<Card.Title>Account Information</Card.Title>
			<Card.Description>Your account details and status</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">User ID</p>
					<p class="text-sm font-mono">{auth.user?.id}</p>
				</div>

				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">Account Type</p>
					<p class="text-sm">
						{auth.user?.is_superuser ? 'Administrator' : 'Standard User'}
					</p>
				</div>

				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">Email Address</p>
					<p class="text-sm">{auth.user?.email}</p>
				</div>

				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">Account Status</p>
					<p class="text-sm">
						{auth.user?.is_active ? 'Active' : 'Inactive'}
					</p>
				</div>

				{#if auth.user?.created_at}
					<div class="space-y-1">
						<p class="text-sm font-medium text-muted-foreground">Member Since</p>
						<p class="text-sm">{formatDate(auth.user.created_at)}</p>
					</div>
				{/if}

				{#if auth.user?.updated_at}
					<div class="space-y-1">
						<p class="text-sm font-medium text-muted-foreground">Last Updated</p>
						<p class="text-sm">{formatDate(auth.user.updated_at)}</p>
					</div>
				{/if}
			</div>
		</Card.Content>
	</Card.Root>
</div>
