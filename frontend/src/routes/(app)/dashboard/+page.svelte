<script lang="ts">
	import { auth } from '$lib/stores/auth.svelte';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui';
	import { Target, Radar, AlertTriangle, Globe } from 'lucide-svelte';

	// Placeholder stats - will be replaced with actual data
	const stats = [
		{ label: 'Total Targets', value: '0', icon: Target },
		{ label: 'Total Scans', value: '0', icon: Radar },
		{ label: 'Vulnerabilities', value: '0', icon: AlertTriangle },
		{ label: 'Subdomains', value: '0', icon: Globe }
	];
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold">Dashboard</h1>
		<p class="text-muted-foreground">Welcome back, {auth.user?.username}</p>
	</div>

	<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
		{#each stats as stat}
			<Card>
				<CardHeader class="flex flex-row items-center justify-between pb-2">
					<CardTitle class="text-sm font-medium text-muted-foreground">
						{stat.label}
					</CardTitle>
					<stat.icon class="h-4 w-4 text-muted-foreground" />
				</CardHeader>
				<CardContent>
					<div class="text-2xl font-bold">{stat.value}</div>
				</CardContent>
			</Card>
		{/each}
	</div>

	<div class="grid gap-4 md:grid-cols-2">
		<Card>
			<CardHeader>
				<CardTitle>Recent Scans</CardTitle>
			</CardHeader>
			<CardContent>
				<p class="text-sm text-muted-foreground">No scans yet. Start by adding a target.</p>
			</CardContent>
		</Card>

		<Card>
			<CardHeader>
				<CardTitle>Recent Vulnerabilities</CardTitle>
			</CardHeader>
			<CardContent>
				<p class="text-sm text-muted-foreground">No vulnerabilities found yet.</p>
			</CardContent>
		</Card>
	</div>
</div>
