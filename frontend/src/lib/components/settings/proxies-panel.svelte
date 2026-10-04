<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import RouteIcon from '@lucide/svelte/icons/route';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import XIcon from '@lucide/svelte/icons/x';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { proxiesStore } from '$lib/stores/proxies.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { settingsActions } from '$lib/stores/settings-actions.svelte';
	import { MASK } from '$lib/constants';
	import { relativeTime } from '$lib/utilities/dates';
	import { formatMilliseconds } from '$lib/utilities/format';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import {
		PROXY_SCHEMES,
		PROXY_SCHEME_LABELS,
		type ProxyEndpoint,
		type ProxyRead
	} from '$lib/types/proxy';
	import CheckStatus from './check-status.svelte';
	import { BODY_ROW, HEAD_ROW, PROXY_COL } from './columns';
	import { checkState, type CheckState } from './status';

	type Scheme = (typeof PROXY_SCHEMES)[number];

	interface EndpointRow {
		scheme: string;
		host: string;
		port: string;
		username: string;
		password: string;
		stored: boolean;
	}

	const STATUS_LABEL: Record<CheckState, string> = {
		ok: 'Reachable',
		failed: 'Failed',
		untested: 'Not tested',
		off: 'Disabled'
	};

	let loading = $state(true);
	let loadFailed = $state(false);
	let testing = $state<string | null>(null);

	let dialogOpen = $state(false);
	let editing = $state<ProxyRead | null>(null);
	let name = $state('');
	let description = $state('');
	let asDefault = $state(false);
	let rows = $state<EndpointRow[]>([]);
	let saving = $state(false);
	let initial = $state('');
	let nameError = $state('');
	let endpointError = $state('');

	let removing = $state<ProxyRead | null>(null);
	let deleting = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const proxies = $derived(proxiesStore.proxies);
	const dirty = $derived(snapshot() !== initial);
	const guard = new DiscardGuard(
		() => dirty,
		() => (dialogOpen = false)
	);

	function snapshot(): string {
		return JSON.stringify([name.trim(), description.trim(), asDefault, rows]);
	}

	function blank(): EndpointRow {
		return { scheme: 'http', host: '', port: '8080', username: '', password: '', stored: false };
	}

	async function load() {
		loading = true;
		await proxiesStore.fetch();
		loadFailed = !proxiesStore.hasFetched;
		loading = false;
	}

	onMount(() => {
		if (!isAdmin) loading = false;
		else if (proxiesStore.hasFetched) loading = false;
		else void load();
	});

	function openDialog(proxy: ProxyRead | null) {
		editing = proxy;
		name = proxy?.name ?? '';
		description = proxy?.description ?? '';
		asDefault = proxy ? proxy.is_default : proxies.length === 0;
		rows = proxy?.endpoints.length
			? proxy.endpoints.map((e) => ({
					scheme: e.scheme,
					host: e.host,
					port: String(e.port),
					username: e.username ?? '',
					password: '',
					stored: e.has_password
				}))
			: [blank()];
		nameError = '';
		endpointError = '';
		initial = snapshot();
		dialogOpen = true;
	}

	function endpoints(): ProxyEndpoint[] | null {
		const out: ProxyEndpoint[] = [];
		for (const row of rows) {
			const host = row.host.trim();
			const port = Math.trunc(Number(row.port));
			if (!host || !Number.isFinite(port) || port < 1 || port > 65535) return null;
			out.push({
				scheme: row.scheme,
				host,
				port,
				username: row.username.trim() || null,
				password: row.password ? row.password : row.stored ? MASK : null
			});
		}
		return out.length ? out : null;
	}

	async function save() {
		const parsed = endpoints();
		nameError = name.trim() ? '' : 'Proxy name is required';
		endpointError = parsed ? '' : 'Each endpoint needs a host and a port between 1 and 65535';
		if (!parsed || nameError) return;
		saving = true;
		try {
			const body = {
				name: name.trim(),
				description: description.trim() || null,
				is_default: asDefault,
				endpoints: parsed
			};
			const saved = editing
				? await proxiesStore.update(editing.id, body)
				: await proxiesStore.create({ ...body, is_active: true });
			if (saved) {
				if (asDefault) await proxiesStore.fetch();
				toast.success(editing ? 'Proxy saved' : 'Proxy added');
				dialogOpen = false;
			}
		} finally {
			saving = false;
		}
	}

	async function test(proxy: ProxyRead) {
		testing = proxy.id;
		try {
			const result = await proxiesStore.test(proxy.id);
			if (!result) return;
			if (result.success) {
				toast.success(
					result.message,
					result.latency_ms != null
						? { description: formatMilliseconds(result.latency_ms) }
						: undefined
				);
			} else {
				toast.error(result.message);
			}
		} finally {
			testing = null;
		}
	}

	async function setActive(proxy: ProxyRead, active: boolean) {
		const updated = await proxiesStore.update(proxy.id, { is_active: active });
		if (updated) toast.success(`Proxy ${active ? 'enabled' : 'disabled'}`);
	}

	async function makeDefault(proxy: ProxyRead) {
		const updated = await proxiesStore.setDefault(proxy.id);
		if (updated) toast.success(`${proxy.name} is the default proxy`);
	}

	async function remove() {
		const proxy = removing;
		if (!proxy) return;
		deleting = true;
		try {
			if (await proxiesStore.remove(proxy.id)) {
				toast.success('Proxy removed');
				removing = null;
			}
		} finally {
			deleting = false;
		}
	}

	function removeDescription(proxy: ProxyRead): string {
		const n = proxy.contexts;
		if (!n) return `Proxy ${proxy.name} is removed.`;
		return `Proxy ${proxy.name} is removed and cleared from ${n} scan context${n === 1 ? '' : 's'}.`;
	}

	$effect(() => {
		if (!isAdmin) return;
		settingsActions.set(addAction);
		return () => settingsActions.clear(addAction);
	});
