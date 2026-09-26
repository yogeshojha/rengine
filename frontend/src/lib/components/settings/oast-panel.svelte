<script lang="ts">
	import { errorMessage } from '$lib/utilities/errors';
	import { onMount } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import SatelliteDishIcon from '@lucide/svelte/icons/satellite-dish';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { oastApi } from '$lib/api/oast';
	import { ROUTES } from '$lib/config/routes';
	import {
		DEFAULT_WAIT_SECONDS,
		MAX_WAIT_SECONDS,
		OAST_MODES,
		OAST_MODE_HELP,
		OAST_MODE_LABELS,
		OastMode,
		PUBLIC_ACK,
		WAIT_STEPS
	} from '$lib/config/oast';
	import { relativeTime } from '$lib/utilities/dates';
	import type { OastRead, OastTest } from '$lib/types/oast';

	let settings = $state<OastRead | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let serverError = $state<string | null>(null);
	let saving = $state(false);
	let testing = $state(false);
	let resetOpen = $state(false);
	let resetting = $state(false);
	let result = $state<OastTest | null>(null);

	let mode = $state<OastMode>(OastMode.OFF);
	let server = $state('');
	let wait = $state(DEFAULT_WAIT_SECONDS);
	let acknowledged = $state(false);

	let ModeIcon = $derived(
		!settings || settings.mode === OastMode.OFF ? CircleXIcon : SatelliteDishIcon
	);
	let tone = $derived<BadgeVariant>(
		!settings || settings.reason
			? 'outline'
			: settings.mode === OastMode.PUBLIC
				? 'warning'
				: 'success'
	);
	let dirty = $derived(
		!!settings &&
			(mode !== settings.mode ||
				server.trim() !== (settings.server ?? '') ||
				wait !== settings.wait_seconds ||
				acknowledged !== settings.public_acknowledged)
	);
	let blocked = $derived(
		mode === OastMode.SELF_HOSTED && !server.trim()
			? 'Set the server first.'
			: mode === OastMode.PUBLIC && !acknowledged
				? 'Accept the public server first.'
				: null
	);
	let canTest = $derived(
		!!settings && settings.mode !== OastMode.OFF && !settings.reason && !dirty
	);
	let canReset = $derived(
		!!settings &&
			(settings.mode !== OastMode.OFF ||
				!!settings.server ||
				settings.token_set ||
				settings.public_acknowledged ||
				settings.wait_seconds !== DEFAULT_WAIT_SECONDS)
	);

	function apply(row: OastRead) {
		settings = row;
		mode = row.mode as OastMode;
		server = row.server ?? '';
		wait = row.wait_seconds;
		acknowledged = row.public_acknowledged;
		serverError = null;
	}

	async function load() {
		loading = true;
		try {
			apply(await oastApi.get());
			error = null;
		} catch (e) {
			error = errorMessage(e, 'Request failed.');
		} finally {
			loading = false;
		}
	}

	onMount(load);

	let showLeaveDialog = $state(false);
	let pendingNav: (() => void) | null = $state(null);
	let allowNavigation = $state(false);

	beforeNavigate((nav) => {
		if (allowNavigation) {
			allowNavigation = false;
			return;
		}
		if (!dirty || saving || pendingNav) return;
		nav.cancel();
		pendingNav = () => {
			allowNavigation = true;
			if (nav.to) goto(nav.to.url);
		};
		showLeaveDialog = true;
	});

	async function save() {
		saving = true;
		try {
			apply(
				await oastApi.update({
					mode,
					server: server.trim(),
					wait_seconds: wait,
					public_acknowledged: acknowledged
				})
			);
			result = null;
			toast.success('Out-of-band settings saved');
		} catch (e) {
			const message = errorMessage(e, 'Settings not saved');
			if (mode === OastMode.SELF_HOSTED) serverError = message;
			else toast.error(message);
		} finally {
			saving = false;
		}
	}

	async function test() {
		testing = true;
		try {
			result = await oastApi.test();
		} catch (e) {
			result = {
				ok: false,
				detail: errorMessage(e, 'Request failed.'),
				address: null,
				status_code: null
			};
		} finally {
			testing = false;
		}
	}

	async function reset() {
		resetting = true;
		try {
			apply(await oastApi.reset());
			result = null;
			resetOpen = false;
			toast.success('Out-of-band settings cleared');
		} catch (e) {
			toast.error(errorMessage(e, 'Settings not cleared'));
		} finally {
			resetting = false;
		}
	}
