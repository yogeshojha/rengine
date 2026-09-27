<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import MoreVerticalIcon from '@lucide/svelte/icons/more-vertical';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import UsersIcon from '@lucide/svelte/icons/users';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { usersApi, type UserAccount } from '$lib/api/users';
	import { auth } from '$lib/stores/auth.svelte';
	import { settingsActions } from '$lib/stores/settings-actions.svelte';
	import { ROLE_LABELS, roleLabel } from '$lib/config/users';
	import { formatDate } from '$lib/utilities';
	import { BODY_ROW, HEAD_ROW, USER_COL } from './columns';

	const ADMIN = 'admin';
	const MEMBER = 'member';

	let users = $state<UserAccount[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);

	let dialogOpen = $state(false);
	let username = $state('');
	let email = $state('');
	let password = $state('');
	let showPassword = $state(false);
	let role = $state(MEMBER);
	let saving = $state(false);

	let removing = $state<UserAccount | null>(null);
	let deleting = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const selfId = $derived(auth.user?.id ?? null);
	const canSave = $derived(!saving && !!username.trim() && !!email.trim() && password.length > 0);

	async function load() {
		loading = true;
		loadError = null;
		try {
			users = await usersApi.list();
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Users not loaded';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		if (isAdmin) void load();
		else loading = false;
	});

	function openAdd() {
		username = '';
		email = '';
		password = '';
		showPassword = false;
		role = MEMBER;
		dialogOpen = true;
	}

	async function create() {
		if (!canSave) return;
		saving = true;
		try {
			const created = await usersApi.create({
				username: username.trim(),
				email: email.trim(),
				password,
				is_superuser: role === ADMIN
			});
			users = [...users, created];
			toast.success(`User ${created.username} added`);
			dialogOpen = false;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'User not added');
		} finally {
			saving = false;
		}
	}

	async function update(user: UserAccount, patch: { is_active?: boolean; is_superuser?: boolean }) {
		try {
			const updated = await usersApi.update(user.id, patch);
			users = users.map((u) => (u.id === updated.id ? updated : u));
			if (patch.is_active !== undefined) {
				toast.success(`User ${user.username} ${patch.is_active ? 'enabled' : 'disabled'}`);
			} else {
				toast.success('Role saved');
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'User not updated');
		}
	}

	async function remove() {
		const user = removing;
		if (!user) return;
		deleting = true;
		try {
			await usersApi.remove(user.id);
			users = users.filter((u) => u.id !== user.id);
			toast.success(`User ${user.username} removed`);
			removing = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'User not removed');
			removing = null;
		} finally {
			deleting = false;
		}
	}

	$effect(() => {
		if (!isAdmin) return;
		settingsActions.set(addAction);
		return () => settingsActions.clear(addAction);
	});
</script>

