<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { twoFactorApi } from '$lib/api/twoFactor';
	import OtpInput from '$lib/components/onboarding/otp-input.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { toast } from 'svelte-sonner';
	import ShieldIcon from '@lucide/svelte/icons/shield';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import CheckIcon from '@lucide/svelte/icons/check';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import { downloadBlob } from '$lib/utilities/download';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { TOTP_DIGITS } from '$lib/constants';

	let twoFactorEnabled = $state(false);
	let twoFactorLoading = $state(true);

	let setupOpen = $state(false);
	let setupPassword = $state('');
	let setupError = $state('');
	let setupPasswordInput = $state<HTMLInputElement | null>(null);
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
	let disableUseBackupCode = $state(false);
	let isDisabling = $state(false);

	let copiedBackup = $state(false);

	let setupOtpInput = $state<HTMLInputElement | null>(null);
	let disableOtpInput = $state<HTMLInputElement | null>(null);

	$effect(() => {
		if (setupOpen && setupQr && !backupCodes) setupOtpInput?.focus();
	});
	$effect(() => {
		if (disableOpen && !disableUseBackupCode) disableOtpInput?.focus();
	});

	const canDisable = $derived(
		disableUseBackupCode ? disableCode.trim().length > 0 : disableCode.length === TOTP_DIGITS
	);

	const enrollDirty = $derived(
		setupOpen && ((!backupCodes && setupCode.length > 0) || (!!backupCodes && !backupCodesSaved))
	);

	let showLeaveDialog = $state(false);
	let pendingNav: (() => void) | null = $state(null);
	let allowNavigation = $state(false);

	beforeNavigate((nav) => {
		if (allowNavigation) {
			allowNavigation = false;
			return;
		}
		if (!enrollDirty || pendingNav) return;
		nav.cancel();
		pendingNav = () => {
			allowNavigation = true;
			if (nav.to) goto(nav.to.url);
		};
		showLeaveDialog = true;
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
			toast.error(error instanceof Error ? error.message : 'Two-factor status not loaded');
		} finally {
			twoFactorLoading = false;
		}
	}

	async function handleStartSetup() {
		if (!setupPassword) return;
		isSettingUp = true;
		setupError = '';
		try {
			const res = await twoFactorApi.setup(setupPassword);
			setupPassword = '';
			setupSecret = res.secret;
			setupQr = res.qr;
			setupCode = '';
			backupCodes = null;
			backupCodesSaved = false;
			setupOpen = true;
		} catch (error) {
			setupError = error instanceof Error ? error.message : 'Two-factor setup not started';
		} finally {
			isSettingUp = false;
		}
		if (setupError) {
			await tick();
			setupPasswordInput?.focus();
			setupPasswordInput?.select();
		}
	}

	async function handleVerify() {
		if (setupCode.length !== TOTP_DIGITS) {
			toast.error(`Enter the ${TOTP_DIGITS}-digit code`);
			return;
		}
		isVerifying = true;
		try {
			const res = await twoFactorApi.verify(setupCode);
			twoFactorEnabled = res.enabled;
			backupCodes = res.backup_codes;
			backupCodesSaved = false;
			await auth.refreshUser();
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

	function toggleDisableBackupCode() {
		disableUseBackupCode = !disableUseBackupCode;
		disableCode = '';
	}

	async function handleDisable() {
		if (!canDisable) return;
		isDisabling = true;
		try {
			const res = await twoFactorApi.disable(disableCode.trim());
			twoFactorEnabled = res.enabled;
			disableOpen = false;
			disableCode = '';
			disableUseBackupCode = false;
			await auth.refreshUser();
			toast.success('Two-factor authentication disabled');
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Invalid code');
		} finally {
			isDisabling = false;
		}
	}

	async function copyBackupCodes() {
		if (!backupCodes) return;
		if (await writeClipboard(backupCodes.join('\n'))) {
			copiedBackup = true;
			backupCodesSaved = true;
			setTimeout(() => (copiedBackup = false), 2000);
		} else {
			toast.error('Backup codes not copied');
		}
	}

	function downloadBackupCodes() {
		if (!backupCodes) return;
		downloadBlob('rengine-backup-codes.txt', backupCodes.join('\n') + '\n');
		backupCodesSaved = true;
	}

	onMount(() => {
		loadTwoFactorStatus();
	});
</script>

<svelte:window onbeforeunload={handleBeforeUnload} />

<Card.Root>
	<Card.Header>
		<div class="flex items-center gap-2">
			<div class="p-2 rounded-lg bg-primary/10">
				<ShieldIcon class="w-5 h-5 text-primary" />
			</div>
			<div class="flex-1">
				<div class="flex items-center gap-2">
					<Card.Title>Two-factor authentication</Card.Title>
					{#if !twoFactorLoading}
						{#if twoFactorEnabled}
							<Badge variant="secondary" class="h-5 text-xs px-2 border-0">Enabled</Badge>
						{:else}
							<Badge variant="secondary" class="h-5 text-xs px-2">Disabled</Badge>
						{/if}
					{/if}
				</div>
				<Card.Description>Require a time-based one-time code at login.</Card.Description>
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
				An authenticator app is registered.
			</div>

			{#if disableOpen}
				<Separator />
				<div class="space-y-3">
					<Alert.Root variant="destructive">
						<TriangleAlertIcon class="size-4" />
						<Alert.Title>Disable two-factor authentication</Alert.Title>
						<Alert.Description>
							Removes the second factor and invalidates every backup code.
						</Alert.Description>
					</Alert.Root>
					<p class="text-xs text-muted-foreground">
						{disableUseBackupCode
							? 'Enter one of the backup codes saved at enrollment.'
							: `Enter the ${TOTP_DIGITS}-digit code from the authenticator app.`}
					</p>
					{#if disableUseBackupCode}
						<Label for="disable-backup-code" class="sr-only">Backup code</Label>
						<Input
							id="disable-backup-code"
							type="text"
							autocomplete="one-time-code"
							placeholder="0000-0000"
							class="max-w-48 font-mono"
							disabled={isDisabling}
							bind:value={disableCode}
						/>
					{:else}
						<Label for="disable-otp" class="sr-only">Authentication code</Label>
						<OtpInput
							id="disable-otp"
							bind:inputRef={disableOtpInput}
							value={disableCode}
							onValueChange={(v) => (disableCode = v)}
							disabled={isDisabling}
						/>
					{/if}
					<Button
						variant="link"
						size="sm"
						class="h-auto p-0 text-muted-foreground"
						onclick={toggleDisableBackupCode}
						disabled={isDisabling}
					>
						{disableUseBackupCode ? 'Use the authenticator app' : 'Use a backup code'}
					</Button>
					<div class="flex items-center gap-2">
						<LoadingButton
							variant="destructive"
							onclick={handleDisable}
							loading={isDisabling}
							loadingLabel="Disabling"
							disabled={!canDisable}
						>
							Disable 2FA
						</LoadingButton>
						<Button
							variant="ghost"
							onclick={() => {
								disableOpen = false;
								disableCode = '';
								disableUseBackupCode = false;
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
					<Alert.Title>Backup codes</Alert.Title>
					<Alert.Description>Shown once. Each code is valid for one login.</Alert.Description>
				</Alert.Root>
				<div class="rounded-md border-l-2 border-warning bg-muted p-3">
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-sm">
						{#each backupCodes as code (code)}
							<span class="select-all tabular-nums">{code}</span>
						{/each}
					</div>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					<Button variant="outline" onclick={copyBackupCodes}>
						{#if copiedBackup}
							<CheckIcon class="size-4 text-foreground" />
							Copied
						{:else}
							<CopyIcon class="size-4" />
							Copy codes
						{/if}
					</Button>
					<Button variant="outline" onclick={downloadBackupCodes}>
						<DownloadIcon class="size-4" />
						Download codes
					</Button>
					<Button onclick={handleDone}>Done</Button>
				</div>
			{:else}
				<div class="grid gap-6 sm:grid-cols-[auto_1fr] sm:items-start">
					<div class="flex flex-col items-center gap-2">
						{#if setupQr}
							<img src={setupQr} alt="2FA QR code" class="size-40 rounded-md border bg-white p-2" />
						{/if}
					</div>
					<div class="space-y-4">
						<div class="space-y-1">
							<p class="text-sm font-medium">Scan the QR code</p>
							<p class="text-xs text-muted-foreground">
								Scan the code with an authenticator app or enter the setup key manually.
							</p>
						</div>
						<div class="flex flex-col gap-3">
							<Label>Setup key</Label>
							<div class="flex items-center gap-1.5">
								<code
									class="block flex-1 text-xs font-mono bg-muted px-3 py-2 rounded-md break-all select-all"
								>
									{setupSecret}
								</code>
								<CopyButton value={setupSecret} />
							</div>
						</div>
						<FormField label="Verification code">
							{#snippet children({ id })}
								<OtpInput
									{id}
									bind:inputRef={setupOtpInput}
									value={setupCode}
									onValueChange={(v) => (setupCode = v)}
									disabled={isVerifying}
								/>
							{/snippet}
						</FormField>
						<div class="flex items-center gap-2 pt-1">
							<LoadingButton
								onclick={handleVerify}
								loading={isVerifying}
								loadingLabel="Verifying"
								disabled={setupCode.length !== TOTP_DIGITS}
							>
								Verify and enable
							</LoadingButton>
							<Button variant="ghost" onclick={closeSetup} disabled={isVerifying}>Cancel</Button>
						</div>
					</div>
				</div>
			{/if}
		{:else}
			<form
				class="space-y-3"
				onsubmit={(e) => {
					e.preventDefault();
					handleStartSetup();
				}}
			>
				<FormField label="Current password" error={setupError || undefined}>
					{#snippet children({ id })}
						<Input
							{id}
							type="password"
							autocomplete="current-password"
							class="max-w-72"
							disabled={isSettingUp}
							aria-invalid={setupError ? true : undefined}
							bind:ref={setupPasswordInput}
							bind:value={setupPassword}
							oninput={() => (setupError = '')}
						/>
					{/snippet}
				</FormField>
				<LoadingButton
					type="submit"
					loading={isSettingUp}
					loadingLabel="Preparing"
					disabled={!setupPassword}
				>
					Enable 2FA
				</LoadingButton>
			</form>
		{/if}
	</Card.Content>
</Card.Root>

<UnsavedChangesDialog
	open={confirmCloseCodes}
	title="Backup codes not saved"
	description="The codes are shown once."
	confirmLabel="Close without saving"
	cancelLabel="Back"
	onOpenChange={(o) => (confirmCloseCodes = o)}
	onConfirm={() => {
		confirmCloseCodes = false;
		closeSetup();
	}}
/>

<UnsavedChangesDialog
	bind:open={showLeaveDialog}
	title={backupCodes ? 'Backup codes not saved' : 'Discard two-factor setup'}
	description={backupCodes ? 'The codes are shown once.' : 'Enrollment is discarded.'}
	confirmLabel={backupCodes ? 'Leave' : 'Discard setup'}
	cancelLabel={backupCodes ? 'Back' : 'Continue setup'}
	onOpenChange={(o) => {
		showLeaveDialog = o;
		if (!o) pendingNav = null;
	}}
	onConfirm={() => {
		showLeaveDialog = false;
		const resume = pendingNav;
		pendingNav = null;
		resume?.();
	}}
/>
