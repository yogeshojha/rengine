<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$stores/auth.svelte';
	import { Button } from '$components/ui';
	import {
		LayoutDashboard,
		Target,
		Radar,
		Settings,
		LogOut,
		Menu,
		X
	} from 'lucide-svelte';

	let mobileMenuOpen = $state(false);

	const navItems = [
		{ href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
		{ href: '/targets', label: 'Targets', icon: Target },
		{ href: '/scans', label: 'Scans', icon: Radar },
		{ href: '/settings', label: 'Settings', icon: Settings }
	];

	function isActive(href: string): boolean {
		return $page.url.pathname.startsWith(href);
	}

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}
</script>

<nav class="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
	<div class="container flex h-16 items-center justify-between">
		<!-- Logo -->
		<a href="/dashboard" class="flex items-center space-x-2">
			<Radar class="h-6 w-6 text-primary" />
			<span class="text-xl font-bold">reNgine</span>
		</a>

		<!-- Desktop Navigation -->
		<div class="hidden md:flex md:items-center md:space-x-1">
			{#each navItems as item}
				<a
					href={item.href}
					class="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors {isActive(item.href)
						? 'bg-accent text-accent-foreground'
						: 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}"
				>
					<item.icon class="h-4 w-4" />
					<span>{item.label}</span>
				</a>
			{/each}
		</div>

		<!-- User Menu -->
		<div class="hidden md:flex md:items-center md:space-x-4">
			<span class="text-sm text-muted-foreground">
				{auth.user?.username}
			</span>
			<Button variant="ghost" size="icon" onclick={() => auth.logout()}>
				<LogOut class="h-4 w-4" />
			</Button>
		</div>

		<!-- Mobile Menu Button -->
		<Button variant="ghost" size="icon" class="md:hidden" onclick={toggleMobileMenu}>
			{#if mobileMenuOpen}
				<X class="h-5 w-5" />
			{:else}
				<Menu class="h-5 w-5" />
			{/if}
		</Button>
	</div>

	<!-- Mobile Navigation -->
	{#if mobileMenuOpen}
		<div class="md:hidden border-t">
			<div class="container py-4 space-y-2">
				{#each navItems as item}
					<a
						href={item.href}
						onclick={() => (mobileMenuOpen = false)}
						class="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors {isActive(item.href)
							? 'bg-accent text-accent-foreground'
							: 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}"
					>
						<item.icon class="h-4 w-4" />
						<span>{item.label}</span>
					</a>
				{/each}
				<div class="pt-4 border-t">
					<div class="flex items-center justify-between px-3 py-2">
						<span class="text-sm text-muted-foreground">{auth.user?.username}</span>
						<Button variant="ghost" size="sm" onclick={() => auth.logout()}>
							<LogOut class="h-4 w-4 mr-2" />
							Logout
						</Button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</nav>
