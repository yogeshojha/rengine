<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import { toast } from 'svelte-sonner';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import LockIcon from '@lucide/svelte/icons/lock';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import { instanceSettingsApi } from '$lib/api/instanceSettings';
	import { authApi } from '$lib/api/auth';
	import type { StepProps } from '$lib/types/onboarding';

	let { data, next, setFooter }: StepProps = $props();

	const TIMEZONES = [
		'UTC',
		'America/New_York',
		'America/Chicago',
		'America/Denver',
		'America/Los_Angeles',
		'America/Sao_Paulo',
		'Europe/London',
		'Europe/Paris',
		'Europe/Berlin',
		'Europe/Moscow',
		'Asia/Dubai',
		'Asia/Kolkata',
		'Asia/Singapore',
		'Asia/Shanghai',
		'Asia/Tokyo',
		'Australia/Sydney'
	];

	let instanceName = $state(data.instanceName || 'reNgine');
	let timezone = $state('UTC');

	let pwOpen = $state(false);
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let showCurrent = $state(false);
	let showNew = $state(false);

	let busy = $state(false);

	let zoneOptions = $derived.by(() => {
		const local = Intl.DateTimeFormat().resolvedOptions().timeZone;
		if (local && !TIMEZONES.includes(local)) return [local, ...TIMEZONES];
		return TIMEZONES;
	});

	const MIN_PW_LENGTH = 10;
	let pwMismatch = $derived(newPassword.length > 0 && newPassword !== confirmPassword);
	let pwTooShort = $derived(newPassword.length > 0 && newPassword.length < MIN_PW_LENGTH);
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
		if (newPassword && newPassword.length < MIN_PW_LENGTH) {
			toast.error(`Password must be at least ${MIN_PW_LENGTH} characters`);
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
			await instanceSettingsApi.update({ instance_name: instanceName.trim(), timezone });
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
			toast.error(e instanceof Error ? e.message : 'Settings could not be saved');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<div class="space-y-5">
		<div class="space-y-1.5">
			<Label for="instance-name" class="text-sm font-medium">Instance name</Label>
			<Input
				id="instance-name"
				bind:value={instanceName}
				placeholder="reNgine"
				disabled={busy}
				maxlength={120}
			/>
			<p class="text-xs text-muted-foreground">Shown in the header and on reports.</p>
		</div>

		<div class="space-y-1.5">
			<Label class="text-sm font-medium">Timezone</Label>
			<Select.Root type="single" bind:value={timezone}>
				<Select.Trigger class="w-full sm:w-72">{timezone}</Select.Trigger>
				<Select.Content>
					{#each zoneOptions as tz (tz)}
						<Select.Item value={tz} label={tz}>{tz}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			<p class="text-xs text-muted-foreground">Used for scan schedules and timestamps.</p>
		</div>
	</div>

	<Separator />

	<Collapsible.Root bind:open={pwOpen}>
		<Collapsible.Trigger
			class="flex w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/50 data-[state=open]:bg-muted/40"
		>
			<span class="flex items-center gap-2">
				<LockIcon class="size-4 text-muted-foreground" />
				<span class="font-medium">Change admin password</span>
				<span
					class="rounded-full border border-input px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground"
					>Recommended</span
				>
			</span>
			<ChevronDownIcon
				class="size-4 text-muted-foreground transition-transform {pwOpen ? 'rotate-180' : ''}"
			/>
		</Collapsible.Trigger>
		<Collapsible.Content class="space-y-4 pt-4">
			<p class="text-xs text-muted-foreground">
				reNgine ships with a default administrator password. Change it before this instance is
				reachable.
			</p>
			<div class="space-y-1.5">
				<Label for="current-pw" class="text-xs">Current password</Label>
				<div class="relative">
					<Input
						id="current-pw"
						type={showCurrent ? 'text' : 'password'}
						bind:value={currentPassword}
						placeholder="Current password"
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
				{#if currentPwMissing}
					<p class="text-xs text-destructive">Enter the current password to change it.</p>
				{/if}
			</div>

			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1.5">
					<Label for="new-pw" class="text-xs">New password</Label>
					<div class="relative">
						<Input
							id="new-pw"
							type={showNew ? 'text' : 'password'}
							bind:value={newPassword}
							placeholder="New password"
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
					{#if pwTooShort}
						<p class="text-xs text-destructive">Use at least {MIN_PW_LENGTH} characters.</p>
					{:else}
						<p class="text-xs text-muted-foreground">
							At least {MIN_PW_LENGTH} characters; mix upper/lowercase, numbers, and symbols.
						</p>
					{/if}
				</div>
				<div class="space-y-1.5">
					<Label for="confirm-pw" class="text-xs">Confirm new password</Label>
					<Input
						id="confirm-pw"
						type="password"
						bind:value={confirmPassword}
						placeholder="Repeat new password"
						autocomplete="new-password"
						disabled={busy}
						aria-invalid={pwMismatch}
					/>
					{#if pwMismatch}
						<p class="text-xs text-destructive">Passwords do not match.</p>
					{/if}
				</div>
			</div>
			<p class="text-xs text-muted-foreground">Leave blank to keep the current password.</p>
		</Collapsible.Content>
	</Collapsible.Root>
</div>
