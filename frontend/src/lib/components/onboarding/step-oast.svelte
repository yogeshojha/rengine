<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import SatelliteDishIcon from '@lucide/svelte/icons/satellite-dish';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { apiKeysApi } from '$lib/api/api-keys';
	import { oastApi } from '$lib/api/oast';
	import {
		OAST_MODES,
		OAST_MODE_HELP,
		OAST_MODE_LABELS,
		OastMode,
		PUBLIC_ACK
	} from '$lib/config/oast';
	import { APIProvider } from '$lib/types/api-key';
	import type { OastRead, OastTest } from '$lib/types/oast';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	let settings = $state<OastRead | null>(null);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let mode = $state<OastMode>(OastMode.OFF);
	let server = $state('');
	let token = $state('');
	let reveal = $state(false);
	let acknowledged = $state(false);
	let busy = $state(false);
	let testing = $state(false);
	let result = $state<OastTest | null>(null);
	let serverError = $state<string | null>(null);

	const blocked = $derived(
		mode === OastMode.SELF_HOSTED && !server.trim()
			? 'Server domain not set.'
			: mode === OastMode.PUBLIC && !acknowledged
				? 'Public server not accepted.'
				: null
	);

	onMount(async () => {
		try {
			const row = await oastApi.get();
			settings = row;
			mode = row.mode as OastMode;
			server = row.server ?? '';
			acknowledged = row.public_acknowledged;
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Out-of-band settings not loaded';
		} finally {
			loading = false;
		}
	});

	$effect(() => {
		setFooter({
			onNext: handleNext,
			nextLabel: 'Continue',
			nextLoading: busy,
			nextDisabled: !!blocked || !!loadError,
			canSkip: true
		});
	});

	async function save(): Promise<boolean> {
		serverError = null;
		try {
			settings = await oastApi.update({
				mode,
				...(mode === OastMode.SELF_HOSTED ? { server: server.trim() } : {}),
				...(mode === OastMode.PUBLIC ? { public_acknowledged: acknowledged } : {})
			});
			if (mode === OastMode.SELF_HOSTED && token.trim()) {
				await apiKeysApi.upsert(APIProvider.INTERACTSH, token.trim());
				token = '';
				settings = await oastApi.get();
			}
			return true;
		} catch (e) {
			const message = e instanceof Error ? e.message : 'Out-of-band settings not saved';
			if (mode === OastMode.SELF_HOSTED) serverError = message;
			else toast.error(message);
			return false;
		}
	}

	async function test() {
		testing = true;
		result = null;
		try {
			if (await save()) result = await oastApi.test();
		} catch (e) {
			result = {
				ok: false,
				detail: e instanceof Error ? e.message : 'Request failed.',
				address: null,
				status_code: null
			};
		} finally {
			testing = false;
		}
	}

	async function handleNext() {
		busy = true;
		try {
			if (await save()) next();
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	{#if loading}
		<Skeleton class="h-40 w-full rounded-lg" />
	{:else if loadError}
		<EmptyState
			compact
			icon={SatelliteDishIcon}
			title="Out-of-band settings not loaded"
			description={loadError}
		/>
	{:else if settings}
		<div class="space-y-2">
			<ToggleGroup.Root
				type="single"
				value={mode}
				onValueChange={(v) => {
					if (v) {
						mode = v as OastMode;
						result = null;
					}
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
			{#if settings.checks}
				<p class="text-xs text-muted-foreground tabular-nums">
					{settings.checks.toLocaleString()} checks in the library need a callback.
				</p>
			{/if}
		</div>

		{#if mode === OastMode.SELF_HOSTED}
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="space-y-1.5">
					<Label for="oast-server" class="text-xs">Server domain</Label>
					<Input
						id="oast-server"
						bind:value={server}
						placeholder="oast.example.com"
						autocomplete="off"
						spellcheck="false"
						class="h-9 text-sm"
						aria-invalid={!!serverError}
						oninput={() => (serverError = null)}
					/>
					{#if serverError}
						<p class="text-xs text-destructive">{serverError}</p>
					{/if}
				</div>
				<div class="space-y-1.5">
					<Label for="oast-token" class="text-xs">Token</Label>
					<div class="relative">
						<Input
							id="oast-token"
							type={reveal ? 'text' : 'password'}
							bind:value={token}
							placeholder={settings.token_set ? 'Saved' : ''}
							autocomplete="off"
							class="h-9 pr-9 text-sm"
						/>
						<button
							type="button"
							class="absolute top-1/2 right-2.5 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
							onclick={() => (reveal = !reveal)}
							aria-label={reveal ? 'Hide token' : 'Show token'}
						>
							{#if reveal}<EyeOffIcon class="size-4" />{:else}<EyeIcon class="size-4" />{/if}
						</button>
					</div>
					<p class="text-xs text-muted-foreground">
						A server without authentication needs no token.
					</p>
				</div>
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
			</div>
		{/if}

		{#if mode !== OastMode.OFF}
			<div class="flex flex-wrap items-center gap-3">
				<LoadingButton
					variant="outline"
					size="sm"
					class="h-8 text-xs"
					loading={testing}
					loadingLabel="Testing"
					disabled={!!blocked || busy}
					onclick={test}
				>
					Test server
				</LoadingButton>
				{#if blocked}
					<span class="text-xs text-muted-foreground">{blocked}</span>
				{:else if result}
					<span class="flex items-start gap-1.5 text-xs">
						<span class="flex h-4 items-center">
							{#if result.ok}
								<CheckIcon class="size-3.5 shrink-0 text-success" />
							{:else}
								<CircleXIcon class="size-3.5 shrink-0 text-destructive" />
							{/if}
						</span>
						<span>{result.detail}</span>
					</span>
				{/if}
			</div>
		{/if}
	{/if}
</div>
