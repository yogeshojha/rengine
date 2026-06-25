<script lang="ts">
	import { onMount } from 'svelte';
	import { proxiesStore } from '$lib/stores/proxies.svelte';
	import {
		PROXY_SCHEMES,
		PROXY_MODES,
		PROXY_SCHEME_LABELS,
		PROXY_MODE_LABELS,
		type ProxyRead,
		type ProxyEndpoint
	} from '$lib/types/proxy';
	import { MASK } from '$lib/constants';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import { toast } from 'svelte-sonner';
	import RouteIcon from '@lucide/svelte/icons/route';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import StarIcon from '@lucide/svelte/icons/star';
	import XIcon from '@lucide/svelte/icons/x';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import { formatDate } from '$lib/utilities';

	let isLoading = $state(true);
	let testingId = $state<string | null>(null);
	let settingDefaultId = $state<string | null>(null);

	interface EndpointRow {
		scheme: string;
		host: string;
		port: string;
		username: string;
		password: string;
		masked: boolean;
	}

	function blankRow(): EndpointRow {
		return { scheme: 'http', host: '', port: '8080', username: '', password: '', masked: false };
	}

	let dialogOpen = $state(false);
	let editingId = $state<string | null>(null);
	let formName = $state('');
	let formDescription = $state('');
	let formMode = $state('single');
	let formActive = $state(true);
	let formDefault = $state(false);
	let formRows = $state<EndpointRow[]>([blankRow()]);
	let saving = $state(false);

	let deleteOpen = $state(false);
	let deletingProxy = $state<ProxyRead | null>(null);
	let isDeleting = $state(false);

	let proxies = $derived(proxiesStore.proxies);

	function openAdd() {
		editingId = null;
		formName = '';
		formDescription = '';
		formMode = 'single';
		formActive = true;
		formDefault = proxies.length === 0;
		formRows = [blankRow()];
		dialogOpen = true;
	}

	function openEdit(p: ProxyRead) {
		editingId = p.id;
		formName = p.name;
		formDescription = p.description ?? '';
		formMode = p.mode;
		formActive = p.is_active;
		formDefault = p.is_default;
		formRows = p.endpoints.map((e) => ({
			scheme: e.scheme,
			host: e.host,
			port: String(e.port),
			username: e.username ?? '',
			password: '',
			masked: e.has_password
		}));
		if (formRows.length === 0) formRows = [blankRow()];
		dialogOpen = true;
	}

	function addRow() {
		formRows = [...formRows, blankRow()];
	}

	function removeRow(i: number) {
		formRows = formRows.filter((_, idx) => idx !== i);
		if (formRows.length === 0) formRows = [blankRow()];
	}

	function setRow(i: number, key: keyof EndpointRow, value: string) {
		const rows = formRows.map((r) => ({ ...r }));
		(rows[i] as Record<string, unknown>)[key] = value;
		if (key === 'password') rows[i].masked = false;
		formRows = rows;
	}

	function buildEndpoints(): ProxyEndpoint[] | null {
		const out: ProxyEndpoint[] = [];
		for (const r of formRows) {
			const host = r.host.trim();
			const port = Math.trunc(Number(r.port));
			if (!host || !Number.isFinite(port) || port <= 0) continue;
			const username = r.username.trim() || null;
			let password: string | null;
			if (r.password) password = r.password;
			else if (r.masked) password = MASK;
			else password = null;
			out.push({ scheme: r.scheme, host, port, username, password });
		}
		return out.length > 0 ? out : null;
	}

	async function handleSave() {
		if (!formName.trim()) {
			toast.error('Proxy name is required');
			return;
		}
		const endpoints = buildEndpoints();
		if (!endpoints) {
			toast.error('Add at least one valid endpoint (host and port)');
			return;
		}

		saving = true;
		try {
			if (editingId) {
				const updated = await proxiesStore.update(editingId, {
					name: formName.trim(),
					description: formDescription.trim() || null,
					mode: formMode,
					is_active: formActive,
					is_default: formDefault,
					endpoints
				});
				if (updated) {
					toast.success('Proxy updated');
					dialogOpen = false;
				}
			} else {
				const created = await proxiesStore.create({
					name: formName.trim(),
					description: formDescription.trim() || null,
					mode: formMode,
					is_active: formActive,
					is_default: formDefault,
					endpoints
				});
				if (created) {
					toast.success('Proxy added');
					dialogOpen = false;
				}
			}
		} finally {
			saving = false;
		}
	}

	async function handleTest(id: string) {
		testingId = id;
		try {
			const result = await proxiesStore.test(id);
			if (!result) return;
			if (result.success) {
				const ms = result.latency_ms != null ? ` (${result.latency_ms} ms)` : '';
				toast.success(`${result.message}${ms}`);
			} else {
				toast.error(result.message);
			}
		} finally {
			testingId = null;
		}
	}

	async function handleSetDefault(id: string) {
		settingDefaultId = id;
		try {
			const updated = await proxiesStore.setDefault(id);
			if (updated) toast.success('Default proxy updated');
		} finally {
			settingDefaultId = null;
		}
	}

	function openDelete(p: ProxyRead) {
		deletingProxy = p;
		deleteOpen = true;
	}

	async function handleDelete() {
		if (!deletingProxy) return;
		isDeleting = true;
		try {
			const ok = await proxiesStore.remove(deletingProxy.id);
			if (ok) {
				toast.success('Proxy removed');
				deleteOpen = false;
			}
		} finally {
			isDeleting = false;
		}
	}

	onMount(async () => {
		if (!proxiesStore.hasFetched) await proxiesStore.fetch();
		isLoading = false;
	});
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between">
		<div>
			<h3 class="text-lg font-semibold">Proxies</h3>
			<p class="text-sm text-muted-foreground">
				Route scan traffic through proxies. The default applies to scan contexts that don't pick
				one.
			</p>
		</div>
		<Button size="sm" onclick={openAdd}>
			<PlusIcon class="mr-1.5 size-4" />
			Add proxy
		</Button>
	</div>

	<Separator />

	{#if isLoading}
		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<Card.Root>
					<Card.Content class="p-5">
						<div class="flex items-start gap-3">
							<Skeleton class="size-10 rounded-lg" />
							<div class="flex-1 space-y-2">
								<Skeleton class="h-5 w-28" />
								<Skeleton class="h-4 w-full" />
							</div>
						</div>
					</Card.Content>
				</Card.Root>
			{/each}
		</div>
	{:else if proxies.length === 0}
		<Card.Root class="border-dashed">
			<Card.Content class="flex flex-col items-center justify-center gap-3 py-16 text-center">
				<RouteIcon class="size-10 text-muted-foreground/40" />
				<div class="space-y-1">
					<p class="text-sm font-medium">No proxies configured</p>
					<p class="text-xs text-muted-foreground">
						Add a proxy to route recon traffic through it.
					</p>
				</div>
				<Button size="sm" variant="outline" onclick={openAdd}>
					<PlusIcon class="mr-1.5 size-4" />
					Add proxy
				</Button>
			</Card.Content>
		</Card.Root>
	{:else}
		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#each proxies as proxy (proxy.id)}
				<Card.Root
					class="relative transition-all duration-200 {proxy.is_active
						? 'ring-1 ring-border'
						: 'border-dashed opacity-75'}"
				>
					<Card.Content class="p-5">
						<div class="flex items-start justify-between gap-3">
							<div class="flex min-w-0 items-start gap-3">
								<div class="shrink-0 rounded-lg bg-muted p-2.5">
									<RouteIcon class="size-5 text-foreground" />
								</div>
								<div class="min-w-0">
									<div class="flex items-center gap-2">
										<h4 class="truncate text-sm font-medium">{proxy.name}</h4>
										{#if proxy.is_default}
											<Badge variant="secondary" class="h-5 shrink-0 border-0 px-1.5 text-[10px]"
												>Default</Badge
											>
										{/if}
									</div>
									<p class="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
										{proxy.description ||
											`${PROXY_MODE_LABELS[proxy.mode as (typeof PROXY_MODES)[number]] ?? proxy.mode} · ${proxy.endpoint_count} endpoint${proxy.endpoint_count === 1 ? '' : 's'}`}
									</p>
								</div>
							</div>
							<Switch
								checked={proxy.is_active}
								onCheckedChange={(checked) =>
									proxiesStore.update(proxy.id, { is_active: checked }).then((u) => {
										if (u) toast.success(checked ? 'Proxy enabled' : 'Proxy disabled');
									})}
							/>
						</div>

						<Separator class="my-3" />

						<div class="space-y-2">
							{#each proxy.endpoints.slice(0, 3) as ep (ep.url_masked)}
								<code class="block truncate font-mono text-xs text-muted-foreground"
									>{ep.url_masked}</code
								>
							{/each}
							{#if proxy.endpoint_count > 3}
								<p class="text-xs text-muted-foreground">+{proxy.endpoint_count - 3} more</p>
							{/if}
						</div>

						{#if proxy.last_test_at}
							<div class="mt-3 flex items-center gap-1.5 text-xs">
								{#if proxy.last_test_ok}
									<CheckIcon class="size-3 text-foreground" />
								{:else}
									<CircleXIcon class="size-3 text-destructive" />
								{/if}
								<span class="text-muted-foreground">Tested {formatDate(proxy.last_test_at)}</span>
							</div>
						{/if}

						<div class="mt-3 flex items-center gap-1.5">
							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<Button
											{...props}
											variant="ghost"
											size="sm"
											class="h-7 px-2 text-xs"
											onclick={() => openEdit(proxy)}
										>
											<Pencil class="mr-1 size-3" />
											Edit
										</Button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content>Edit proxy</Tooltip.Content>
							</Tooltip.Root>

							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<Button
											{...props}
											variant="ghost"
											size="sm"
											class="h-7 px-2 text-xs"
											disabled={testingId === proxy.id}
											onclick={() => handleTest(proxy.id)}
										>
											{#if testingId === proxy.id}
												<Spinner class="mr-1 size-3" />
											{:else}
												<FlaskConicalIcon class="mr-1 size-3" />
											{/if}
											Test
										</Button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content>Run a live reachability check</Tooltip.Content>
							</Tooltip.Root>

							{#if !proxy.is_default}
								<Tooltip.Root>
									<Tooltip.Trigger>
										{#snippet child({ props })}
											<Button
												{...props}
												variant="ghost"
												size="sm"
												class="h-7 px-2 text-xs"
												disabled={settingDefaultId === proxy.id}
												onclick={() => handleSetDefault(proxy.id)}
											>
												{#if settingDefaultId === proxy.id}
													<Spinner class="mr-1 size-3" />
												{:else}
													<StarIcon class="mr-1 size-3" />
												{/if}
												Default
											</Button>
										{/snippet}
									</Tooltip.Trigger>
									<Tooltip.Content>Set as the default proxy</Tooltip.Content>
								</Tooltip.Root>
							{/if}

							<div class="flex-1"></div>

							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<Button
											{...props}
											variant="ghost"
											size="sm"
											class="h-7 px-2 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
											onclick={() => openDelete(proxy)}
										>
											<Trash2Icon class="size-3" />
										</Button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content>Remove proxy</Tooltip.Content>
							</Tooltip.Root>
						</div>
					</Card.Content>
				</Card.Root>
			{/each}
		</div>
	{/if}
</div>

<Dialog.Root bind:open={dialogOpen}>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
		<Dialog.Header class="px-6 pt-6 pb-2">
			<Dialog.Title>{editingId ? 'Edit proxy' : 'Add proxy'}</Dialog.Title>
			<Dialog.Description>
				Define one or more endpoints. Passwords are stored encrypted and never shown again.
			</Dialog.Description>
		</Dialog.Header>

		<ScrollArea class="flex-1">
			<div class="space-y-5 px-6 py-4">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormField label="Name">
						{#snippet children({ id })}
							<Input
								{id}
								bind:value={formName}
								placeholder="Residential pool"
								class="h-9"
								disabled={saving}
							/>
						{/snippet}
					</FormField>
					<div class="space-y-1.5">
						<Label class="text-xs">Mode</Label>
						<Select.Root type="single" bind:value={formMode}>
							<Select.Trigger class="h-9 w-full text-sm"
								>{PROXY_MODE_LABELS[formMode as (typeof PROXY_MODES)[number]] ??
									'Single'}</Select.Trigger
							>
							<Select.Content>
								{#each PROXY_MODES as m (m)}
									<Select.Item value={m} label={PROXY_MODE_LABELS[m]}
										>{PROXY_MODE_LABELS[m]}</Select.Item
									>
								{/each}
							</Select.Content>
						</Select.Root>
					</div>
				</div>

				<FormField label="Description" description="Optional">
					{#snippet children({ id })}
						<Input
							{id}
							bind:value={formDescription}
							placeholder="What this proxy is for"
							class="h-9"
							disabled={saving}
						/>
					{/snippet}
				</FormField>

				<Separator />

				<div class="space-y-3">
					<Label class="text-xs">Endpoints</Label>
					{#each formRows as row, i (i)}
						<div class="space-y-3 rounded-lg border bg-muted/30 p-3">
							<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-[6.5rem_1fr_5.5rem_auto]">
								<div class="space-y-1">
									<Label class="text-[10px] uppercase tracking-wide text-muted-foreground"
										>Scheme</Label
									>
									<Select.Root
										type="single"
										value={row.scheme}
										onValueChange={(v) => setRow(i, 'scheme', v ?? 'http')}
									>
										<Select.Trigger class="h-9 w-full text-sm"
											>{PROXY_SCHEME_LABELS[row.scheme as (typeof PROXY_SCHEMES)[number]] ??
												'HTTP'}</Select.Trigger
										>
										<Select.Content>
											{#each PROXY_SCHEMES as s (s)}
												<Select.Item value={s} label={PROXY_SCHEME_LABELS[s]}
													>{PROXY_SCHEME_LABELS[s]}</Select.Item
												>
											{/each}
										</Select.Content>
									</Select.Root>
								</div>
								<div class="space-y-1">
									<Label class="text-[10px] uppercase tracking-wide text-muted-foreground"
										>Host</Label
									>
									<Input
										value={row.host}
										placeholder="gate.provider.com"
										class="h-9 font-mono text-xs"
										autocomplete="off"
										oninput={(e) => setRow(i, 'host', e.currentTarget.value)}
									/>
								</div>
								<div class="space-y-1">
									<Label class="text-[10px] uppercase tracking-wide text-muted-foreground"
										>Port</Label
									>
									<Input
										type="number"
										min="1"
										max="65535"
										value={row.port}
										placeholder="8080"
										class="h-9 font-mono text-xs"
										oninput={(e) => setRow(i, 'port', e.currentTarget.value)}
									/>
								</div>
								<div class="flex items-end">
									<Button
										variant="ghost"
										size="icon"
										class="h-9 w-9 shrink-0 text-muted-foreground hover:text-destructive"
										disabled={formRows.length === 1}
										onclick={() => removeRow(i)}
										aria-label="Remove endpoint"
									>
										<XIcon class="size-4" />
									</Button>
								</div>
							</div>
							<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
								<div class="space-y-1">
									<Label class="text-[10px] uppercase tracking-wide text-muted-foreground"
										>Username <span class="normal-case">(optional)</span></Label
									>
									<Input
										value={row.username}
										placeholder="username"
										class="h-9 font-mono text-xs"
										autocomplete="off"
										oninput={(e) => setRow(i, 'username', e.currentTarget.value)}
									/>
								</div>
								<div class="space-y-1">
									<Label class="text-[10px] uppercase tracking-wide text-muted-foreground"
										>Password <span class="normal-case">(optional)</span></Label
									>
									<Input
										type="password"
										value={row.password}
										placeholder={row.masked ? 'Leave blank to keep current' : 'password'}
										class="h-9 font-mono text-xs"
										autocomplete="off"
										oninput={(e) => setRow(i, 'password', e.currentTarget.value)}
									/>
								</div>
							</div>
						</div>
					{/each}
					<Button
						variant="ghost"
						size="sm"
						class="h-8 gap-1.5 text-muted-foreground"
						onclick={addRow}
					>
						<PlusIcon class="size-3.5" />
						Add endpoint
					</Button>
				</div>

				<Separator />

				<div class="flex items-center justify-between rounded-lg border px-4 py-3">
					<div class="space-y-0.5">
						<Label class="text-sm font-medium">Set as default</Label>
						<p class="text-xs text-muted-foreground">Used by contexts that don't pick a proxy.</p>
					</div>
					<Switch
						checked={formDefault}
						onCheckedChange={(v) => (formDefault = v)}
						disabled={saving}
					/>
				</div>
			</div>
		</ScrollArea>

		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" onclick={() => (dialogOpen = false)} disabled={saving}
				>Cancel</Button
			>
			<LoadingButton onclick={handleSave} loading={saving} loadingLabel="Saving...">
				{editingId ? 'Save changes' : 'Add proxy'}
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<DeleteConfirmationDialog
	bind:open={deleteOpen}
	title="Remove proxy"
	description={`Are you sure you want to remove ${deletingProxy?.name ?? 'this proxy'}? Scan contexts using it will fall back to direct traffic.`}
	confirmLabel="Remove proxy"
	{isDeleting}
	onOpenChange={(o) => (deleteOpen = o)}
	onConfirm={handleDelete}
/>
