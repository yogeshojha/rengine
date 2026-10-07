<script lang="ts">
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import { toast } from 'svelte-sonner';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import CheckIcon from '@lucide/svelte/icons/check';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { twoFactorApi } from '$lib/api/twoFactor';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { downloadBlob } from '$lib/utilities/download';
	import { TOTP_DIGITS } from '$lib/constants';
	import OtpInput from './otp-input.svelte';
	import type { StepProps } from '$lib/types/onboarding';

	let { data, next, setFooter }: StepProps = $props();

	type Phase = 'intro' | 'enroll' | 'done';
	let phase = $state<Phase>(data.twoFactorEnabled ? 'done' : 'intro');

	onMount(async () => {
		if (data.twoFactorEnabled) return;
		try {
			if (!(await twoFactorApi.status()).enabled) return;
		} catch {
			return;
		}
		data.twoFactorEnabled = true;
		if (phase === 'intro') phase = 'done';
	});

	let setupLoading = $state(false);
	let verifying = $state(false);

	let busy = $derived(setupLoading || verifying);

	$effect(() => {
		setFooter({
			onNext: next,
			nextLabel: 'Continue',
			nextLoading: busy,
			nextLoadingLabel: verifying ? 'Verifying' : 'Preparing',
			nextDisabled: hasBackupCodes && !backupCodesAck,
			canSkip: !hasBackupCodes
		});
	});

	let password = $state('');
	let qr = $state('');
	let qrFailed = $state(false);
	let secret = $state('');
	let code = $state('');
	let errorMsg = $state('');
	let failCount = $state(0);
	let backupCodes = $state<string[]>([]);
	let manualOpen = $state(false);

	let hasBackupCodes = $derived(backupCodes.length > 0);
	let backupCodesAck = $state(false);
	let copiedCodes = $state(false);

	let groupedSecret = $derived(secret.replace(/(.{4})/g, '$1 ').trim());
	let showClockHint = $derived(failCount >= 2);

	async function startSetup() {
		if (!password) return;
		setupLoading = true;
		try {
			const res = await twoFactorApi.setup(password);
			password = '';
			qr = res.qr;
			qrFailed = false;
			secret = res.secret;
			code = '';
			phase = 'enroll';
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Two-factor setup not started');
		} finally {
			setupLoading = false;
		}
	}

	async function verify() {
		if (code.length !== TOTP_DIGITS) {
			errorMsg = `Enter the ${TOTP_DIGITS}-digit code from the authenticator app.`;
			return;
		}
		verifying = true;
		errorMsg = '';
		try {
			const res = await twoFactorApi.verify(code);
			backupCodes = res.backup_codes;
			data.twoFactorEnabled = true;
			phase = 'done';
			failCount = 0;
			toast.success('Two-factor authentication enabled');
		} catch (e) {
			failCount += 1;
			errorMsg = e instanceof Error ? e.message : 'Code not accepted. Enter the current code.';
			code = '';
		} finally {
			verifying = false;
		}
	}

	async function copyCodes() {
		if (await writeClipboard(backupCodes.join('\n'))) {
			copiedCodes = true;
			setTimeout(() => (copiedCodes = false), 2000);
		} else {
			toast.error('Backup codes not copied');
		}
	}

	function downloadCodes() {
		downloadBlob('rengine-backup-codes.txt', backupCodes.join('\n') + '\n');
	}

	function onCodeChange(v: string) {
		code = v;
		if (errorMsg) errorMsg = '';
		if (v.length === TOTP_DIGITS && !verifying) verify();
	}
</script>

