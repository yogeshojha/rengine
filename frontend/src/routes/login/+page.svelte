<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$stores/auth.svelte';
	import { Button, Input, Card, CardHeader, CardTitle, CardDescription, CardContent } from '$components/ui';
	import { Radar } from 'lucide-svelte';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let isLoading = $state(false);

	// Redirect if already authenticated
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

<div class="min-h-screen flex items-center justify-center bg-background p-4">
	<Card class="w-full max-w-md">
		<CardHeader class="text-center">
			<div class="flex justify-center mb-4">
				<Radar class="h-12 w-12 text-primary" />
			</div>
			<CardTitle>Welcome Back</CardTitle>
			<CardDescription>Sign in to your reNgine account</CardDescription>
		</CardHeader>
		<CardContent>
			<form onsubmit={handleSubmit} class="space-y-4">
				<div class="space-y-2">
					<label for="username" class="text-sm font-medium">Username</label>
					<Input
						id="username"
						type="text"
						placeholder="username"
						bind:value={username}
						required
					/>
				</div>

				<div class="space-y-2">
					<label for="password" class="text-sm font-medium">Password</label>
					<Input
						id="password"
						type="password"
						placeholder="••••••••"
						bind:value={password}
						required
					/>
				</div>

				{#if error}
					<p class="text-sm text-destructive">{error}</p>
				{/if}

				<Button type="submit" class="w-full" disabled={isLoading}>
					{isLoading ? 'Signing in...' : 'Sign In'}
				</Button>
			</form>
		</CardContent>
	</Card>
</div>
