<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { AlertTriangle, Loader2, ChevronLeft, Copy, Trash2, Save, ChevronDown } from 'lucide-svelte';

	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Label } from '$lib/components/ui/label';
	import * as Card from '$lib/components/ui/card';
	import * as Collapsible from '$lib/components/ui/collapsible';

	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scanContextsApi } from '$lib/api/scan-contexts';

	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import AuthSection from '$lib/components/contexts/auth-section.svelte';
	import RateSection from '$lib/components/contexts/rate-section.svelte';
	import ScopeSection from '$lib/components/contexts/scope-section.svelte';
	import RuntimeSection from '$lib/components/contexts/runtime-section.svelte';
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

	// Editable shape: the Create payload plus a name we always control.
	type Draft = ScanContextCreate;

	// ── Route param ────────────────────────────────────────────────────────────
	let contextId = $derived(page.params.id);
	let isNew = $derived(contextId === 'new');

	// ── Page state ─────────────────────────────────────────────────────────────
	let loaded = $state<ScanContextRead | null>(null); // server snapshot (edit mode)
	let draft = $state<Draft | null>(null); // local edited copy
	let isLoading = $state(false);
	let loadError = $state<string | null>(null);
	let isSaving = $state(false);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);

	// Secret fields the user has actually typed this session — only these are sent.
	let touchedSecrets = $state<Set<string>>(new Set());

	// Bumped whenever the underlying record is (re)loaded or saved, so the
	// AuthSection remounts and re-derives its secret/mask state from fresh props.
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

	function initNew() {
		const d = DEFAULT_SCAN_CONTEXT();
		d.name = '';
		draft = d;
		loaded = null;
		baseline = '';
		touchedSecrets = new Set();
		seedKey++;
	}

	// Map a server Read into an editable draft. Secrets arrive as MASK; we keep
	// them as MASK in the draft so the auth-section can show the "value set" hint,
	// but they are STRIPPED at save time unless the user typed a replacement.
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
			compare_baseline_scan_id: ctx.compare_baseline_scan_id,
			scan_only_new_assets: ctx.scan_only_new_assets
		};
	}

	async function loadContext(id: string, projectId: string) {
		isLoading = true;
		loadError = null;
		touchedSecrets = new Set();
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

	// ── Section change handlers ────────────────────────────────────────────────
	function patchDraft(updates: Partial<Draft>) {
		if (!draft) return;
		draft = { ...draft, ...updates };
	}

	function handleAuthChange(next: { auth: AuthConfig; extraHeaders: AuthHeader[] }) {
		if (!draft) return;
		// Record which secrets were typed (non-mask, non-null) so save sends only those.
		for (const k of SECRET_KEYS) {
			const v = next.auth[k];
			if (v != null && v !== MASK) touchedSecrets.add(k);
		}
		touchedSecrets = new Set(touchedSecrets);
		draft = {
			...draft,
			auth_type: next.auth.auth_type as Draft['auth_type'],
			auth: next.auth,
			extra_headers: next.extraHeaders
		};
	}

	// ── Save ──────────────────────────────────────────────────────────────────
	// CRITICAL: build the auth payload omitting any secret the user did NOT type,
	// so the masked placeholder is never round-tripped back to the server.
	function buildAuthPayload(): Partial<AuthConfig> | undefined {
		if (!draft) return undefined;
		const a = draft.auth;
		if (!a) return undefined;
		const out: Partial<AuthConfig> = { auth_type: a.auth_type };

		// Non-secret fields always included (visible, never masked).
		const visible: (keyof AuthConfig)[] = [
			'basic_username',
			'header_name',
			'api_key_name'
		];
		for (const k of visible) {
			if (a[k] != null) out[k] = a[k];
		}

		// Secret fields: include ONLY if the user typed this session.
		// A typed empty string ("") is allowed through to CLEAR the stored secret.
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
			compare_baseline_scan_id: null,
			scan_only_new_assets: false
		};
	}

	async function handleSave() {
		if (!draft || isSaving) return;
		if (!draft.name.trim()) {
			toast.error('Name is required');
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
					touchedSecrets = new Set();
					seedKey++;
					// goto (not bare replaceState) re-runs the route so page.params.id —
					// and therefore isNew/contextId — flip to the real saved record.
					goto(`/automation/contexts/${created.id}`, { replaceState: true });
				} else {
					toast.error(scanContextsStore.error ?? 'Failed to create context');
				}
			} else {
				const update: ScanContextUpdate = buildPayload();
				// PATCH semantics: omit deferred baseline fields rather than forcing
				// defaults, so a legacy non-default value isn't silently cleared.
				delete update.compare_baseline_scan_id;
				delete update.scan_only_new_assets;
				const updated = await scanContextsStore.updateContext(contextId!, project.id, update);
				if (updated) {
					loaded = updated;
					draft = JSON.parse(JSON.stringify(readToDraft(updated)));
					baseline = JSON.stringify(draft);
					touchedSecrets = new Set();
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
		if (!project || !contextId || isNew) return;
		try {
			const dup = await scanContextsStore.duplicateContext(contextId, project.id);
			if (dup?.id) {
				toast.success(`Duplicated as "${dup.name}"`);
				goto(`/automation/contexts/${dup.id}`);
			} else {
				toast.error('Duplicate failed');
			}
		} catch {
			toast.error('Duplicate failed');
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
		if (hasUnsavedChanges) {
			const leave = window.confirm('You have unsaved changes. Leave anyway?');
			if (!leave) return;
		}
		goto('/automation/contexts');
	}

	// ── Collapsible open state ─────────────────────────────────────────────────
	let open = $state({
		identity: true,
		auth: true,
		rate: false,
		scope: false,
		runtime: false
	});

	let summary = $derived(draft ? buildContextSummary(draft) : '');
</script>

<div class="form-shell">
	{#if isLoading && !loaded && !isNew}
		<div class="state-center">
			<Loader2 size={20} class="animate-spin text-muted-foreground" />
			<span class="text-sm text-muted-foreground">Loading context…</span>
		</div>
	{:else if loadError}
		<div class="state-center">
			<div class="error-icon">
				<AlertTriangle size={22} class="text-destructive" />
			</div>
			<div>
				<p class="error-title">Failed to load context</p>
				<p class="error-msg">{loadError}</p>
			</div>
			<Button onclick={() => goto('/automation/contexts')}>Back to Contexts</Button>
		</div>
	{:else if draft}
		<!-- Slim topbar -->
		<div class="topbar">
			<Button variant="ghost" size="icon" class="h-8 w-8 shrink-0" onclick={handleBack}>
				<ChevronLeft class="h-4 w-4" />
			</Button>
			<Input
				bind:value={draft.name}
				placeholder="Context name"
				class="h-9 max-w-sm border-transparent bg-transparent text-base font-semibold shadow-none focus-visible:border-input focus-visible:bg-background"
			/>
			<div class="flex-1"></div>
			{#if !isNew}
				<Button variant="ghost" size="sm" class="gap-1.5" onclick={handleDuplicate}>
					<Copy class="h-3.5 w-3.5" /> Duplicate
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
			<Button
				class="gap-1.5"
				size="sm"
				disabled={isSaving || !draft.name.trim()}
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
		</div>

		<!-- Body: centered form column + sticky summary -->
		<div class="body">
			<div class="form-col">
				{#snippet section(key: keyof typeof open, title: string, subtitle: string, content: import('svelte').Snippet)}
					<Card.Root>
						<Collapsible.Root bind:open={open[key]}>
							<Collapsible.Trigger class="w-full">
								<Card.Header class="flex flex-row items-center justify-between gap-2 py-4 text-left">
									<div>
										<Card.Title class="text-sm">{title}</Card.Title>
										<Card.Description class="text-xs">{subtitle}</Card.Description>
									</div>
									<ChevronDown
										class="h-4 w-4 shrink-0 text-muted-foreground transition-transform {open[key] ? 'rotate-180' : ''}"
									/>
								</Card.Header>
							</Collapsible.Trigger>
							<Collapsible.Content>
								<Card.Content class="pb-5">
									{@render content()}
								</Card.Content>
							</Collapsible.Content>
						</Collapsible.Root>
					</Card.Root>
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

				{@render section('identity', 'Identity', 'Name and description', identityBody)}
				{@render section('auth', 'Authentication', 'How requests authenticate to the target', authBody)}
				{@render section('rate', 'Rate Limiting', 'Throughput ceilings and concurrency', rateBody)}
				{@render section('scope', 'Scope', 'Include / exclude rules for assets', scopeBody)}
				{@render section('runtime', 'Runtime Options', 'Protocol and redirect behaviour', runtimeBody)}
			</div>

			<!-- Sticky summary -->
			<div class="summary-col">
				<Card.Root class="sticky top-4">
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

<style>
	.form-shell {
		display: flex;
		flex-direction: column;
		min-height: 100%;
		margin: -24px;
	}

	.state-center {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 14px;
		text-align: center;
		padding: 60px 40px;
	}

	.error-icon {
		width: 52px;
		height: 52px;
		border-radius: 12px;
		background: oklch(0.95 0.05 25);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	:global(.dark) .error-icon {
		background: oklch(0.22 0.05 25);
	}

	.error-title {
		font-size: 15px;
		font-weight: 700;
		color: var(--foreground);
		margin: 0 0 5px;
	}

	.error-msg {
		font-size: 13px;
		color: var(--muted-foreground);
		margin: 0;
	}

	.topbar {
		position: sticky;
		top: 0;
		z-index: 10;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 16px;
		border-bottom: 1px solid var(--border);
		background: var(--background);
	}

	.dirty-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: currentColor;
		margin-left: 2px;
	}

	.body {
		flex: 1;
		display: flex;
		gap: 24px;
		padding: 24px;
		justify-content: center;
	}

	.form-col {
		flex: 1;
		max-width: 48rem;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	.summary-col {
		width: 260px;
		flex-shrink: 0;
	}

	@media (max-width: 1024px) {
		.summary-col {
			display: none;
		}
	}
</style>
