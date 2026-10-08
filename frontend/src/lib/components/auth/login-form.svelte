<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { FieldGroup, Field, FieldLabel, FieldError } from '$lib/components/ui/field/index.js';
	import OtpInput from '$lib/components/onboarding/otp-input.svelte';

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { ROUTES } from '$lib/config/routes';
	import { localPath } from '$lib/utilities/links';
	import { takeSessionExpired } from './login';
	import { auth, NO_SESSION } from '$lib/stores/auth.svelte';
	import { twoFactorApi } from '$lib/api/twoFactor';
	import { TOTP_DIGITS } from '$lib/constants';

	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let missing = $state<{ username?: boolean; password?: boolean }>({});
	let isLoading = $state(false);
	let showPassword = $state(false);
	let capsLock = $state(false);

	let usernameEl = $state<HTMLInputElement | null>(null);
	let passwordEl = $state<HTMLInputElement | null>(null);

	let mfaToken = $state<string | null>(null);
	let code = $state('');
	let mfaError = $state('');
	let verifying = $state(false);
	let useBackupCode = $state(false);

	let expired = $state(false);
	let next = $derived(localPath(page.url.searchParams.get('next')));

	let inMfa = $derived(mfaToken !== null);
	let canVerify = $derived(useBackupCode ? code.trim().length > 0 : code.length === TOTP_DIGITS);

	onMount(() => {
		expired = takeSessionExpired();
		usernameEl?.focus();
	});

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading) {
			goto(next && !next.startsWith(ROUTES.login) ? next : ROUTES.dashboard);
		}
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		// inline, like every other form, instead of the browser's required bubble
		missing = { username: !username.trim(), password: !password };
		if (missing.username || missing.password) {
			(missing.username ? usernameEl : passwordEl)?.focus();
			return;
		}
		isLoading = true;

		const result = await auth.login(username, password);
		if (result.mfaRequired) {
			mfaToken = result.mfaToken ?? null;
			code = '';
			mfaError = '';
			isLoading = false;
			return;
		}
		if (!result.success) {
			error = result.error || 'Not logged in';
			isLoading = false;
			password = '';
			passwordEl?.focus();
		}
	}

	async function verifyMfa() {
		if (!mfaToken || !canVerify || verifying) return;
		verifying = true;
		mfaError = '';
		try {
			await twoFactorApi.loginVerify(mfaToken, code.trim());
			await auth.checkAuth();
			if (!auth.isAuthenticated) {
				mfaError = NO_SESSION;
				code = '';
				verifying = false;
			}
		} catch (err) {
			mfaError = err instanceof Error ? err.message : 'Invalid code';
			code = '';
			verifying = false;
		}
	}

	function onCodeChange(v: string) {
		code = v;
		mfaError = '';
		if (v.length === TOTP_DIGITS) verifyMfa();
	}

	function backToPassword() {
		mfaToken = null;
		code = '';
		mfaError = '';
		password = '';
		useBackupCode = false;
	}

	function readCapsLock(e: KeyboardEvent) {
		capsLock = e.getModifierState?.('CapsLock') ?? false;
	}

	function toggleBackupCode() {
		useBackupCode = !useBackupCode;
		code = '';
		mfaError = '';
	}
</script>

