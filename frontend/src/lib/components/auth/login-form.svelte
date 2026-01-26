<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { FieldGroup, Field, FieldLabel } from '$lib/components/ui/field/index.js';

	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';

	import { cn } from '$lib/utils.js';
	import type { HTMLAttributes } from 'svelte/elements';
	import Eye from 'lucide-svelte/icons/eye';
	import EyeOff from 'lucide-svelte/icons/eye-off';

	let { class: className, ...restProps }: HTMLAttributes<HTMLDivElement> = $props();

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let isLoading = $state(false);
	let showPassword = $state(false);

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading) {
			goto('/dashboard');
		}
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		isLoading = true;

		const result = await auth.login(username, password);
		if (result.success) {
			goto('/dashboard');
		} else {
			error = result.error || 'Login failed';
		}

		isLoading = false;
	}
</script>

<div class={cn('flex flex-col gap-6 max-w-lg w-full', className)} {...restProps}>
	<Card.Root>
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
					<p class="text-sm text-red-600">{error}</p>
				{/if}
				<Button type="submit" class="w-full mt-4" disabled={isLoading}>
					{#if isLoading}
						Logging in...
					{:else}
						Log In
					{/if}
				</Button>
			</form>
		</Card.Content>
	</Card.Root>
</div>
