<script lang="ts">
	import { onMount } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { authApi } from '$lib/api/auth';
	import { twoFactorApi } from '$lib/api/twoFactor';
	import OtpInput from '$lib/components/onboarding/otp-input.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Avatar from '$lib/components/ui/avatar/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { toast } from 'svelte-sonner';
	import ShieldIcon from 'lucide-svelte/icons/shield';
	import ShieldCheckIcon from 'lucide-svelte/icons/shield-check';
	import UserIcon from 'lucide-svelte/icons/user';
	import LockIcon from 'lucide-svelte/icons/lock';
	import MailIcon from 'lucide-svelte/icons/mail';
	import CheckCircleIcon from 'lucide-svelte/icons/check-circle';
	import TriangleAlertIcon from 'lucide-svelte/icons/triangle-alert';
	import CopyIcon from 'lucide-svelte/icons/copy';
	import CheckIcon from 'lucide-svelte/icons/check';
	import DownloadIcon from 'lucide-svelte/icons/download';
	import EyeIcon from 'lucide-svelte/icons/eye';
	import EyeOffIcon from 'lucide-svelte/icons/eye-off';
	import { formatDate } from '$lib/utilities';
	import { getInitials } from '$lib/utilities';

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let isChangingPassword = $state(false);
	let passwordDirty = $state({ current: false, next: false, confirm: false });
	let showCurrentPassword = $state(false);
	let showNewPassword = $state(false);
	let showConfirmPassword = $state(false);
	let passwordSavedAt = $state<Date | null>(null);

	let newUsername = $state('');
	let isChangingUsername = $state(false);
	let usernameDirty = $state(false);
	let usernameSavedAt = $state<Date | null>(null);

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
	const usernameError = $derived.by(() => {
		if (!usernameDirty || !newUsername) return '';
		if (newUsername.length < 3) return 'At least 3 characters';
		if (newUsername === auth.user?.username) return 'Same as current username';
		return '';
	});
	const passwordValid = $derived(
		!!currentPassword &&
			newPassword.length >= 8 &&
			confirmPassword === newPassword &&
			confirmPassword.length > 0
	);
	const usernameValid = $derived(
		!!newUsername && newUsername.length >= 3 && newUsername !== auth.user?.username
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

	const handleUsernameChange = async () => {
		usernameDirty = true;
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
			await authApi.changeUsername({ new_username: newUsername });
			await auth.checkAuth();
			toast.success('Username changed successfully');
			usernameSavedAt = new Date();
			newUsername = '';
			usernameDirty = false;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Failed to change username');
		} finally {
			isChangingUsername = false;
		}
	};

	let twoFactorEnabled = $state(false);
	let twoFactorLoading = $state(true);

	let setupOpen = $state(false);
	let setupSecret = $state('');
	let setupQr = $state('');
	let setupCode = $state('');
	let isSettingUp = $state(false);
	let isVerifying = $state(false);
	let backupCodes = $state<string[] | null>(null);
	let backupCodesSaved = $state(false);
	let confirmCloseCodes = $state(false);

	let disableOpen = $state(false);
	let disableCode = $state('');
	let isDisabling = $state(false);

	let copiedBackup = $state(false);

	let setupOtpWrap = $state<HTMLDivElement | null>(null);
	let disableOtpWrap = $state<HTMLDivElement | null>(null);

	function focusOtp(wrap: HTMLDivElement | null) {
		queueMicrotask(() => wrap?.querySelector('input')?.focus());
	}

	$effect(() => {
		if (setupOpen && setupQr && !backupCodes) focusOtp(setupOtpWrap);
	});
	$effect(() => {
		if (disableOpen) focusOtp(disableOtpWrap);
	});

	const enrollDirty = $derived(
		setupOpen && ((!backupCodes && setupCode.length > 0) || (!!backupCodes && !backupCodesSaved))
	);

	beforeNavigate((nav) => {
		if (!enrollDirty) return;
		if (!confirm('You have an unfinished two-factor setup. Leave and discard it?')) {
			nav.cancel();
		}
	});

	function handleBeforeUnload(e: BeforeUnloadEvent) {
		if (enrollDirty) e.preventDefault();
	}

	async function loadTwoFactorStatus() {
		twoFactorLoading = true;
		try {
			const res = await twoFactorApi.status();
			twoFactorEnabled = res.enabled;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Failed to load 2FA status');
		} finally {
			twoFactorLoading = false;
		}
	}

	async function handleStartSetup() {
		isSettingUp = true;
		try {
			const res = await twoFactorApi.setup();
			setupSecret = res.secret;
			setupQr = res.qr;
			setupCode = '';
			backupCodes = null;
			backupCodesSaved = false;
			setupOpen = true;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Failed to start 2FA setup');
		} finally {
			isSettingUp = false;
		}
	}

	async function handleVerify() {
		if (setupCode.length !== 6) {
			toast.error('Enter the 6-digit code');
			return;
		}
		isVerifying = true;
		try {
			const res = await twoFactorApi.verify(setupCode);
			twoFactorEnabled = res.enabled;
			backupCodes = res.backup_codes;
			backupCodesSaved = false;
			await auth.checkAuth();
			toast.success('Two-factor authentication enabled');
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Invalid code');
		} finally {
			isVerifying = false;
		}
	}

	function closeSetup() {
		setupOpen = false;
		setupSecret = '';
		setupQr = '';
		setupCode = '';
		backupCodes = null;
		backupCodesSaved = false;
	}

	function handleDone() {
		if (!backupCodesSaved) {
			confirmCloseCodes = true;
			return;
		}
		closeSetup();
	}

	async function handleDisable() {
		if (disableCode.length !== 6) {
			toast.error('Enter the 6-digit code');
			return;
		}
		isDisabling = true;
		try {
			const res = await twoFactorApi.disable(disableCode);
			twoFactorEnabled = res.enabled;
			disableOpen = false;
			disableCode = '';
			await auth.checkAuth();
			toast.success('Two-factor authentication disabled');
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Invalid code');
		} finally {
			isDisabling = false;
		}
	}

	async function copyBackupCodes() {
		if (!backupCodes) return;
		try {
			await navigator.clipboard.writeText(backupCodes.join('\n'));
			copiedBackup = true;
			backupCodesSaved = true;
			setTimeout(() => (copiedBackup = false), 2000);
		} catch {
			toast.error('Failed to copy');
		}
	}

	function downloadBackupCodes() {
		if (!backupCodes) return;
		const blob = new Blob([backupCodes.join('\n') + '\n'], { type: 'text/plain' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'rengine-backup-codes.txt';
		a.click();
		URL.revokeObjectURL(url);
		backupCodesSaved = true;
	}

	onMount(() => {
		loadTwoFactorStatus();
	});
</script>

<svelte:window onbeforeunload={handleBeforeUnload} />

<div class="container max-w-5xl mx-auto space-y-6">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">Account &amp; Security</h1>
		<p class="text-sm text-muted-foreground">Manage your credentials and two-factor authentication.</p>
	</div>

	<Card.Root class="overflow-hidden">
		<Card.Content class="pt-0">
			<div class="mb-6">
				<div class="flex items-center gap-4 mb-4">
					<Avatar.Root class="size-14 rounded-md border">
						<Avatar.Fallback
							class="rounded-md bg-primary text-primary-foreground text-lg font-semibold"
						>
							{getInitials(auth.user?.username || 'U')}
						</Avatar.Fallback>
					</Avatar.Root>

					<div class="flex-1">
						<div class="flex items-baseline gap-2 mb-0.5">
							<h2 class="text-xl font-semibold">{auth.user?.username}</h2>
							{#if auth.user?.is_superuser}
								<Badge variant="secondary" class="h-5 text-xs px-2">Administrator</Badge>
							{/if}
						</div>
						<div class="flex items-center gap-3 text-sm text-muted-foreground">
							<span class="flex items-center gap-1.5">
								<MailIcon class="w-3.5 h-3.5" />
								{auth.user?.email}
							</span>
							<span class="text-xs">•</span>
							<span class="flex items-center gap-1.5">
								<CheckCircleIcon class="w-3.5 h-3.5 text-foreground" />
								Active
							</span>
						</div>
					</div>
				</div>
				<Separator />
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
			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleUsernameChange();
				}}
			>
				<Card.Content class="space-y-4">
					<div class="space-y-2">
						<Label for="current-username">Current Username</Label>
						<Input
							id="current-username"
							type="text"
							value={auth.user?.username ?? ''}
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
					<Button class="w-full" type="submit" disabled={isChangingUsername || !usernameValid}>
						{#if isChangingUsername}
							<Spinner class="mr-2" />
							Updating...
						{:else}
							Update Username
						{/if}
					</Button>
				</Card.Footer>
			</form>
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
					<Button class="w-full" type="submit" disabled={isChangingPassword || !passwordValid}>
						{#if isChangingPassword}
							<Spinner class="mr-2" />
							Updating...
						{:else}
							Update Password
						{/if}
					</Button>
				</Card.Footer>
			</form>
		</Card.Root>
	</div>

	<Card.Root>
		<Card.Header>
			<div class="flex items-center gap-2">
				<div class="p-2 rounded-lg bg-primary/10">
					<ShieldIcon class="w-5 h-5 text-primary" />
				</div>
				<div class="flex-1">
					<div class="flex items-center gap-2">
						<Card.Title>Two-Factor Authentication</Card.Title>
						{#if !twoFactorLoading}
							{#if twoFactorEnabled}
								<Badge variant="secondary" class="h-5 text-xs px-2 border-0">Enabled</Badge>
							{:else}
								<Badge variant="secondary" class="h-5 text-xs px-2">Disabled</Badge>
							{/if}
						{/if}
					</div>
					<Card.Description>
						Add an extra layer of security with a time-based one-time code.
					</Card.Description>
				</div>
			</div>
		</Card.Header>
		<Card.Content class="space-y-4">
			{#if twoFactorLoading}
				<div class="space-y-2">
					<Skeleton class="h-4 w-2/3" />
					<Skeleton class="h-9 w-32" />
				</div>
			{:else if twoFactorEnabled && !setupOpen}
				<div class="flex items-center gap-2 text-sm text-muted-foreground">
					<ShieldCheckIcon class="w-4 h-4 text-foreground shrink-0" />
					Your account is protected by an authenticator app.
				</div>

				{#if disableOpen}
					<Separator />
					<div class="space-y-3">
						<Alert.Root variant="destructive">
							<TriangleAlertIcon class="size-4" />
							<Alert.Title>Disable two-factor authentication?</Alert.Title>
							<Alert.Description>
								This removes your second factor and invalidates all backup codes. Anyone with your
								password will be able to sign in.
							</Alert.Description>
						</Alert.Root>
						<p class="text-xs text-muted-foreground">
							Enter a code from your authenticator app or a backup code to confirm.
						</p>
						<div bind:this={disableOtpWrap}>
							<OtpInput
								value={disableCode}
								onValueChange={(v) => (disableCode = v)}
								disabled={isDisabling}
							/>
						</div>
						<div class="flex items-center gap-2">
							<Button
								variant="destructive"
								onclick={handleDisable}
								disabled={isDisabling || disableCode.length !== 6}
							>
								{#if isDisabling}
									<Spinner class="mr-2" />
									Disabling...
								{:else}
									Disable 2FA
								{/if}
							</Button>
							<Button
								variant="ghost"
								onclick={() => {
									disableOpen = false;
									disableCode = '';
								}}
								disabled={isDisabling}
							>
								Cancel
							</Button>
						</div>
					</div>
				{:else}
					<Button
						variant="outline"
						class="text-destructive hover:text-destructive hover:bg-destructive/10"
						onclick={() => {
							disableOpen = true;
							disableCode = '';
						}}
					>
						Disable
					</Button>
				{/if}
			{:else if setupOpen}
				{#if backupCodes}
					<Alert.Root>
						<TriangleAlertIcon class="size-4" />
						<Alert.Title>Save your backup codes</Alert.Title>
						<Alert.Description>
							These are shown only once. Store them somewhere safe — each code can be used once if
							you lose access to your authenticator.
						</Alert.Description>
					</Alert.Root>
					<div class="rounded-md border bg-muted/40 p-3">
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-sm">
							{#each backupCodes as code (code)}
								<span class="select-all tabular-nums">{code}</span>
							{/each}
						</div>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						<Button variant="outline" onclick={copyBackupCodes}>
							{#if copiedBackup}
								<CheckIcon class="size-4 mr-2 text-foreground" />
								Copied
							{:else}
								<CopyIcon class="size-4 mr-2" />
								Copy codes
							{/if}
						</Button>
						<Button variant="outline" onclick={downloadBackupCodes}>
							<DownloadIcon class="size-4 mr-2" />
							Download codes
						</Button>
						<Button onclick={handleDone}>I've saved my codes</Button>
					</div>
				{:else}
					<div class="grid gap-6 sm:grid-cols-[auto_1fr] sm:items-start">
						<div class="flex flex-col items-center gap-2">
							{#if setupQr}
								<img
									src={setupQr}
									alt="2FA QR code"
									class="size-40 rounded-md border bg-white p-2"
								/>
							{/if}
						</div>
						<div class="space-y-3">
							<div class="space-y-1">
								<p class="text-sm font-medium">Scan the QR code</p>
								<p class="text-xs text-muted-foreground">
									Use an authenticator app (1Password, Authy, Google Authenticator) to scan the
									code, or enter the secret manually.
								</p>
							</div>
							<div class="space-y-1.5">
								<Label class="text-xs">Manual setup key</Label>
								<div class="flex items-center gap-1.5">
									<code
										class="block flex-1 text-xs font-mono bg-muted px-3 py-2 rounded-md break-all select-all"
									>
										{setupSecret}
									</code>
									<CopyButton value={setupSecret} />
								</div>
							</div>
							<div class="space-y-1.5">
								<Label class="text-xs">Verification code</Label>
								<div bind:this={setupOtpWrap}>
									<OtpInput
										value={setupCode}
										onValueChange={(v) => (setupCode = v)}
										disabled={isVerifying}
									/>
								</div>
							</div>
							<div class="flex items-center gap-2 pt-1">
								<Button onclick={handleVerify} disabled={isVerifying || setupCode.length !== 6}>
									{#if isVerifying}
										<Spinner class="mr-2" />
										Verifying...
									{:else}
										Verify &amp; enable
									{/if}
								</Button>
								<Button variant="ghost" onclick={closeSetup} disabled={isVerifying}>Cancel</Button>
							</div>
						</div>
					</div>
				{/if}
			{:else}
				<div class="flex items-center gap-2 text-sm text-muted-foreground">
					<TriangleAlertIcon class="w-4 h-4 text-muted-foreground shrink-0" />
					Two-factor authentication is not enabled on your account.
				</div>
				<Button onclick={handleStartSetup} disabled={isSettingUp}>
					{#if isSettingUp}
						<Spinner class="mr-2" />
						Preparing...
					{:else}
						Enable 2FA
					{/if}
				</Button>
			{/if}
		</Card.Content>
	</Card.Root>

	<Card.Root>
		<Card.Header>
			<Card.Title>Account Information</Card.Title>
			<Card.Description>Your account details and status</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">User ID</p>
					<div class="flex items-center gap-1.5">
						<p class="text-sm font-mono break-all">{auth.user?.id}</p>
						{#if auth.user?.id}
							<CopyButton value={auth.user.id} />
						{/if}
					</div>
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

<AlertDialog.Root bind:open={confirmCloseCodes}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>You haven't saved your backup codes</AlertDialog.Title>
			<AlertDialog.Description>
				These codes are shown only once and cannot be retrieved later. Continue without saving them?
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Go back</AlertDialog.Cancel>
			<AlertDialog.Action onclick={closeSetup}>Continue without saving</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
