<script lang="ts">
	import { ROLE_LABELS, roleLabel } from '$lib/config/users';
	import { pageTitle } from '$lib/utilities/page-title';
	import { routeLabels } from '$lib/config/routes';
	import { auth } from '$lib/stores/auth.svelte';
	import ChangeUsernameCard from '$lib/components/profile/change-username-card.svelte';
	import ChangePasswordCard from '$lib/components/profile/change-password-card.svelte';
	import TwoFactorCard from '$lib/components/profile/two-factor-card.svelte';
	import SidebarItems from '$lib/components/layout/sidebar-items.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import { sidebarLayout } from '$lib/stores/sidebar-layout.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import PageHeader from '$lib/components/page-header.svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Avatar from '$lib/components/ui/avatar/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import MailIcon from '@lucide/svelte/icons/mail';
	import CheckCircleIcon from '@lucide/svelte/icons/check-circle';
	import CircleSlashIcon from '@lucide/svelte/icons/circle-slash';
	import { formatDate } from '$lib/utilities/dates';
	import { getInitials } from '$lib/utilities/strings';
</script>

<svelte:head><title>{pageTitle(routeLabels.profile)}</title></svelte:head>

<div class="flex w-full max-w-5xl flex-col gap-6">
	<PageHeader
		title={routeLabels.profile}
		description="Account details, password, two-factor authentication and sidebar"
	/>

	<Card.Root class="overflow-hidden">
		<Card.Content class="pt-0">
			<div>
				<div class="flex items-center gap-4">
					<Avatar.Root class="size-14 rounded-md border">
						<Avatar.Fallback
							class="rounded-md bg-primary text-primary-foreground text-lg font-semibold"
						>
							{getInitials(auth.user?.username || 'U')}
						</Avatar.Fallback>
					</Avatar.Root>

					<div class="min-w-0 flex-1">
						<div class="flex flex-wrap items-baseline gap-x-2 mb-0.5">
							<h2 class="text-xl font-semibold">{auth.user?.username}</h2>
							{#if auth.user?.is_superuser}
								<Badge variant="secondary" class="h-5 text-xs px-2">{ROLE_LABELS.admin}</Badge>
							{/if}
						</div>
						<div class="flex flex-wrap items-center gap-x-3 text-sm text-muted-foreground">
							<span class="flex min-w-0 items-center gap-1.5 wrap-anywhere">
								<MailIcon class="w-3.5 h-3.5 shrink-0" />
								{auth.user?.email}
							</span>
							<span class="text-xs">•</span>
							<span class="flex items-center gap-1.5">
								{#if auth.user?.is_active}
									<CheckCircleIcon class="w-3.5 h-3.5 text-foreground" />
									Active
								{:else}
									<CircleSlashIcon class="w-3.5 h-3.5 text-muted-foreground" />
									Inactive
								{/if}
							</span>
						</div>
					</div>
				</div>
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
			<Card.Title>Sidebar</Card.Title>
			<Card.Description>Applies to this account in this browser</Card.Description>
			{#if sidebarLayout.customized}
				<Card.Action>
					<Button variant="ghost" size="sm" onclick={() => sidebarLayout.reset()}>Show all</Button>
				</Card.Action>
			{/if}
		</Card.Header>
		<Card.Content>
			<SidebarItems />
		</Card.Content>
	</Card.Root>

	<Card.Root>
		<Card.Header>
			<Card.Title>Account information</Card.Title>
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
						{roleLabel(auth.user?.is_superuser ?? false)}
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