{#if phase === 'intro'}
	<div class="rounded-lg border p-4">
		<div class="flex items-start gap-3">
			<div
				class="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-muted text-foreground"
			>
				<ShieldCheckIcon class="size-[18px]" />
			</div>
			<div class="flex-1 space-y-0.5">
				<h3 class="text-sm font-semibold">Authenticator app</h3>
				<p class="text-xs text-muted-foreground">
					Google Authenticator, 1Password, Authy or any TOTP app.
				</p>
			</div>
		</div>
		<form
			class="mt-4 space-y-3"
			onsubmit={(e) => {
				e.preventDefault();
				startSetup();
			}}
		>
			<FormField label="Current password">
				{#snippet children({ id })}
					<Input
						{id}
						type="password"
						autocomplete="current-password"
						class="max-w-72"
						disabled={setupLoading}
						bind:value={password}
					/>
				{/snippet}
			</FormField>
			<LoadingButton
				type="submit"
				loading={setupLoading}
				loadingLabel="Preparing"
				disabled={!password}
			>
				Set up two-factor
			</LoadingButton>
		</form>
	</div>
{:else if phase === 'enroll'}
	<div class="grid gap-8 sm:grid-cols-[auto_1fr] sm:items-start">
		<div class="flex flex-col items-center gap-3">
			{#if qrFailed}
				<div
					class="flex size-56 flex-col items-center justify-center gap-1.5 rounded-xl border bg-muted p-4 text-center"
				>
					<p class="text-sm font-medium">QR code unavailable</p>
					<p class="text-xs text-muted-foreground">Use the manual key.</p>
				</div>
			{:else}
				<div class="rounded-xl border bg-white p-4 shadow-sm">
					<img
						src={qr}
						alt="Two-factor enrollment QR code"
						class="size-56"
						onerror={() => (qrFailed = true)}
					/>
				</div>
			{/if}
			<p class="max-w-[12rem] text-center text-xs text-muted-foreground">
				Scan with an authenticator app.
			</p>
		</div>

		<div class="space-y-4">
			<FormField label="Enter the {TOTP_DIGITS}-digit code" error={errorMsg || undefined}>
				{#snippet children({ id })}
					<OtpInput {id} value={code} onValueChange={onCodeChange} disabled={verifying} />
				{/snippet}
			</FormField>

			{#if showClockHint}
				<p class="flex items-start gap-1.5 text-xs text-warning">
					<TriangleAlertIcon class="mt-px size-3.5 shrink-0" />
					<span>Check that the device clock is set automatically.</span>
				</p>
			{/if}

			<LoadingButton
				class="w-full sm:w-auto"
				onclick={verify}
				loading={verifying}
				loadingLabel="Verifying"
				disabled={code.length !== TOTP_DIGITS}
			>
				Verify and enable
			</LoadingButton>

			<Collapsible.Root bind:open={manualOpen} class="pt-1">
				<Collapsible.Trigger
					class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
				>
					Enter the key manually
					<ChevronDownIcon class="size-3.5 transition-transform {manualOpen ? 'rotate-180' : ''}" />
				</Collapsible.Trigger>
				<Collapsible.Content class="pt-2.5">
					<div class="flex items-center gap-2">
						<code
							class="flex-1 select-all rounded-md bg-muted px-3 py-2 font-mono text-sm tracking-[0.15em]"
						>
							{groupedSecret}
						</code>
						<CopyButton value={secret} class="size-9" />
					</div>
				</Collapsible.Content>
			</Collapsible.Root>
		</div>
	</div>
{:else}
	<div class="space-y-6">
		<Alert.Root>
			<ShieldCheckIcon class="size-4" />
			<Alert.Title>Two-factor authentication is on</Alert.Title>
			<Alert.Description>A code is required at each login.</Alert.Description>
		</Alert.Root>

		{#if backupCodes.length}
			<div class="rounded-lg border p-4">
				<div class="flex items-start justify-between gap-3">
					<div class="flex items-center gap-2">
						<KeyRoundIcon class="size-4 text-muted-foreground" />
						<h3 class="text-sm font-semibold">Backup codes</h3>
					</div>
					<div class="flex shrink-0 items-center gap-1">
						<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={copyCodes}>
							{#if copiedCodes}
								<CheckIcon class="size-4 text-foreground" />
								Copied
							{:else}
								<CopyIcon class="size-4" />
								Copy all
							{/if}
						</Button>
						<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={downloadCodes}>
							<DownloadIcon class="size-4" />
							Download .txt
						</Button>
					</div>
				</div>
				<p class="mt-1 text-xs text-muted-foreground">
					Each code signs in once when the authenticator is unavailable. Shown once.
				</p>
				<div class="mt-4 grid grid-cols-2 gap-2.5">
					{#each backupCodes as bc (bc)}
						<code
							class="select-all rounded-md bg-muted px-3 py-1.5 text-center font-mono text-sm tracking-wide"
						>
							{bc}
						</code>
					{/each}
				</div>
				<Label
					class="mt-4 flex cursor-pointer items-center gap-2 font-normal text-muted-foreground"
				>
					<Checkbox bind:checked={backupCodesAck} />
					Backup codes saved
				</Label>
			</div>
		{/if}
	</div>
{/if}