</script>

{#snippet addAction()}
	<Button size="sm" onclick={() => openDialog(null)}>
		<PlusIcon class="size-4" />
		Add proxy
	</Button>
{/snippet}

{#if !isAdmin}
	<EmptyState compact icon={RouteIcon} title="Proxies are managed by administrators" />
{:else if loading}
	<Card.Root class="gap-3 p-4">
		<Skeleton class="h-8 w-full" />
		<Skeleton class="h-10 w-full" />
		<Skeleton class="h-10 w-full" />
	</Card.Root>
{:else if loadFailed}
	<EmptyState compact icon={TriangleAlertIcon} title="Proxies not loaded">
		<Button variant="outline" size="sm" onclick={load}>
			<RotateCwIcon class="size-3.5" />
			Retry
		</Button>
	</EmptyState>
{:else if proxies.length === 0}
	<EmptyState icon={RouteIcon} title="No proxies">
		<Button size="sm" onclick={() => openDialog(null)}>
			<PlusIcon class="size-4" />
			Add proxy
		</Button>
	</EmptyState>
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="@container/proxies w-full" role="table" aria-label="Proxies">
			<div class={HEAD_ROW} role="row">
				<div class={PROXY_COL.proxy} role="columnheader">Proxy</div>
				<div class={PROXY_COL.endpoint} role="columnheader">Endpoint</div>
				<div class={PROXY_COL.contexts} role="columnheader">Contexts</div>
				<div class={PROXY_COL.status} role="columnheader">Status</div>
				<div class={PROXY_COL.actions} role="columnheader">
					<span class="sr-only">Actions</span>
				</div>
			</div>
			{#each proxies as proxy (proxy.id)}
				{@const check = checkState(proxy.is_active, proxy.last_test_ok)}
				<div class="{BODY_ROW} {proxy.is_active ? '' : 'text-muted-foreground'}" role="row">
					<div class="{PROXY_COL.proxy} flex flex-col" role="cell">
						<span class="flex items-center gap-2 text-sm leading-5 font-medium">
							<span class="wrap-anywhere">{proxy.name}</span>
							{#if proxy.is_default}
								<Badge variant="secondary" class="h-5 px-1.5 text-2xs">Default</Badge>
							{/if}
						</span>
						<span class="text-2xs text-muted-foreground">
							{proxy.description ||
								(proxy.endpoint_count > 1
									? `Pool of ${proxy.endpoint_count} endpoints`
									: 'Single endpoint')}
						</span>
					</div>
					<div class="{PROXY_COL.endpoint} flex min-w-0 flex-col" role="cell">
						<code class="truncate font-mono text-xs text-muted-foreground">
							{proxy.endpoints[0]?.url_masked ?? ''}
						</code>
						{#if proxy.endpoint_count > 1}
							<span class="text-2xs text-muted-foreground">
								+{proxy.endpoint_count - 1} more
							</span>
						{/if}
					</div>
					<div class="{PROXY_COL.contexts} text-sm tabular-nums" role="cell">
						{proxy.contexts || '—'}
					</div>
					<div class="{PROXY_COL.status} flex flex-col" role="cell">
						<CheckStatus
							{check}
							label={STATUS_LABEL[check]}
							message={check === 'failed' ? proxy.last_test_message : null}
							busy={testing === proxy.id}
							busyLabel="Testing"
							muted={check !== 'ok' && check !== 'failed'}
						/>
						{#if proxy.last_test_at && testing !== proxy.id}
							<span class="pl-4 text-2xs text-muted-foreground tabular-nums">
								{relativeTime(proxy.last_test_at)}
							</span>
						{/if}
					</div>
					<div class={PROXY_COL.actions} role="cell">
						<DropdownMenu.Root>
							<DropdownMenu.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="ghost"
										size="icon"
										class="size-7"
										aria-label="{proxy.name} actions"
									>
										<EllipsisIcon class="size-4" />
									</Button>
								{/snippet}
							</DropdownMenu.Trigger>
							<DropdownMenu.Content align="end">
								<DropdownMenu.Item
									disabled={testing !== null || !proxy.is_active}
									onSelect={() => test(proxy)}
								>
									Test
								</DropdownMenu.Item>
								<DropdownMenu.Item onSelect={() => openDialog(proxy)}>Edit</DropdownMenu.Item>
								{#if !proxy.is_default}
									<DropdownMenu.Item
										disabled={!proxy.is_active}
										onSelect={() => makeDefault(proxy)}
									>
										Set as default
									</DropdownMenu.Item>
								{/if}
								<DropdownMenu.Item onSelect={() => setActive(proxy, !proxy.is_active)}>
									{proxy.is_active ? 'Disable' : 'Enable'}
								</DropdownMenu.Item>
								<DropdownMenu.Separator />
								<DropdownMenu.Item variant="destructive" onSelect={() => (removing = proxy)}>
									Remove
								</DropdownMenu.Item>
							</DropdownMenu.Content>
						</DropdownMenu.Root>
					</div>
				</div>
			{/each}
		</div>
	</Card.Root>
{/if}

<Dialog.Root
	bind:open={() => dialogOpen, (next) => (next ? (dialogOpen = true) : !saving && guard.close())}
>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{editing ? 'Edit proxy' : 'Add proxy'}</Dialog.Title>
		</Dialog.Header>
		<ScrollArea
			class="min-h-0 flex-1 [&>[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-10rem)]"
		>
			<div class="flex flex-col gap-5 px-6 py-5">
				<div class="grid gap-4 sm:grid-cols-2">
					<FormField label="Name" error={nameError}>
						{#snippet children({ id })}
							<Input
								{id}
								bind:value={name}
								maxlength={120}
								disabled={saving}
								aria-invalid={!!nameError}
								oninput={() => (nameError = '')}
							/>
						{/snippet}
					</FormField>
					<FormField label="Description">
						{#snippet children({ id })}
							<Input
								{id}
								bind:value={description}
								maxlength={500}
								placeholder="Optional"
								disabled={saving}
							/>
						{/snippet}
					</FormField>
				</div>

				<div class="flex flex-col gap-2">
					<div class="flex items-baseline justify-between gap-3">
						<span class="text-sm font-medium">Endpoints</span>
						{#if rows.length > 1}
							<span class="text-xs text-muted-foreground">
								Each scan uses one endpoint from the pool
							</span>
						{/if}
					</div>
					<div class="overflow-hidden rounded-lg border">
						<div
							class="hidden grid-cols-[6.5rem_minmax(0,1fr)_5rem_minmax(0,0.8fr)_minmax(0,0.8fr)_2rem] gap-2 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase sm:grid"
						>
							<span>Scheme</span>
							<span>Host</span>
							<span>Port</span>
							<span>Username</span>
							<span>Password</span>
							<span></span>
						</div>
						{#each rows as row, i (i)}
							<div
								class="grid grid-cols-2 gap-2 border-b border-border/60 px-4 py-2 last:border-b-0 sm:grid-cols-[6.5rem_minmax(0,1fr)_5rem_minmax(0,0.8fr)_minmax(0,0.8fr)_2rem]"
							>
								<Select.Root
									type="single"
									value={row.scheme}
									onValueChange={(v) => v && (row.scheme = v)}
								>
									<Select.Trigger class="h-9 w-full" aria-label="Scheme">
										{PROXY_SCHEME_LABELS[row.scheme as Scheme] ?? row.scheme}
									</Select.Trigger>
									<Select.Content>
										{#each PROXY_SCHEMES as scheme (scheme)}
											<Select.Item value={scheme} label={PROXY_SCHEME_LABELS[scheme]}>
												{PROXY_SCHEME_LABELS[scheme]}
											</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
								<Input
									bind:value={row.host}
									placeholder="gate.provider.com"
									aria-label="Host"
									autocomplete="off"
									class="h-9 font-mono text-xs"
								/>
								<Input
									bind:value={row.port}
									type="number"
									min="1"
									max="65535"
									aria-label="Port"
									class="h-9 font-mono text-xs"
								/>
								<Input
									bind:value={row.username}
									placeholder="Optional"
									aria-label="Username"
									autocomplete="off"
									class="h-9 font-mono text-xs"
								/>
								<Input
									bind:value={row.password}
									type="password"
									placeholder={row.stored ? 'Stored' : 'Optional'}
									aria-label="Password"
									autocomplete="new-password"
									class="h-9 font-mono text-xs"
								/>
								<Button
									variant="ghost"
									size="icon"
									class="text-muted-foreground"
									disabled={rows.length === 1}
									aria-label="Remove endpoint"
									onclick={() => (rows = rows.filter((_, idx) => idx !== i))}
								>
									<XIcon class="size-4" />
								</Button>
							</div>
						{/each}
					</div>
					{#if endpointError && !endpoints()}
						<p class="text-sm text-destructive" role="alert">{endpointError}</p>
					{/if}
					<Button
						variant="ghost"
						size="sm"
						class="w-fit text-muted-foreground"
						onclick={() => (rows = [...rows, blank()])}
					>
						<PlusIcon class="size-3.5" />
						Add endpoint
					</Button>
				</div>

				<label
					class="flex cursor-pointer items-center justify-between gap-4 rounded-lg border px-4 py-3"
					for="proxy-default"
				>
					<span class="flex flex-col gap-0.5">
						<span class="text-sm font-medium">Default proxy</span>
						<span class="text-xs text-muted-foreground">
							Used by scans launched without a scan context. Preselected for new scan contexts.
						</span>
					</span>
					<Switch id="proxy-default" bind:checked={asDefault} disabled={saving} />
				</label>
			</div>
		</ScrollArea>
		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" disabled={saving} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton loading={saving} loadingLabel="Saving" onclick={save}>
				{editing ? 'Save' : 'Add proxy'}
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<ConfirmDialog
	open={removing !== null}
	title="Remove proxy"
	description={removing ? removeDescription(removing) : ''}
	confirmLabel="Remove"
	loadingLabel="Removing"
	destructive
	loading={deleting}
	onOpenChange={(open) => {
		if (!open) removing = null;
	}}
	onConfirm={remove}
/>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
