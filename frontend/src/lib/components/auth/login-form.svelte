<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { FieldGroup, Field, FieldLabel } from '$lib/components/ui/field/index.js';
	import OtpInput from '$lib/components/onboarding/otp-input.svelte';

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { auth } from '$lib/stores/auth.svelte';
	import { twoFactorApi } from '$lib/api/twoFactor';

	import { cn } from '$lib/utils.js';
	import type { HTMLAttributes } from 'svelte/elements';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';

	let { class: className, ...restProps }: HTMLAttributes<HTMLDivElement> = $props();

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let isLoading = $state(false);
	let showPassword = $state(false);

	let usernameEl = $state<HTMLInputElement | null>(null);
	let passwordEl = $state<HTMLInputElement | null>(null);

	let mfaToken = $state<string | null>(null);
	let code = $state('');
	let mfaError = $state('');
	let verifying = $state(false);

	let inMfa = $derived(mfaToken !== null);

	onMount(() => usernameEl?.focus());

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading) {
			goto(ROUTES.dashboard);
		}
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
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
			error = result.error || 'Login failed';
			isLoading = false;
			password = '';
			passwordEl?.focus();
		}
	}

	async function verifyMfa() {
		if (!mfaToken || code.length !== 6 || verifying) return;
		verifying = true;
		mfaError = '';
		try {
			await twoFactorApi.loginVerify(mfaToken, code);
			await auth.checkAuth();
		} catch (err) {
			mfaError = err instanceof Error ? err.message : 'Invalid code, try again';
			code = '';
			verifying = false;
		}
	}

	function onCodeChange(v: string) {
		code = v;
		mfaError = '';
		if (v.length === 6) verifyMfa();
	}

	function backToPassword() {
		mfaToken = null;
		code = '';
		mfaError = '';
		password = '';
	}
</script>

<div class={cn('flex w-full flex-col gap-6', className)} {...restProps}>
	<Card.Root>
		{#if inMfa}
			<Card.Header class="text-center">
				<div class="mx-auto mb-1 flex size-10 items-center justify-center rounded-lg bg-muted">
					<ShieldCheckIcon class="size-5 text-foreground" />
				</div>
				<Card.Title class="text-xl">Two-factor authentication</Card.Title>
				<Card.Description>Enter the 6-digit code from your authenticator app</Card.Description>
			</Card.Header>
			<Card.Content>
				<div class="flex flex-col items-center gap-5">
					<div class="space-y-2">
						<Label class="sr-only">Authentication code</Label>
						<OtpInput value={code} onValueChange={onCodeChange} disabled={verifying} />
					</div>
					{#if mfaError}
						<p class="text-sm text-destructive">{mfaError}</p>
					{/if}
					<Button class="w-full" onclick={verifyMfa} disabled={verifying || code.length !== 6}>
						{#if verifying}<Spinner class="mr-2" />Verifying...{:else}Verify{/if}
					</Button>
					<Button
						variant="ghost"
						size="sm"
						class="text-muted-foreground"
						onclick={backToPassword}
						disabled={verifying}
					>
						<ArrowLeftIcon class="mr-1.5 size-4" />
						Back
					</Button>
				</div>
			</Card.Content>
		{:else}
			<Card.Header class="text-center">
				<Card.Title class="text-xl">Welcome back</Card.Title>
				<Card.Description>Sign in to your reNgine account</Card.Description>
			</Card.Header>
			<Card.Content>
				<form onsubmit={handleSubmit}>
					<FieldGroup>
						<Field>
							<FieldLabel for="username">Username</FieldLabel>
							<Input
								id="username"
								type="text"
								placeholder="username"
								required
								bind:ref={usernameEl}
								bind:value={username}
							/>
						</Field>
						<Field>
							<div class="flex items-center">
								<FieldLabel for="password">Password</FieldLabel>
							</div>
							<div class="relative">
								<Input
									id="password"
									type={showPassword ? 'text' : 'password'}
									bind:ref={passwordEl}
									bind:value={password}
									class="pr-10"
									required
								/>
								<button
									type="button"
									onclick={() => (showPassword = !showPassword)}
									class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
									aria-label={showPassword ? 'Hide password' : 'Show password'}
								>
									{#if showPassword}
										<EyeOff class="h-4 w-4 text-muted-foreground" />
									{:else}
										<Eye class="h-4 w-4 text-muted-foreground" />
									{/if}
								</button>
							</div>
						</Field>
					</FieldGroup>
					{#if error}
						<p class="text-sm text-destructive">{error}</p>
					{/if}
					<Button type="submit" class="w-full mt-4" disabled={isLoading}>
						{#if isLoading}<Spinner class="mr-2" />Logging in...{:else}Log In{/if}
					</Button>
				</form>
			</Card.Content>
		{/if}
	</Card.Root>
</div>
