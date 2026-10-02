<script lang="ts">
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { oastApi } from '$lib/api/oast';
	import { auth } from '$lib/stores/auth.svelte';
	import { ROUTES } from '$lib/config/routes';
	import {
		CALLBACK_SERVER,
		DEFAULT_WAIT_SECONDS,
		OAST_MODES,
		OAST_MODE_HELP,
		OAST_MODE_LABELS,
		OastMode,
		PUBLIC_ACK,
		WAIT_STEPS
	} from '$lib/config/oast';
	import { relativeTime } from '$lib/utilities/dates';
	import type { OastRead, OastTest } from '$lib/types/oast';

	interface Props {
		open: boolean;
		settings: OastRead | null;
		onSaved: (row: OastRead) => void;
	}

	let { open = $bindable(), settings, onSaved }: Props = $props();

	let mode = $state<OastMode>(OastMode.OFF);
	let server = $state('');
	let wait = $state(0);
	let acknowledged = $state(false);
	let serverError = $state<string | null>(null);
	let saving = $state(false);
	let testing = $state(false);
	let result = $state<OastTest | null>(null);
	let resetOpen = $state(false);
	let resetting = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const dirty = $derived(
		!!settings &&
			(mode !== settings.mode ||
				server.trim() !== (settings.server ?? '') ||
				wait !== settings.wait_seconds ||
				acknowledged !== settings.public_acknowledged)
	);
	const blocked = $derived(
		mode === OastMode.SELF_HOSTED && !server.trim()
			? 'Server domain not set'
			: mode === OastMode.PUBLIC && !acknowledged
				? 'Public server not accepted'
				: null
	);
	const canTest = $derived(
		!!settings && settings.mode !== OastMode.OFF && !settings.reason && !dirty
	);
	const canReset = $derived(
		!!settings &&
			(settings.mode !== OastMode.OFF ||
				!!settings.server ||
				settings.token_set ||
				settings.public_acknowledged ||
				settings.wait_seconds !== DEFAULT_WAIT_SECONDS)
	);

	$effect(() => {
		if (open && settings) {
			mode = settings.mode as OastMode;
			server = settings.server ?? '';
			wait = settings.wait_seconds;
			acknowledged = settings.public_acknowledged;
			serverError = null;
			result = null;
		}
	});

	function waitLabel(seconds: number): string {
		if (seconds === 0) return 'No wait';
		if (seconds < 60) return `${seconds} seconds`;
		const minutes = seconds / 60;
		return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
	}

	async function save() {
		saving = true;
		try {
			const row = await oastApi.update({
				mode,
				server: server.trim(),
				wait_seconds: wait,
				public_acknowledged: acknowledged
			});
			onSaved(row);
			result = null;
			toast.success(`${CALLBACK_SERVER} saved`);
		} catch (e) {
			const message = e instanceof Error ? e.message : `${CALLBACK_SERVER} not saved`;
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
				detail: e instanceof Error ? e.message : 'Request failed.',
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
			const row = await oastApi.reset();
			onSaved(row);
			resetOpen = false;
			toast.success(`${CALLBACK_SERVER} reset`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : `${CALLBACK_SERVER} not reset`);
		} finally {
			resetting = false;
		}
	}
