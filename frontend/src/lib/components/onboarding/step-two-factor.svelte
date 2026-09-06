<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { toast } from 'svelte-sonner';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import CheckIcon from '@lucide/svelte/icons/check';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { twoFactorApi } from '$lib/api/twoFactor';
	import OtpInput from './otp-input.svelte';
	import type { StepProps } from '$lib/types/onboarding';

	let { data, next, setFooter }: StepProps = $props();

	type Phase = 'intro' | 'enroll' | 'done';
	let phase = $state<Phase>(data.twoFactorEnabled ? 'done' : 'intro');

	let setupLoading = $state(false);
	let verifying = $state(false);

	let busy = $derived(setupLoading || verifying);

	$effect(() => {
		setFooter({
			onNext: next,
			nextLabel: 'Continue',
			nextLoading: busy,
			nextDisabled: hasBackupCodes && !backupCodesAck,
			canSkip: !hasBackupCodes
		});
	});

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
		setupLoading = true;
		try {
			const res = await twoFactorApi.setup();
			qr = res.qr;
			qrFailed = false;
			secret = res.secret;
			code = '';
			phase = 'enroll';
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Two-factor setup could not be started');
		} finally {
			setupLoading = false;
		}
	}

	async function verify() {
		if (code.length !== 6) {
			errorMsg = 'Enter the 6-digit code from your authenticator app.';
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
			errorMsg =
				e instanceof Error ? e.message : 'That code was not accepted. Enter the current code.';
			code = '';
		} finally {
			verifying = false;
		}
	}

	async function writeClipboard(text: string): Promise<boolean> {
		if (navigator.clipboard && window.isSecureContext) {
			try {
				await navigator.clipboard.writeText(text);
				return true;
			} catch {}
		}
		try {
			const ta = document.createElement('textarea');
			ta.value = text;
			ta.style.position = 'fixed';
			ta.style.opacity = '0';
			document.body.appendChild(ta);
			ta.focus();
			ta.select();
			const ok = document.execCommand('copy');
			ta.remove();
			return ok;
		} catch {
			return false;
		}
	}

	async function copyCodes() {
		if (await writeClipboard(backupCodes.join('\n'))) {
			copiedCodes = true;
			setTimeout(() => (copiedCodes = false), 2000);
		} else {
			toast.error('Copy failed');
		}
	}

	function downloadCodes() {
		const blob = new Blob([backupCodes.join('\n') + '\n'], { type: 'text/plain' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'rengine-2fa-backup-codes.txt';
		a.click();
		URL.revokeObjectURL(url);
	}

	function onCodeChange(v: string) {
		code = v;
		if (errorMsg) errorMsg = '';
		if (v.length === 6 && !verifying) verify();
	}
</script>

{#if phase === 'intro'}
	<div class="rounded-xl border bg-card p-6">
		<div class="flex items-start gap-4">
			<div
				class="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-muted text-foreground"
			>
				<ShieldCheckIcon class="size-[18px]" />
			</div>
			<div class="flex-1 space-y-1">
				<h3 class="text-sm font-medium">Authenticator app</h3>
				<p class="text-sm text-muted-foreground">
					Works with Google Authenticator, 1Password, Authy and similar apps. Scan a QR code, then
					confirm with a 6-digit code.
				</p>
			</div>
		</div>
		<Button class="mt-6" onclick={startSetup} disabled={setupLoading}>
			{#if setupLoading}<Spinner class="mr-2" />{/if}
			Set up two-factor
		</Button>
	</div>
{:else if phase === 'enroll'}
	<div class="grid gap-8 sm:grid-cols-[auto_1fr] sm:items-start">
		<div class="flex flex-col items-center gap-3">
			{#if qrFailed}
				<div
					class="flex size-56 flex-col items-center justify-center gap-1.5 rounded-xl border bg-muted p-4 text-center"
				>
					<p class="text-sm font-medium">QR code unavailable</p>
					<p class="text-xs text-muted-foreground">Use the manual key instead.</p>
				</div>
			{:else}
				<div class="rounded-xl border bg-white p-4 shadow-sm">
					<img
						src={qr}
						alt="QR code for enrolling this account in an authenticator app"
						class="size-56"
						onerror={() => (qrFailed = true)}
					/>
				</div>
			{/if}
			<p class="max-w-[12rem] text-center text-xs text-muted-foreground">
				Scan with your authenticator app.
			</p>
		</div>

		<div class="space-y-4">
			<div class="space-y-1">
				<Label class="text-sm font-medium">Enter the 6-digit code</Label>
				<p class="text-xs text-muted-foreground">Type the code your authenticator app shows.</p>
			</div>
			<OtpInput value={code} onValueChange={onCodeChange} disabled={verifying} />

			{#if errorMsg}
				<p class="text-xs text-destructive">{errorMsg}</p>
			{/if}
			{#if showClockHint}
				<p class="flex items-start gap-1.5 text-xs text-warning">
					<TriangleAlertIcon class="mt-px size-3.5 shrink-0" />
					<span
						>If codes are repeatedly rejected, check that the device clock is set to update
						automatically.</span
					>
				</p>
			{/if}

			<Button class="w-full sm:w-auto" onclick={verify} disabled={verifying || code.length !== 6}>
				{#if verifying}<Spinner class="mr-2" />{/if}
				Verify and enable
			</Button>

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
			<Alert.Description>
				A code from the authenticator app is required at the next sign-in.
			</Alert.Description>
		</Alert.Root>

		{#if backupCodes.length}
			<div class="rounded-xl border bg-card p-5">
				<div class="flex items-start justify-between gap-3">
					<div class="flex items-center gap-2">
						<KeyRoundIcon class="size-4 text-muted-foreground" />
						<h3 class="text-sm font-medium">Backup codes</h3>
					</div>
					<div class="flex shrink-0 items-center gap-1">
						<Button variant="ghost" size="sm" class="h-7 gap-1.5 px-2 text-xs" onclick={copyCodes}>
							{#if copiedCodes}
								<CheckIcon class="size-4 text-foreground" />
								Copied
							{:else}
								<CopyIcon class="size-4" />
								Copy all
							{/if}
						</Button>
						<Button
							variant="ghost"
							size="sm"
							class="h-7 gap-1.5 px-2 text-xs"
							onclick={downloadCodes}
						>
							<DownloadIcon class="size-4" />
							Download .txt
						</Button>
					</div>
				</div>
				<p class="mt-1 text-xs text-muted-foreground">
					Store these securely. Each code can be used once if the authenticator is unavailable. They
					are shown only now.
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
					class="mt-4 flex cursor-pointer items-center gap-2 text-xs font-normal text-muted-foreground"
				>
					<Checkbox bind:checked={backupCodesAck} />
					Backup codes saved
				</Label>
			</div>
		{/if}
	</div>
{/if}
