<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { page } from '$app/state';
	import { goto, beforeNavigate } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { AlertTriangle, Loader2, ChevronLeft, Copy, Trash2, Save, ChevronDown, Info } from 'lucide-svelte';

	import { Button } from '$lib/components/ui/button';
	import * as Empty from '$lib/components/ui/empty';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Label } from '$lib/components/ui/label';
	import * as Card from '$lib/components/ui/card';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Popover from '$lib/components/ui/popover';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CopyButton from '@/components/copy-button.svelte';

	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scanContextsApi } from '$lib/api/scan-contexts';

	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import AuthSection from '$lib/components/contexts/auth-section.svelte';
	import RateSection from '$lib/components/contexts/rate-section.svelte';
	import ScopeSection from '$lib/components/contexts/scope-section.svelte';
	import RuntimeSection from '$lib/components/contexts/runtime-section.svelte';
	import ProxySection from '$lib/components/contexts/proxy-section.svelte';
	import { buildContextSummary } from '$lib/components/contexts/context-summary';

	import {
		DEFAULT_SCAN_CONTEXT,
		MASK,
		type ScanContextRead,
		type ScanContextCreate,
		type ScanContextUpdate,
		type AuthConfig,
		type AuthHeader
	} from '$lib/types/scan-context';

	type Draft = ScanContextCreate;

	// ── Route param ────────────────────────────────────────────────────────────
	let contextId = $derived(page.params.id);
	let isNew = $derived(contextId === 'new');

	// ── Page state ─────────────────────────────────────────────────────────────
	let loaded = $state<ScanContextRead | null>(null);
	let draft = $state<Draft | null>(null);
	let isLoading = $state(false);
	let loadError = $state<string | null>(null);
	let isSaving = $state(false);
	let isDuplicating = $state(false);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);

	let nameInputEl = $state<HTMLInputElement | null>(null);

	let showLeaveDialog = $state(false);
	let pendingNav: (() => void) | null = $state(null);
	let bypassGuard = false;

	let touchedSecrets = new SvelteSet<string>();

	let seedKey = $state(0);

	const SECRET_KEYS = [
		'bearer_token',
		'basic_password',
		'header_value',
		'cookie_value',
		'api_key_value'
	] as const;

	// ── Dirty detection ──────────────────────────────────────────────────────────
	let baseline = $state<string>('');
	let hasUnsavedChanges = $derived.by(() => {
		if (!draft) return false;
		if (isNew) return true;
		return JSON.stringify(draft) !== baseline;
	});

	// ── Validation ─────────────────────────────────────────────────────────────────
	function isPathValid(v: string): boolean {
		return v.startsWith('/');
	}

	function isIpValid(v: string): boolean {
		const cidr = v.split('/');
		if (cidr.length > 2) return false;
		const ip = cidr[0];
		const v4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
		const v6 = /^[0-9a-fA-F:]+$/;
		const isV4 = v4.test(ip) && ip.split('.').every((o) => Number(o) <= 255);
		const isV6 = v6.test(ip) && ip.includes(':');
		if (!isV4 && !isV6) return false;
		if (cidr.length === 2) {
			const n = Number(cidr[1]);
			const maxPrefix = isV6 ? 128 : 32;
			if (cidr[1].trim() === '' || !Number.isInteger(n) || n < 0 || n > maxPrefix) return false;
		}
		return true;
	}

	let validationIssue = $derived.by<{ message: string; section: keyof typeof open } | null>(() => {
		if (!draft) return null;
		if (!draft.name.trim()) return { message: 'Name is required', section: 'identity' };
		const badPaths = draft.excluded_paths.filter((p) => !isPathValid(p)).length;
		if (badPaths > 0)
			return { message: `Fix ${badPaths} invalid path in Scope`, section: 'scope' };
		const badIps = draft.excluded_ips.filter((ip) => !isIpValid(ip)).length;
		if (badIps > 0) return { message: `Fix ${badIps} invalid IP in Scope`, section: 'scope' };
		const badHeader = draft.extra_headers.some((h) => !h.name.trim() && h.value.trim());
		if (badHeader)
			return { message: 'A header has a value but no name in Authentication', section: 'auth' };
		if (draft.auth_type === 'api_key' && !draft.auth?.api_key_name?.trim())
			return { message: 'API key auth needs a key name in Authentication', section: 'auth' };
		return null;
	});
	let isValid = $derived(validationIssue === null);

	// ── Load / init ───────────────────────────────────────────────────────────────
	$effect(() => {
		const project = projectsStore.activeProject;
		const id = contextId;
		if (!project) return;
		untrack(() => {
			if (id === 'new') {
				initNew();
			} else if (id) {
				loadContext(id, project.id);
			}
		});
	});

	$effect(() => {
		if (isNew && draft && nameInputEl) nameInputEl.focus();
	});

	beforeNavigate((nav) => {
		if (bypassGuard) {
			bypassGuard = false;
			return;
		}
		if (!hasUnsavedChanges || showLeaveDialog) return;
		if (nav.willUnload) return;
		nav.cancel();
		pendingNav = () => {
			bypassGuard = true;
			if (nav.to) goto(nav.to.url);
		};
		showLeaveDialog = true;
	});

	$effect(() => {
		function onBeforeUnload(e: BeforeUnloadEvent) {
			if (hasUnsavedChanges) {
				e.preventDefault();
				e.returnValue = '';
			}
		}
		window.addEventListener('beforeunload', onBeforeUnload);
		return () => window.removeEventListener('beforeunload', onBeforeUnload);
	});

	function confirmLeave() {
		showLeaveDialog = false;
		const go = pendingNav;
		pendingNav = null;
		go?.();
	}

	function cancelLeave() {
		showLeaveDialog = false;
		pendingNav = null;
	}

	function onKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
			e.preventDefault();
			if (draft && !isSaving) handleSave();
		}
	}

	function initNew() {
		const d = DEFAULT_SCAN_CONTEXT();
		d.name = '';
		draft = d;
		loaded = null;
		baseline = '';
		touchedSecrets = new SvelteSet();
		seedKey++;
	}

	function readToDraft(ctx: ScanContextRead): Draft {
		return {
			name: ctx.name,
			description: ctx.description,
			auth_type: ctx.auth_type,
			auth: { ...ctx.auth },
			extra_headers: ctx.extra_headers.map((h) => ({ ...h })),
			global_rate_limit_override: ctx.global_rate_limit_override,
			per_tool_rate_overrides: { ...ctx.per_tool_rate_overrides },
			thread_multiplier: ctx.thread_multiplier,
			timeout_multiplier: ctx.timeout_multiplier,
			excluded_subdomains: [...ctx.excluded_subdomains],
			excluded_paths: [...ctx.excluded_paths],
			excluded_ips: [...ctx.excluded_ips],
			included_subdomains: [...ctx.included_subdomains],
			follow_redirects_override: ctx.follow_redirects_override,
			http_protocol: ctx.http_protocol,
			proxy_id: ctx.proxy_id,
			compare_baseline_scan_id: ctx.compare_baseline_scan_id,
			scan_only_new_assets: ctx.scan_only_new_assets
		};
	}

	async function loadContext(id: string, projectId: string) {
		isLoading = true;
		loadError = null;
		touchedSecrets = new SvelteSet();
		try {
			const cached = scanContextsStore.contexts.find((c) => c.id === id);
			if (cached) {
				loaded = cached;
				draft = JSON.parse(JSON.stringify(readToDraft(cached)));
				baseline = JSON.stringify(draft);
				seedKey++;
			}
			const fresh = await scanContextsApi.get(id, projectId);
			loaded = fresh;
			if (!hasUnsavedChanges) {
				draft = JSON.parse(JSON.stringify(readToDraft(fresh)));
				baseline = JSON.stringify(draft);
				seedKey++;
			}
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load context';
		} finally {
			isLoading = false;
		}
	}

	function retryLoad() {
		const project = projectsStore.activeProject;
		if (project && contextId && !isNew) loadContext(contextId, project.id);
	}

	// ── Section change handlers ────────────────────────────────────────────────
	function patchDraft(updates: Partial<Draft>) {
		if (!draft) return;
		draft = { ...draft, ...updates };
	}

	function handleAuthChange(next: { auth: AuthConfig; extraHeaders: AuthHeader[] }) {
		if (!draft) return;
		for (const k of SECRET_KEYS) {
			const v = next.auth[k];
			if (v != null && v !== MASK) touchedSecrets.add(k);
		}
		touchedSecrets = new SvelteSet(touchedSecrets);
		draft = {
			...draft,
			auth_type: next.auth.auth_type as Draft['auth_type'],
			auth: next.auth,
			extra_headers: next.extraHeaders
		};
	}

	// ── Save ──────────────────────────────────────────────────────────────────
	function buildAuthPayload(): Partial<AuthConfig> | undefined {
		if (!draft) return undefined;
		const a = draft.auth;
		if (!a) return undefined;
		const out: Partial<AuthConfig> = { auth_type: a.auth_type };

		const visible: (keyof AuthConfig)[] = [
			'basic_username',
			'header_name',
			'api_key_name'
		];
		for (const k of visible) {
			if (a[k] != null) out[k] = a[k];
		}

		for (const k of SECRET_KEYS) {
			const v = a[k];
			if (touchedSecrets.has(k) && v !== MASK) {
				out[k] = v;
			}
		}
		return out;
	}

	function buildPayload(): ScanContextCreate {
		const d = draft!;
		return {
			name: d.name,
			description: d.description,
			auth_type: d.auth_type,
			auth: buildAuthPayload() as ScanContextCreate['auth'],
			extra_headers: d.extra_headers,
			global_rate_limit_override: d.global_rate_limit_override,
			per_tool_rate_overrides: d.per_tool_rate_overrides,
			thread_multiplier: d.thread_multiplier,
			timeout_multiplier: d.timeout_multiplier,
			excluded_subdomains: d.excluded_subdomains,
			excluded_paths: d.excluded_paths,
			excluded_ips: d.excluded_ips,
			included_subdomains: d.included_subdomains,
			follow_redirects_override: d.follow_redirects_override,
			http_protocol: d.http_protocol,
			proxy_id: d.proxy_id,
			compare_baseline_scan_id: null,
			scan_only_new_assets: false
		};
	}

	async function handleSave() {
		if (!draft || isSaving) return;
		if (validationIssue) {
			open[validationIssue.section] = true;
			toast.error(validationIssue.message);
			return;
		}
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project');
			return;
		}

		isSaving = true;
		try {
			if (isNew) {
				const created = await scanContextsStore.createContext(project.id, buildPayload());
				if (created) {
					toast.success('Context created');
					loaded = created;
					draft = JSON.parse(JSON.stringify(readToDraft(created)));
					baseline = JSON.stringify(draft);
					touchedSecrets = new SvelteSet();
					seedKey++;
					bypassGuard = true;
					goto(`/automation/contexts/${created.id}`, { replaceState: true });
				} else {
					toast.error(scanContextsStore.error ?? 'Failed to create context');
				}
			} else {
				const update: ScanContextUpdate = buildPayload();
				delete update.compare_baseline_scan_id;
				delete update.scan_only_new_assets;
				const updated = await scanContextsStore.updateContext(contextId!, project.id, update);
				if (updated) {
					loaded = updated;
					draft = JSON.parse(JSON.stringify(readToDraft(updated)));
					baseline = JSON.stringify(draft);
					touchedSecrets = new SvelteSet();
					seedKey++;
					toast.success('Context saved');
				} else {
					toast.error(scanContextsStore.error ?? 'Failed to save context');
				}
			}
		} finally {
			isSaving = false;
		}
	}

	async function handleDuplicate() {
		const project = projectsStore.activeProject;
		if (!project || !contextId || isNew || isDuplicating) return;
		if (hasUnsavedChanges) {
			toast.warning('Unsaved changes are not copied — the saved version is duplicated.');
		}
		isDuplicating = true;
		try {
			const dup = await scanContextsStore.duplicateContext(contextId, project.id);
			if (dup?.id) {
				toast.success(`Duplicated as "${dup.name}"`);
				bypassGuard = true;
				goto(`/automation/contexts/${dup.id}`);
			} else {
				toast.error(scanContextsStore.error ?? 'Duplicate failed');
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Duplicate failed');
		} finally {
			isDuplicating = false;
		}
	}

	function requestDelete() {
		if (!contextId || isNew) return;
		showDeleteDialog = true;
	}

	async function handleDelete() {
		if (!contextId || isNew) return;
		const project = projectsStore.activeProject;
		isDeleting = true;
		try {
			const ok = await scanContextsStore.deleteContext(contextId, project?.id);
			if (ok) {
				toast.success('Context deleted');
				showDeleteDialog = false;
				bypassGuard = true;
				goto('/automation/contexts');
			} else {
				toast.error(scanContextsStore.error ?? 'Delete failed');
			}
		} catch {
			toast.error('Delete failed');
		} finally {
			isDeleting = false;
		}
	}

	function handleBack() {
		goto('/automation/contexts');
	}

	// ── Collapsible open state ─────────────────────────────────────────────────
	let open = $state({
		identity: true,
		auth: true,
		rate: false,
		scope: false,
		runtime: false,
		proxy: false
	});

	let summary = $derived(draft ? buildContextSummary(draft) : '');
</script>

<svelte:window onkeydown={onKeydown} />

<div class="mx-auto w-full max-w-5xl space-y-6">
	{#if isLoading && !loaded && !isNew}
		<div class="flex items-center gap-2">
			<Skeleton class="h-8 w-8 rounded-md" />
			<Skeleton class="h-9 w-56" />
			<div class="ml-auto flex gap-2">
				<Skeleton class="h-8 w-24" />
				<Skeleton class="h-8 w-20" />
			</div>
		</div>
		<div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
			<div class="space-y-4">
				{#each Array(6) as _, i (i)}
					<Skeleton class="h-16 w-full rounded-xl" />
				{/each}
			</div>
			<Skeleton class="hidden h-48 w-full rounded-xl lg:block" />
		</div>
	{:else if loadError}
		<Empty.Root class="min-h-[50vh]">
			<Empty.Header>
				<Empty.Media class="size-[52px] rounded-xl bg-destructive/10">
					<AlertTriangle size={22} class="text-destructive" />
				</Empty.Media>
				<Empty.Title>Failed to load context</Empty.Title>
				<Empty.Description>{loadError}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<div class="flex items-center gap-2">
					<Button onclick={retryLoad} disabled={isLoading}>
						{#if isLoading}<Loader2 class="h-3.5 w-3.5 animate-spin" />{/if}
						Retry
					</Button>
					<Button variant="outline" onclick={() => goto('/automation/contexts')}>
						Back to Contexts
					</Button>
				</div>
			</Empty.Content>
		</Empty.Root>
	{:else if draft}
		<div class="flex flex-wrap items-center gap-2">
			<div class="flex min-w-0 flex-1 items-center gap-2">
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="h-8 w-8 shrink-0"
								aria-label="Back to Contexts"
								onclick={handleBack}
							>
								<ChevronLeft class="h-4 w-4" />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content><p>Back to Contexts</p></Tooltip.Content>
				</Tooltip.Root>
				<Input
					bind:value={draft.name}
					bind:ref={nameInputEl}
					placeholder="Context name"
					onkeydown={(e) => e.key === 'Enter' && handleSave()}
					class="h-9 min-w-0 flex-1 sm:max-w-sm border-transparent bg-transparent text-base font-semibold shadow-none focus-visible:border-input focus-visible:bg-background"
				/>
			</div>
			<div class="flex flex-wrap items-center justify-end gap-2">
				{#if !isNew}
					{#if contextId}
						<CopyButton value={contextId} class="h-8 w-8" />
					{/if}
					<Button
						variant="ghost"
						size="sm"
						class="gap-1.5"
						disabled={isDuplicating}
						onclick={handleDuplicate}
					>
						{#if isDuplicating}
							<Loader2 class="h-3.5 w-3.5 animate-spin" />
						{:else}
							<Copy class="h-3.5 w-3.5" />
						{/if}
						Duplicate
					</Button>
					<Button
						variant="ghost"
						size="sm"
						class="gap-1.5 text-destructive hover:text-destructive"
						onclick={requestDelete}
					>
						<Trash2 class="h-3.5 w-3.5" /> Delete
					</Button>
				{/if}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								class="gap-1.5"
								size="sm"
								disabled={isSaving || !isValid}
								onclick={handleSave}
							>
								{#if isSaving}
									<Loader2 class="h-3.5 w-3.5 animate-spin" />
								{:else}
									<Save class="h-3.5 w-3.5" />
								{/if}
								Save
								{#if hasUnsavedChanges}<span class="dirty-dot"></span>{/if}
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>
						<p>{validationIssue ? validationIssue.message : 'Save changes (⌘S)'}</p>
					</Tooltip.Content>
				</Tooltip.Root>
			</div>
		</div>

		<p class="text-xs text-muted-foreground lg:hidden">{summary}</p>

		<div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
			<div class="space-y-4">
				{#snippet section(
					key: keyof typeof open,
					title: string,
					subtitle: string,
					content: import('svelte').Snippet,
					info?: import('svelte').Snippet
				)}
					<Card.Root>
						<Collapsible.Root bind:open={open[key]}>
							<Card.Header class="flex flex-row items-center justify-between gap-2 py-4 text-left">
								<Collapsible.Trigger class="flex min-w-0 flex-1 items-center justify-between gap-2">
									<div class="min-w-0">
										<Card.Title class="text-sm">{title}</Card.Title>
										<Card.Description class="text-xs">{subtitle}</Card.Description>
									</div>
									<ChevronDown
										class="h-4 w-4 shrink-0 text-muted-foreground transition-transform {open[key] ? 'rotate-180' : ''}"
									/>
								</Collapsible.Trigger>
								{#if info}
									<Popover.Root>
										<Popover.Trigger>
											{#snippet child({ props })}
												<Button
													{...props}
													variant="ghost"
													size="icon"
													class="h-7 w-7 shrink-0 text-muted-foreground"
													aria-label="Merge behaviour"
												>
													<Info class="h-3.5 w-3.5" />
												</Button>
											{/snippet}
										</Popover.Trigger>
										<Popover.Content class="w-72 text-xs text-muted-foreground">
											{@render info()}
										</Popover.Content>
									</Popover.Root>
								{/if}
							</Card.Header>
							<Collapsible.Content>
								<Card.Content class="pb-5">
									{@render content()}
								</Card.Content>
							</Collapsible.Content>
						</Collapsible.Root>
					</Card.Root>
				{/snippet}

				{#snippet authInfo()}
					<p class="mb-1 font-medium text-foreground">Merge behaviour</p>
					<ul class="space-y-1 pl-3">
						<li class="list-disc">Headers: engine ∪ context — context wins on conflict.</li>
						<li class="list-disc">A context cannot enable a tool the engine disabled.</li>
					</ul>
				{/snippet}

				{#snippet rateInfo()}
					<p class="mb-1 font-medium text-foreground">Merge behaviour</p>
					<ul class="space-y-1 pl-3">
						<li class="list-disc">Context rate overrides take precedence over engine defaults.</li>
						<li class="list-disc">A context cannot enable a tool the engine disabled.</li>
					</ul>
				{/snippet}

				{#snippet identityBody()}
					<div class="space-y-4">
						<div class="space-y-1.5">
							<Label class="text-xs">Name</Label>
							<Input bind:value={draft!.name} placeholder="e.g. Authenticated staging" class="h-9" />
						</div>
						<div class="space-y-1.5">
							<Label class="text-xs">Description</Label>
							<Textarea
								value={draft!.description ?? ''}
								placeholder="What this context is for (optional)"
								class="min-h-20"
								oninput={(e) => patchDraft({ description: e.currentTarget.value || null })}
							/>
						</div>
					</div>
				{/snippet}

				{#snippet authBody()}
					{#key seedKey}
						<AuthSection
							auth={draft!.auth as AuthConfig}
							extraHeaders={draft!.extra_headers}
							onChange={handleAuthChange}
						/>
					{/key}
				{/snippet}

				{#snippet rateBody()}
					<RateSection context={draft!} onChange={patchDraft} />
				{/snippet}

				{#snippet scopeBody()}
					<ScopeSection context={draft!} onChange={patchDraft} />
				{/snippet}

				{#snippet runtimeBody()}
					<RuntimeSection context={draft!} onChange={patchDraft} />
				{/snippet}

				{#snippet proxyBody()}
					<ProxySection context={draft!} onChange={patchDraft} />
				{/snippet}

				{@render section('identity', 'Identity', 'Name and description', identityBody)}
				{@render section('auth', 'Authentication', 'How requests authenticate to the target', authBody, authInfo)}
				{@render section('rate', 'Rate Limiting', 'Throughput ceilings and concurrency', rateBody, rateInfo)}
				{@render section('scope', 'Scope', 'Include / exclude rules for assets', scopeBody)}
				{@render section('runtime', 'Runtime Options', 'Protocol and redirect behaviour', runtimeBody)}
				{@render section('proxy', 'Proxy', 'Route scan traffic through a proxy', proxyBody)}
			</div>

			<div class="hidden lg:block">
				<Card.Root class="lg:sticky lg:top-6">
					<Card.Header class="py-4">
						<Card.Title class="text-sm">Summary</Card.Title>
						<Card.Description class="text-xs">{summary}</Card.Description>
					</Card.Header>
					<Card.Content class="space-y-3 pb-5 text-xs text-muted-foreground">
						<div>
							<p class="mb-1 font-medium text-foreground">Merge notes</p>
							<ul class="space-y-1 pl-3">
								<li class="list-disc">Headers: engine ∪ context — context wins on conflict.</li>
								<li class="list-disc">A context cannot enable a tool the engine disabled.</li>
							</ul>
						</div>
					</Card.Content>
				</Card.Root>
			</div>
		</div>
	{/if}
</div>

{#if !isNew}
	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete Context"
		description="Are you sure you want to delete '{draft?.name ?? 'this context'}'? This action cannot be undone."
		{isDeleting}
		onOpenChange={(open) => (showDeleteDialog = open)}
		onConfirm={handleDelete}
	/>
{/if}

<AlertDialog.Root bind:open={showLeaveDialog}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Discard unsaved changes?</AlertDialog.Title>
			<AlertDialog.Description>
				You have unsaved changes to this context. If you leave now, they will be lost.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel onclick={cancelLeave}>Keep editing</AlertDialog.Cancel>
			<AlertDialog.Action
				class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
				onclick={confirmLeave}
			>
				Discard
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>

<style>
	.dirty-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: currentColor;
		margin-left: 2px;
	}
</style>