<div class="flex w-full flex-col gap-6">
	<Card.Root>
		{#if inMfa}
			<Card.Header class="text-center">
				<div class="mx-auto mb-1 flex size-10 items-center justify-center rounded-lg bg-muted">
					<ShieldCheckIcon class="size-5 text-foreground" />
				</div>
				<Card.Title class="text-xl">Two-factor authentication</Card.Title>
				<Card.Description>
					{useBackupCode
						? 'Enter one of the backup codes saved at enrollment'
						: `Enter the ${TOTP_DIGITS}-digit code from the authenticator app`}
				</Card.Description>
			</Card.Header>
			<Card.Content>
				<div class="flex flex-col items-center gap-5">
					<div class="w-full space-y-2">
						<Label for="mfa-code" class="sr-only">
							{useBackupCode ? 'Backup code' : 'Authentication code'}
						</Label>
						{#if useBackupCode}
							<Input
								id="mfa-code"
								type="text"
								autocomplete="one-time-code"
								placeholder="0000-0000"
								class="text-center font-mono"
								disabled={verifying}
								bind:value={code}
							/>
						{:else}
							<OtpInput value={code} onValueChange={onCodeChange} disabled={verifying} />
						{/if}
					</div>
					{#if mfaError}
						<p class="text-sm text-destructive" role="alert">{mfaError}</p>
					{/if}
					<LoadingButton
						class="w-full"
						onclick={() => verifyMfa()}
						disabled={!canVerify}
						loading={verifying}
						loadingLabel="Verifying"
					>
						Verify
					</LoadingButton>
					<Button
						variant="link"
						size="sm"
						class="text-muted-foreground"
						onclick={toggleBackupCode}
						disabled={verifying}
					>
						{useBackupCode ? 'Use the authenticator app' : 'Use a backup code'}
					</Button>
					<Button
						variant="ghost"
						size="sm"
						class="text-muted-foreground"
						onclick={backToPassword}
						disabled={verifying}
					>
						<ArrowLeftIcon class="size-4" />
						Back
					</Button>
				</div>
			</Card.Content>
		{:else}
			<Card.Header class="text-center">
				<Card.Title class="text-xl">Log in</Card.Title>
				{#if expired}
					<Card.Description>Session expired. Log in again.</Card.Description>
				{/if}
			</Card.Header>
			<Card.Content>
				<form novalidate onsubmit={handleSubmit}>
					<FieldGroup>
						<Field>
							<FieldLabel for="username">Username</FieldLabel>
							<Input
								id="username"
								name="username"
								type="text"
								autocomplete="username"
								autocapitalize="none"
								autocorrect="off"
								spellcheck={false}
								required
								aria-invalid={missing.username || undefined}
								aria-describedby={missing.username ? 'username-error' : undefined}
								bind:ref={usernameEl}
								bind:value={username}
								oninput={() => (missing.username = false)}
							/>
							{#if missing.username}
								<FieldError id="username-error">Enter your username</FieldError>
							{/if}
						</Field>
						<Field>
							<FieldLabel for="password">Password</FieldLabel>
							<div class="relative">
								<Input
									id="password"
									name="password"
									type={showPassword ? 'text' : 'password'}
									autocomplete="current-password"
									bind:ref={passwordEl}
									bind:value={password}
									class="pr-10"
									required
									aria-invalid={missing.password || undefined}
									aria-describedby={missing.password ? 'password-error' : undefined}
									oninput={() => (missing.password = false)}
									onkeydown={readCapsLock}
									onkeyup={readCapsLock}
									onblur={() => (capsLock = false)}
								/>
								<button
									type="button"
									onclick={() => (showPassword = !showPassword)}
									class="absolute right-0 top-0 h-full px-3 py-2 text-muted-foreground hover:text-foreground"
									aria-label={showPassword ? 'Hide password' : 'Show password'}
								>
									{#if showPassword}
										<EyeOff class="h-4 w-4" />
									{:else}
										<Eye class="h-4 w-4" />
									{/if}
								</button>
							</div>
							{#if missing.password}
								<FieldError id="password-error">Enter your password</FieldError>
							{/if}
							{#if capsLock}
								<p class="text-xs text-warning" role="status">Caps Lock is on</p>
							{/if}
						</Field>
					</FieldGroup>
					{#if error}
						<p class="mt-3 text-sm text-destructive" role="alert">{error}</p>
					{/if}
					<LoadingButton
						type="submit"
						class="w-full mt-4"
						loading={isLoading}
						loadingLabel="Logging in"
					>
						Log in
					</LoadingButton>
				</form>
			</Card.Content>
		{/if}
	</Card.Root>
</div>
