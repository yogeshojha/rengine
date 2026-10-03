<script lang="ts">
	import { onMount } from 'svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import TimezonePicker from '$lib/components/settings/timezone-picker.svelte';
	import { toast } from 'svelte-sonner';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import LockIcon from '@lucide/svelte/icons/lock';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import { instanceSettingsApi } from '$lib/api/instanceSettings';
	import { authApi } from '$lib/api/auth';
	import { MIN_PASSWORD_LENGTH, PRODUCT_NAME } from '$lib/constants';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import type { StepProps } from '$lib/types/onboarding';

	let { data, next, setFooter }: StepProps = $props();

	let instanceName = $state(data.instanceName || PRODUCT_NAME);
	let timezone = $state('');

	onMount(() => {
		instanceSettingsApi
			.get()
			.then((s) => (timezone = s.timezone))
			.catch(() => {});
	});

	let pwOpen = $state(false);
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let showCurrent = $state(false);
	let showNew = $state(false);

	let busy = $state(false);

	let pwMismatch = $derived(newPassword.length > 0 && newPassword !== confirmPassword);
	let pwTooShort = $derived(newPassword.length > 0 && newPassword.length < MIN_PASSWORD_LENGTH);
	let currentPwMissing = $derived(newPassword.length > 0 && !currentPassword);
	let pwInvalid = $derived(pwMismatch || pwTooShort || currentPwMissing);

	$effect(() => {
		setFooter({
			onNext: handleNext,
			nextLoading: busy,
			nextDisabled: !instanceName.trim() || pwInvalid
		});
	});

	async function handleNext() {
		if (!instanceName.trim()) {
			toast.error('Instance name is required');
			return;
		}
		if (newPassword && newPassword.length < MIN_PASSWORD_LENGTH) {
			toast.error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
			return;
		}
		if (newPassword && newPassword !== confirmPassword) {
			toast.error('New passwords do not match');
			return;
		}
		if (newPassword && !currentPassword) {
			toast.error('Enter the current password to change it');
			return;
		}

		busy = true;
		try {
			await instanceSettingsApi.update({
				instance_name: instanceName.trim(),
				...(timezone ? { timezone } : {})
			});
			capabilitiesStore.setInstanceName(instanceName.trim());
			if (newPassword) {
				await authApi.changePassword({
					current_password: currentPassword,
					new_password: newPassword
				});
				toast.success('Admin password updated');
			}
			data.instanceName = instanceName.trim();
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Settings not saved');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<div class="space-y-4">
		<FormField label="Instance name" description="Shown in the browser tab title.">
			{#snippet children({ id })}
				<Input
					{id}
					bind:value={instanceName}
					placeholder={PRODUCT_NAME}
					disabled={busy}
					maxlength={120}
				/>
			{/snippet}
		</FormField>

		<FormField label="Time zone" description="Used for scan schedules and timestamps.">
			{#snippet children({ id })}
				<div>
					<TimezonePicker
						{id}
						value={timezone}
						disabled={busy || !timezone}
						onChange={(zone) => (timezone = zone)}
					/>
				</div>
			{/snippet}
		</FormField>
	</div>

	<Separator />

	<Collapsible.Root bind:open={pwOpen}>
		<Collapsible.Trigger
			class="flex w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/50 data-[state=open]:bg-muted/40"
		>
			<span class="flex items-center gap-2">
				<LockIcon class="size-4 text-muted-foreground" />
				<span class="font-medium">Change admin password</span>
			</span>
			<ChevronDownIcon
				class="size-4 text-muted-foreground transition-transform {pwOpen ? 'rotate-180' : ''}"
			/>
		</Collapsible.Trigger>
		<Collapsible.Content class="space-y-4 pt-4">
			<FormField
				label="Current password"
				error={currentPwMissing ? 'Enter the current password to change it.' : undefined}
			>
				{#snippet children({ id })}
					<div class="relative">
						<Input
							{id}
							type={showCurrent ? 'text' : 'password'}
							bind:value={currentPassword}
							autocomplete="current-password"
							disabled={busy}
							aria-invalid={currentPwMissing}
							class="pr-10"
						/>
						<button
							type="button"
							class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
							onclick={() => (showCurrent = !showCurrent)}
							aria-label={showCurrent ? 'Hide password' : 'Show password'}
						>
							{#if showCurrent}<EyeOffIcon class="size-4" />{:else}<EyeIcon class="size-4" />{/if}
						</button>
					</div>
				{/snippet}
			</FormField>

			<div class="grid gap-4 sm:grid-cols-2">
				<FormField
					label="New password"
					description="At least {MIN_PASSWORD_LENGTH} characters."
					error={pwTooShort ? `Use at least ${MIN_PASSWORD_LENGTH} characters.` : undefined}
				>
					{#snippet children({ id })}
						<div class="relative">
							<Input
								{id}
								type={showNew ? 'text' : 'password'}
								bind:value={newPassword}
								autocomplete="new-password"
								disabled={busy}
								aria-invalid={pwTooShort}
								class="pr-10"
							/>
							<button
								type="button"
								class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
								onclick={() => (showNew = !showNew)}
								aria-label={showNew ? 'Hide password' : 'Show password'}
							>
								{#if showNew}<EyeOffIcon class="size-4" />{:else}<EyeIcon class="size-4" />{/if}
							</button>
						</div>
					{/snippet}
				</FormField>
				<FormField
					label="Confirm new password"
					error={pwMismatch ? 'Passwords do not match.' : undefined}
				>
					{#snippet children({ id })}
						<Input
							{id}
							type="password"
							bind:value={confirmPassword}
							placeholder="Repeat new password"
							autocomplete="new-password"
							disabled={busy}
							aria-invalid={pwMismatch}
						/>
					{/snippet}
				</FormField>
			</div>
		</Collapsible.Content>
	</Collapsible.Root>
</div>