{#snippet addAction()}
	<Button size="sm" onclick={openAdd}>
		<PlusIcon class="size-4" />
		Add user
	</Button>
{/snippet}

{#if !isAdmin}
	<EmptyState compact icon={UsersIcon} title="Users are managed by administrators" />
{:else if loading}
	<Card.Root class="gap-3 p-4">
		<Skeleton class="h-8 w-full" />
		<Skeleton class="h-10 w-full" />
		<Skeleton class="h-10 w-full" />
	</Card.Root>
{:else if loadError}
	<EmptyState compact icon={TriangleAlertIcon} title="Users not loaded" description={loadError}>
		<Button variant="outline" size="sm" onclick={load}>
			<RotateCwIcon class="size-3.5" />
			Retry
		</Button>
	</EmptyState>
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="@container/users w-full" role="table" aria-label="Users">
			<div class={HEAD_ROW} role="row">
				<div class={USER_COL.user}>User</div>
				<div class={USER_COL.role}>Role</div>
				<div class={USER_COL.twoFactor}>Two-factor</div>
				<div class={USER_COL.created}>Added</div>
				<div class={USER_COL.actions}></div>
			</div>
			{#each users as user (user.id)}
				{@const isSelf = user.id === selfId}
				<div class="{BODY_ROW} {user.is_active ? '' : 'text-muted-foreground'}" role="row">
					<div class="{USER_COL.user} flex flex-col">
						<span class="flex items-center gap-2 text-sm leading-5 font-medium">
							<span class="wrap-anywhere">{user.username}</span>
							{#if isSelf}
								<Badge variant="secondary" class="h-5 px-1.5 text-2xs">Signed in</Badge>
							{/if}
							{#if !user.is_active}
								<Badge variant="outline" class="h-5 px-1.5 text-2xs">Disabled</Badge>
							{/if}
						</span>
						<span class="text-2xs text-muted-foreground wrap-anywhere">{user.email}</span>
					</div>
					<div class="{USER_COL.role} text-sm">{roleLabel(user.is_superuser)}</div>
					<div class="{USER_COL.twoFactor} text-sm">
						{#if user.totp_enabled}
							On
						{:else}
							<span class="text-muted-foreground">Off</span>
						{/if}
					</div>
					<div class="{USER_COL.created} text-xs text-muted-foreground tabular-nums">
						{formatDate(user.created_at)}
					</div>
					<div class={USER_COL.actions}>
						{#if !isSelf}
							<DropdownMenu.Root>
								<DropdownMenu.Trigger>
									{#snippet child({ props })}
										<Button {...props} variant="ghost" size="icon" class="size-7">
											<MoreVerticalIcon class="size-4" />
											<span class="sr-only">{user.username} actions</span>
										</Button>
									{/snippet}
								</DropdownMenu.Trigger>
								<DropdownMenu.Content align="end">
									<DropdownMenu.Item
										onSelect={() => update(user, { is_superuser: !user.is_superuser })}
									>
										{user.is_superuser
											? `Make ${ROLE_LABELS.member.toLowerCase()}`
											: 'Make administrator'}
									</DropdownMenu.Item>
									<DropdownMenu.Item onSelect={() => update(user, { is_active: !user.is_active })}>
										{user.is_active ? 'Disable' : 'Enable'}
									</DropdownMenu.Item>
									<DropdownMenu.Separator />
									<DropdownMenu.Item variant="destructive" onSelect={() => (removing = user)}>
										Remove
									</DropdownMenu.Item>
								</DropdownMenu.Content>
							</DropdownMenu.Root>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</Card.Root>
{/if}

<Dialog.Root bind:open={dialogOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Add user</Dialog.Title>
		</Dialog.Header>
		<form
			class="flex flex-col gap-4"
			onsubmit={(e) => {
				e.preventDefault();
				void create();
			}}
		>
			<FormField label="Username">
				{#snippet children({ id })}
					<Input {id} bind:value={username} autocomplete="off" maxlength={50} disabled={saving} />
				{/snippet}
			</FormField>
			<FormField label="Email">
				{#snippet children({ id })}
					<Input {id} type="email" bind:value={email} autocomplete="off" disabled={saving} />
				{/snippet}
			</FormField>
			<FormField label="Password">
				{#snippet children({ id })}
					<div class="relative">
						<Input
							{id}
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							autocomplete="new-password"
							class="pr-10"
							disabled={saving}
						/>
						<Button
							type="button"
							variant="ghost"
							size="icon"
							class="absolute top-1/2 right-1.5 size-7 -translate-y-1/2 text-muted-foreground"
							aria-label={showPassword ? 'Hide password' : 'Show password'}
							aria-pressed={showPassword}
							onclick={() => (showPassword = !showPassword)}
						>
							{#if showPassword}<EyeOffIcon class="size-4" />{:else}<EyeIcon class="size-4" />{/if}
						</Button>
					</div>
				{/snippet}
			</FormField>
			<FormField label="Role">
				{#snippet children({ id })}
					<Select.Root type="single" bind:value={role} disabled={saving}>
						<Select.Trigger {id} class="w-full">
							{role === ADMIN ? ROLE_LABELS.admin : ROLE_LABELS.member}
						</Select.Trigger>
						<Select.Content>
							<Select.Item value={MEMBER} label={ROLE_LABELS.member}
								>{ROLE_LABELS.member}</Select.Item
							>
							<Select.Item value={ADMIN} label={ROLE_LABELS.admin}>{ROLE_LABELS.admin}</Select.Item>
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>
			<Dialog.Footer>
				<Button
					type="button"
					variant="outline"
					disabled={saving}
					onclick={() => (dialogOpen = false)}
				>
					Cancel
				</Button>
				<LoadingButton type="submit" loading={saving} loadingLabel="Adding" disabled={!canSave}>
					Add user
				</LoadingButton>
			</Dialog.Footer>
		</form>
	</Dialog.Content>
</Dialog.Root>

<ConfirmDialog
	open={removing !== null}
	title="Remove user"
	description={removing ? `User ${removing.username} is removed.` : ''}
	confirmLabel="Remove"
	destructive
	loading={deleting}
	onOpenChange={(open) => {
		if (!open) removing = null;
	}}
	onConfirm={remove}
/>
