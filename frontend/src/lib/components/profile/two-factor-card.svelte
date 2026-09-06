<script lang="ts">
	import { onMount } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { twoFactorApi } from '$lib/api/twoFactor';
	import OtpInput from '$lib/components/onboarding/otp-input.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as AlertDialog from '$lib/components/ui/alert-dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
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
			toast.error(error instanceof Error ? error.message : 'Two-factor status could not be loaded');
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
			toast.error(error instanceof Error ? error.message : 'Two-factor setup could not be started');
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
		if (await writeClipboard(backupCodes.join('\n'))) {
			copiedBackup = true;
			backupCodesSaved = true;
			setTimeout(() => (copiedBackup = false), 2000);
		} else {
			toast.error('Copy failed');
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
					<Card.Title>Two-Factor Authentication</Card.Title>
					{#if !twoFactorLoading}
						{#if twoFactorEnabled}
							<Badge variant="secondary" class="h-5 text-xs px-2 border-0">Enabled</Badge>
						{:else}
							<Badge variant="secondary" class="h-5 text-xs px-2">Disabled</Badge>
						{/if}
					{/if}
				</div>
				<Card.Description>Require a time-based one-time code at sign-in.</Card.Description>
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
				This account is protected by an authenticator app.
			</div>

			{#if disableOpen}
				<Separator />
				<div class="space-y-3">
					<Alert.Root variant="destructive">
						<TriangleAlertIcon class="size-4" />
						<Alert.Title>Disable two-factor authentication?</Alert.Title>
						<Alert.Description>
							This removes the second factor and invalidates all backup codes. The password alone
							will grant access.
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
						<LoadingButton
							variant="destructive"
							onclick={handleDisable}
							loading={isDisabling}
							loadingLabel="Disabling…"
							disabled={disableCode.length !== 6}
						>
							Disable 2FA
						</LoadingButton>
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
						Shown only once. Store them securely. Each code can be used once if the authenticator is
						unavailable.
					</Alert.Description>
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
							<img src={setupQr} alt="2FA QR code" class="size-40 rounded-md border bg-white p-2" />
						{/if}
					</div>
					<div class="space-y-3">
						<div class="space-y-1">
							<p class="text-sm font-medium">Scan the QR code</p>
							<p class="text-xs text-muted-foreground">
								Scan the code with an authenticator app such as 1Password, Authy or Google
								Authenticator, or enter the secret manually.
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
							<LoadingButton
								onclick={handleVerify}
								loading={isVerifying}
								loadingLabel="Verifying…"
								disabled={setupCode.length !== 6}
							>
								Verify &amp; enable
							</LoadingButton>
							<Button variant="ghost" onclick={closeSetup} disabled={isVerifying}>Cancel</Button>
						</div>
					</div>
				</div>
			{/if}
		{:else}
			<div class="flex items-center gap-2 text-sm text-muted-foreground">
				<TriangleAlertIcon class="w-4 h-4 text-muted-foreground shrink-0" />
				Two-factor authentication is not enabled on this account.
			</div>
			<LoadingButton onclick={handleStartSetup} loading={isSettingUp} loadingLabel="Preparing…">
				Enable 2FA
			</LoadingButton>
		{/if}
	</Card.Content>
</Card.Root>

<AlertDialog.Root bind:open={confirmCloseCodes}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Backup codes not saved</AlertDialog.Title>
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

<UnsavedChangesDialog
	bind:open={showLeaveDialog}
	title="Discard two-factor setup?"
	description="Two-factor enrollment is unfinished. Leaving now discards it and two-factor stays off."
	confirmLabel="Discard setup"
	cancelLabel="Keep setting up"
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
