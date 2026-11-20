<script lang="ts">
	import { ROLE_LABELS, roleLabel } from '$lib/config/users';
	import { pageTitle } from '$lib/utilities/page-title';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import {
		PROFILE_TAB_LABELS,
		PROFILE_TABS,
		ROUTES,
		routeLabels,
		type ProfileTab
	} from '$lib/config/routes';
	import { LIMIT_DETAIL, MAX_ACCESS_KEYS } from '$lib/config/access-keys';
	import { auth } from '$lib/stores/auth.svelte';
	import ChangeUsernameCard from '$lib/components/profile/change-username-card.svelte';
	import ChangePasswordCard from '$lib/components/profile/change-password-card.svelte';
	import TwoFactorCard from '$lib/components/profile/two-factor-card.svelte';
	import AccessKeysPanel from '$lib/components/access-keys/access-keys-panel.svelte';
	import Hint from '$lib/components/hint.svelte';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import BookOpenIcon from '@lucide/svelte/icons/book-open';
	import PlusIcon from '@lucide/svelte/icons/plus';
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

	const tab = $derived.by((): ProfileTab => {
		const asked = page.url.searchParams.get('tab');
		return PROFILE_TABS.find((t) => t === asked) ?? PROFILE_TABS[0];
	});

	let creating = $state(false);
	let keyCount = $state(0);
	const full = $derived(keyCount >= MAX_ACCESS_KEYS);

	function show(next: string) {
		const target = PROFILE_TABS.find((t) => t === next);
		if (target && target !== tab)
			void goto(ROUTES.profileTab(target), { replaceState: true, noScroll: true, keepFocus: true });
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.profile)}</title></svelte:head>

<div class="flex w-full max-w-5xl flex-col gap-6">
	<PageHeader title={routeLabels.profile} />

	<div class="flex flex-wrap items-center justify-between gap-3 border-b">
		<Tabs.Root value={tab} onValueChange={(v) => v && show(v)} class="min-w-0 self-end">
			<ScrollArea orientation="horizontal" class="w-full sm:w-fit">
				<Tabs.List variant="line" class="h-10 w-max justify-start">
					{#each PROFILE_TABS as t (t)}
						<Tabs.Trigger value={t} class="flex-none px-3">{PROFILE_TAB_LABELS[t]}</Tabs.Trigger>
					{/each}
				</Tabs.List>
			</ScrollArea>
		</Tabs.Root>
		{#if tab === 'access-keys'}
			<div class="flex items-center gap-2">
				<Button variant="outline" size="sm" href={ROUTES.apiReference}>
					<BookOpenIcon class="size-4" />
					{routeLabels['api-reference']}
				</Button>
				<Hint text={full ? LIMIT_DETAIL : null}>
					{#snippet child(props)}
						<span {...props}>
							<Button size="sm" disabled={full} onclick={() => (creating = true)}>
								<PlusIcon class="size-4" />
								New key
							</Button>
						</span>
					{/snippet}
				</Hint>
			</div>
		{/if}
	</div>

	{#if tab === 'access-keys'}
		<AccessKeysPanel bind:creating bind:count={keyCount} />
	{:else if tab === 'two-factor'}
		<TwoFactorCard />
	{:else}
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

		<Card.Root>
			<Card.Header>
				<Card.Title>Sidebar</Card.Title>
				<Card.Description>Applies to this account in this browser</Card.Description>
				{#if sidebarLayout.customized}
					<Card.Action>
						<Button variant="ghost" size="sm" onclick={() => sidebarLayout.reset()}>Show all</Button
						>
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
	{/if}
</div>
