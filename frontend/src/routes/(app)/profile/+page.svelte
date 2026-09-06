<script lang="ts">
	import { auth } from '$lib/stores/auth.svelte';
	import ChangeUsernameCard from '$lib/components/profile/change-username-card.svelte';
	import ChangePasswordCard from '$lib/components/profile/change-password-card.svelte';
	import TwoFactorCard from '$lib/components/profile/two-factor-card.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Avatar from '$lib/components/ui/avatar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import MailIcon from '@lucide/svelte/icons/mail';
	import CheckCircleIcon from '@lucide/svelte/icons/check-circle';
	import { formatDate } from '$lib/utilities';
	import { getInitials } from '$lib/utilities';
</script>

<div class="container max-w-5xl mx-auto space-y-6">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">Account and security</h1>
		<p class="text-sm text-muted-foreground">Credentials and two-factor authentication</p>
	</div>

	<Card.Root class="overflow-hidden">
		<Card.Content class="pt-0">
			<div class="mb-6">
				<div class="flex items-center gap-4 mb-4">
					<Avatar.Root class="size-14 rounded-md border">
						<Avatar.Fallback
							class="rounded-md bg-primary text-primary-foreground text-lg font-semibold"
						>
							{getInitials(auth.user?.username || 'U')}
						</Avatar.Fallback>
					</Avatar.Root>

					<div class="flex-1">
						<div class="flex items-baseline gap-2 mb-0.5">
							<h2 class="text-xl font-semibold">{auth.user?.username}</h2>
							{#if auth.user?.is_superuser}
								<Badge variant="secondary" class="h-5 text-xs px-2">Administrator</Badge>
							{/if}
						</div>
						<div class="flex items-center gap-3 text-sm text-muted-foreground">
							<span class="flex items-center gap-1.5">
								<MailIcon class="w-3.5 h-3.5" />
								{auth.user?.email}
							</span>
							<span class="text-xs">•</span>
							<span class="flex items-center gap-1.5">
								<CheckCircleIcon class="w-3.5 h-3.5 text-foreground" />
								Active
							</span>
						</div>
					</div>
				</div>
				<Separator />
			</div>
		</Card.Content>
	</Card.Root>

	<div class="grid gap-6 md:grid-cols-2">
		<ChangeUsernameCard />
		<ChangePasswordCard />
	</div>

	<TwoFactorCard />

	<Card.Root>
		<Card.Header>
			<Card.Title>Account information</Card.Title>
			<Card.Description>Account details and status</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">User ID</p>
					<div class="flex items-center gap-1.5">
						<p class="text-sm font-mono break-all">{auth.user?.id}</p>
						{#if auth.user?.id}
							<CopyButton value={auth.user.id} />
						{/if}
					</div>
				</div>

				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">Account type</p>
					<p class="text-sm">
						{auth.user?.is_superuser ? 'Administrator' : 'Standard user'}
					</p>
				</div>

				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">Email address</p>
					<p class="text-sm">{auth.user?.email}</p>
				</div>

				<div class="space-y-1">
					<p class="text-sm font-medium text-muted-foreground">Account status</p>
					<p class="text-sm">
						{auth.user?.is_active ? 'Active' : 'Inactive'}
					</p>
				</div>

				{#if auth.user?.created_at}
					<div class="space-y-1">
						<p class="text-sm font-medium text-muted-foreground">Member since</p>
						<p class="text-sm">{formatDate(auth.user.created_at)}</p>
					</div>
				{/if}

				{#if auth.user?.updated_at}
					<div class="space-y-1">
						<p class="text-sm font-medium text-muted-foreground">Last updated</p>
						<p class="text-sm">{formatDate(auth.user.updated_at)}</p>
					</div>
				{/if}
			</div>
		</Card.Content>
	</Card.Root>
</div>