</script>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-md">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>{CALLBACK_SERVER}</Sheet.Title>
			{#if settings}
				<Sheet.Description class="tabular-nums">
					{settings.checks.toLocaleString()} checks need a callback
				</Sheet.Description>
			{/if}
		</Sheet.Header>

		{#if settings}
			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col divide-y px-5">
					<section class="flex flex-col gap-2.5 py-5">
						<SectionHead title="Mode" />
						<ToggleGroup.Root
							type="single"
							variant="outline"
							value={mode}
							onValueChange={(v) => v && (mode = v as OastMode)}
							disabled={!isAdmin || saving}
							class="w-fit"
							aria-label="Mode"
						>
							{#each OAST_MODES as option (option)}
								<ToggleGroup.Item value={option} class="h-9 px-3 text-sm font-normal">
									{OAST_MODE_LABELS[option]}
								</ToggleGroup.Item>
							{/each}
						</ToggleGroup.Root>
						{#if mode !== OastMode.PUBLIC}
							<p class="text-xs text-muted-foreground">{OAST_MODE_HELP[mode]}</p>
						{/if}
						{#if settings.reason && settings.mode !== OastMode.OFF && !dirty}
							<p class="text-xs text-warning">{settings.reason}</p>
						{/if}
					</section>

					{#if mode === OastMode.SELF_HOSTED}
						<section class="flex flex-col gap-2.5 py-5">
							<SectionHead title="Server" />
							<Input
								placeholder="oast.example.com"
								bind:value={server}
								oninput={() => (serverError = null)}
								autocomplete="off"
								spellcheck={false}
								disabled={!isAdmin || saving}
								aria-label="Server domain"
								aria-invalid={serverError ? true : undefined}
								class="font-mono text-xs"
							/>
							{#if serverError}
								<p class="text-xs text-destructive">{serverError}</p>
							{/if}
							<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
								<span class="text-muted-foreground">Token</span>
								<span>{settings.token_set ? 'Set' : 'Not set'}</span>
								<a
									href={ROUTES.settings('api-keys')}
									class="text-primary transition-colors hover:text-foreground"
								>
									API keys
								</a>
							</div>
						</section>
					{/if}

					{#if mode === OastMode.PUBLIC}
						<section class="flex flex-col gap-2.5 py-5">
							<SectionHead title="Public server" />
							<div class="flex items-start gap-2 text-xs">
								<TriangleAlertIcon class="mt-px size-3.5 shrink-0 text-warning" />
								<span>{PUBLIC_ACK}</span>
							</div>
							<label class="flex w-fit cursor-pointer items-center gap-2 text-sm" for="oast-ack">
								<Checkbox
									id="oast-ack"
									checked={acknowledged}
									disabled={!isAdmin || saving}
									onCheckedChange={(v) => (acknowledged = v === true)}
								/>
								Accepted for every scan
							</label>
							<p class="font-mono text-2xs text-muted-foreground">
								{settings.public_servers.join(' · ')}
							</p>
						</section>
					{/if}

					{#if mode !== OastMode.OFF}
						<section class="flex flex-col gap-2.5 py-5">
							<SectionHead title="Wait after each out-of-band batch" />
							<Select.Root
								type="single"
								value={String(wait)}
								onValueChange={(v) => v !== undefined && (wait = Number(v))}
								disabled={!isAdmin || saving}
							>
								<Select.Trigger class="h-9 w-44" aria-label="Wait">
									{waitLabel(wait)}
								</Select.Trigger>
								<Select.Content>
									{#each WAIT_STEPS as step (step)}
										<Select.Item value={String(step)} label={waitLabel(step)}>
											{waitLabel(step)}
										</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						</section>
					{/if}

					{#if result && !dirty}
						<section class="flex items-start gap-2 py-4 text-sm">
							{#if result.ok}
								<CheckIcon class="mt-0.5 size-4 shrink-0 text-success" />
							{:else}
								<CircleXIcon class="mt-0.5 size-4 shrink-0 text-destructive" />
							{/if}
							<span class="wrap-anywhere">{result.detail}</span>
						</section>
					{/if}

					{#if settings.interactions > 0}
						<section class="py-4 text-xs text-muted-foreground tabular-nums">
							{settings.interactions.toLocaleString()}
							{settings.interactions === 1 ? 'finding' : 'findings'} with a callback
							{#if settings.last_interaction_at}
								· most recent {relativeTime(settings.last_interaction_at)}
							{/if}
						</section>
					{/if}
				</div>
			</ScrollArea>

			<div class="flex flex-wrap items-center gap-2 border-t px-5 py-3">
				<LoadingButton
					loading={saving}
					loadingLabel="Saving"
					disabled={!isAdmin || !dirty || !!blocked}
					onclick={save}
				>
					Save
				</LoadingButton>
				<LoadingButton
					variant="outline"
					loading={testing}
					loadingLabel="Testing"
					disabled={!isAdmin || !canTest}
					onclick={test}
				>
					Test server
				</LoadingButton>
				<span class="flex-1"></span>
				<Button
					variant="ghost"
					class="text-muted-foreground"
					disabled={!isAdmin || !canReset}
					onclick={() => (resetOpen = true)}
				>
					Reset
				</Button>
			</div>
			{#if blocked && dirty}
				<p class="border-t px-5 py-2.5 text-xs text-muted-foreground">{blocked}</p>
			{:else if !isAdmin}
				<p class="border-t px-5 py-2.5 text-xs text-muted-foreground">
					Editable by administrators.
				</p>
			{/if}
		{/if}
	</Sheet.Content>
</Sheet.Root>

<ConfirmDialog
	open={resetOpen}
	title="Reset {CALLBACK_SERVER.toLowerCase()}"
	description="The server, the token and the public-server acceptance are removed."
	confirmLabel="Reset"
	destructive
	loading={resetting}
	onOpenChange={(v) => (resetOpen = v)}
	onConfirm={reset}
/>