</script>

<Card.Root>
	<Card.Header>
		<div class="flex items-start gap-3">
			<span class="flex h-5 items-center">
				<ModeIcon class="size-5 shrink-0 text-muted-foreground" />
			</span>
			<div class="flex min-w-0 flex-col gap-1">
				<Card.Title>Out-of-band testing</Card.Title>
				<Card.Description>
					{#if settings?.checks}
						{settings.checks.toLocaleString()} checks confirm a finding through a callback to a server
						outside the target.
					{:else}
						Checks that confirm a finding through a callback to a server outside the target.
					{/if}
				</Card.Description>
			</div>
			{#if settings}
				<Badge variant={tone} class="ml-auto shrink-0">
					{settings.reason ? 'Off' : OAST_MODE_LABELS[settings.mode as OastMode]}
				</Badge>
			{/if}
		</div>
	</Card.Header>

	<Card.Content class="flex flex-col gap-5">
		{#if loading}
			<Skeleton class="h-40 w-full" />
		{:else if error}
			<p class="text-sm text-destructive">{error}</p>
			<Button variant="outline" size="sm" class="w-fit" onclick={() => load()}>Try again</Button>
		{:else if settings}
			<div class="flex flex-col gap-2">
				<Label>Mode</Label>
				<ToggleGroup.Root
					type="single"
					value={mode}
					onValueChange={(v) => {
						if (v) mode = v as OastMode;
					}}
					variant="outline"
					class="w-fit"
					aria-label="Out-of-band mode"
				>
					{#each OAST_MODES as option (option)}
						<ToggleGroup.Item value={option} class="h-9 px-3 text-sm font-normal">
							{OAST_MODE_LABELS[option]}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
				<p class="text-sm text-muted-foreground">{OAST_MODE_HELP[mode]}</p>
				{#if settings.reason && settings.mode !== OastMode.OFF && !dirty}
					<p class="text-sm text-warning">{settings.reason}</p>
				{/if}
			</div>

			{#if mode === OastMode.SELF_HOSTED}
				<FormField label="Server domain" for="oast-server" error={serverError ?? undefined}>
					{#snippet children({ id })}
						<Input
							{id}
							placeholder="oast.example.com"
							bind:value={server}
							oninput={() => (serverError = null)}
							autocomplete="off"
							spellcheck="false"
						/>
					{/snippet}
				</FormField>
				<div class="flex flex-wrap items-center gap-2 text-sm">
					<span class="text-muted-foreground">Token</span>
					{#if settings.token_set}
						<Badge variant="success" class="gap-1"><CheckIcon class="size-3" />Set</Badge>
					{:else}
						<Badge variant="outline">Not set</Badge>
					{/if}
					<a href={ROUTES.settings('api-keys')} class="font-medium text-primary hover:underline">
						{settings.token_set ? 'Replace it under API keys' : 'Add it under API keys'}
					</a>
					<span class="text-muted-foreground">A server without authentication needs no token.</span>
				</div>
			{/if}

			{#if mode === OastMode.PUBLIC}
				<div class="flex flex-col gap-2 rounded-md border border-warning/40 bg-warning/5 p-3">
					<div class="flex items-start gap-2">
						<span class="flex h-5 items-center">
							<TriangleAlertIcon class="size-4 shrink-0 text-warning" />
						</span>
						<p class="text-sm">{PUBLIC_ACK}</p>
					</div>
					<Label class="flex w-fit cursor-pointer items-center gap-2 text-sm font-normal">
						<Checkbox checked={acknowledged} onCheckedChange={(v) => (acknowledged = v === true)} />
						<span>Accepted for every scan on this instance</span>
					</Label>
					<p class="text-xs text-muted-foreground">
						Servers in rotation: {settings.public_servers.join(', ')}
					</p>
				</div>
			{/if}

			{#if mode !== OastMode.OFF}
				<div class="flex flex-col gap-2">
					<Label for="oast-wait">Wait for a callback</Label>
					<div class="flex flex-wrap items-center gap-2">
						<Select.Root
							type="single"
							value={String(wait)}
							onValueChange={(v) => (wait = Number(v))}
						>
							<Select.Trigger id="oast-wait" class="h-9 w-40">
								{wait === 0 ? 'No extra wait' : `${wait}s`}
							</Select.Trigger>
							<Select.Content>
								{#each WAIT_STEPS as step (step)}
									<Select.Item value={String(step)}>
										{step === 0 ? 'No extra wait' : `${step}s`}
									</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
						<span class="text-sm text-muted-foreground">
							Paid once at the end of each out-of-band batch, up to {MAX_WAIT_SECONDS}s.
						</span>
					</div>
				</div>
			{/if}

			<Separator />

			<div class="flex flex-wrap items-center gap-2">
				<LoadingButton
					loading={saving}
					loadingLabel="Saving"
					disabled={!dirty || !!blocked}
					onclick={save}
				>
					Save
				</LoadingButton>
				<LoadingButton
					variant="outline"
					loading={testing}
					loadingLabel="Testing"
					disabled={!canTest}
					onclick={test}
				>
					Test server
				</LoadingButton>
				{#if dirty}
					<span class="text-xs text-muted-foreground">Unsaved changes</span>
				{/if}
				<span class="flex-1"></span>
				<Button
					variant="ghost"
					class="text-muted-foreground"
					disabled={!canReset}
					onclick={() => (resetOpen = true)}
				>
					Reset
				</Button>
			</div>

			{#if blocked}
				<p class="text-sm text-muted-foreground">{blocked}</p>
			{:else if dirty}
				<p class="text-sm text-muted-foreground">Save to test the server.</p>
			{:else if settings.mode === OastMode.OFF}
				<p class="text-sm text-muted-foreground">Choose Self-hosted or Public to test a server.</p>
			{/if}

			{#if result && !dirty}
				<div class="flex items-start gap-2 text-sm">
					<span class="flex h-5 items-center">
						{#if result.ok}
							<CheckIcon class="size-4 shrink-0 text-success" />
						{:else}
							<CircleXIcon class="size-4 shrink-0 text-destructive" />
						{/if}
					</span>
					<span>{result.detail}</span>
				</div>
			{/if}

			{#if settings.interactions > 0}
				<p class="text-sm text-muted-foreground">
					{settings.interactions.toLocaleString()} findings carry a callback.
					{#if settings.last_interaction_at}
						Most recent {relativeTime(settings.last_interaction_at)}.
					{/if}
				</p>
			{/if}
		{/if}
	</Card.Content>
</Card.Root>

<ConfirmDialog
	open={resetOpen}
	title="Reset out-of-band testing"
	description="The server, the token and the public-server acceptance are removed."
	confirmLabel="Reset"
	destructive
	loading={resetting}
	onOpenChange={(open) => (resetOpen = open)}
	onConfirm={reset}
/>

<UnsavedChangesDialog
	open={showLeaveDialog}
	onOpenChange={(o) => {
		showLeaveDialog = o;
		if (!o) pendingNav = null;
	}}
	onConfirm={() => {
		showLeaveDialog = false;
		const resume = pendingNav;
		pendingNav = null;
		resume?.();
	}}
/>
