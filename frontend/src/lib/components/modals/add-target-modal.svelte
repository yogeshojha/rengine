<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import * as Dialog from '$lib/components/ui/dialog';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { Separator } from '$lib/components/ui/separator';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import MultiSelectCombobox from '$lib/components/multi-select-combobox.svelte';
	import TagMultiSelect from '$lib/components/tag-multi-select.svelte';
	import QuickScanFields from '$lib/components/scans/quick-scan-fields.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { toolbox } from '$lib/stores/toolbox.svelte';
	import { ORG_DOMAINS_ICON as OrgIcon, ORG_DOMAINS_TOOL } from '$lib/config/toolbox';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { TargetType, formatTargetType } from '$lib/types/target';
	import { getTargetTypeIcon } from '$lib/config/icons';
	import { ROUTES } from '$lib/config/routes';
	import { SELECT_NONE } from '$lib/constants';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import {
		quickScanPlan,
		rememberQuickScanChoice,
		type QuickScanSelection
	} from '$lib/utilities/quick-scan';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { tick, untrack } from 'svelte';

	interface Props {
		open: boolean;
		initialValue?: string;
	}

	let { open = $bindable(), initialValue = '' }: Props = $props();

	let targetInput = $state<HTMLInputElement | null>(null);
	let showDiscardConfirm = $state(false);
	let targetValue = $state('');
	let displayName = $state('');
	let isValidating = $state(false);
	let validationResult = $state<{
		valid: boolean;
		target_type: TargetType | null;
		error: string | null;
	} | null>(null);
	let isSubmitting = $state(false);

	let seedText = $state('');
	let selectedOrganizations = $state<Array<{ id: string; label: string }>>([]);
	let selectedTags = $state<Array<{ id: string; label: string; color: string }>>([]);

	let scanAfterAdd = $state(false);
	let selection = $state<QuickScanSelection | null>(null);
	let contextId = $state(SELECT_NONE);
	let scanArmed = $state(false);
	let scanPending = $state(false);

	let validateTimeout: ReturnType<typeof setTimeout>;
	let validateSeq = 0;

	let seedLines = $derived(
		seedText
			.split(/[\s,]+/)
			.map((line) => line.trim())
			.filter(Boolean)
	);

	let TypeIcon = $derived(
		validationResult?.target_type ? getTargetTypeIcon(validationResult.target_type, true) : null
	);

	function validateValue(value: string) {
		clearTimeout(validateTimeout);
		const seq = ++validateSeq;

		if (!value.trim()) {
			validationResult = null;
			isValidating = false;
			return;
		}

		isValidating = true;
		validateTimeout = setTimeout(async () => {
			try {
				const result = await targetsApi.validate({ target_value: value });
				if (seq === validateSeq) validationResult = result;
			} catch {
				if (seq === validateSeq)
					validationResult = { valid: false, target_type: null, error: 'Target not validated' };
			} finally {
				if (seq === validateSeq) isValidating = false;
			}
		}, 400);
	}

	function handleTargetInput(e: Event) {
		const value = (e.target as HTMLInputElement).value;
		targetValue = value;
		validateValue(value);
	}

	function handleSelectOrganization(item: { id: string; label: string }) {
		selectedOrganizations = [...selectedOrganizations, item];
	}

	function handleRemoveOrganization(item: { id: string; label: string }) {
		selectedOrganizations = selectedOrganizations.filter((o) => o.id !== item.id);
	}

	async function handleCreateOrganization(name: string) {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug) return;

		const newOrg = await targetsStore.createOrganization(projectSlug, name);
		if (!newOrg) {
			toast.error('Organization not created');
			return;
		}
		selectedOrganizations = [...selectedOrganizations, { id: newOrg.id, label: newOrg.name }];
		toast.success(`Organization "${name}" created`);
	}

	function handleSelectTag(item: { id: string; label: string; color: string }) {
		selectedTags = [...selectedTags, item];
	}

	function handleRemoveTag(item: { id: string; label: string; color: string }) {
		selectedTags = selectedTags.filter((t) => t.id !== item.id);
	}

	async function handleCreateTag(name: string, color: string) {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug) return;

		const newTag = await targetsStore.createTag(projectSlug, name, color);
		if (!newTag) {
			toast.error('Tag not created');
			return;
		}
		selectedTags = [...selectedTags, { id: newTag.id, label: newTag.name, color: newTag.color }];
		toast.success(`Tag "${name}" created`);
	}

	async function handleSubmit(e?: Event) {
		e?.preventDefault();

		const project = projectsStore.activeProject;
		if (!project || !canSubmit) return;

		const wantsScan = scanArmed;
		const plan = selection;
		const context = contextId;

		isSubmitting = true;

		try {
			const result = await targetsStore.createTarget({
				target_value: targetValue.trim(),
				display_name: displayName.trim() || undefined,
				project_slug: project.slug,
				organization_names: selectedOrganizations.map((o) => o.label),
				tag_names: selectedTags.map((t) => t.label)
			});

			if (!result) {
				toast.error(targetsStore.error || 'Target not added');
				return;
			}

			if (seedLines.length > 0) {
				try {
					const stored = await targetsApi.writeSeeds(result.id, seedLines);
					if (stored.rejected.length > 0) {
						toast.warning(
							`${stored.rejected.length} of ${seedLines.length} seed assets not stored. ` +
								stored.rejected[0].reason
						);
					}
				} catch {
					toast.error('Target added. Seed assets not stored');
				}
			}

			if (!wantsScan) {
				toast.success('Target added');
				resetForm();
				open = false;
				return;
			}

			const presets = engineCatalogStore.presets;
			const scans = plan
				? await scansStore.launchScans(project.id, {
						...quickScanPlan(plan, presets),
						context_id: context === SELECT_NONE ? null : context,
						target_ids: [result.id]
					})
				: null;

			resetForm();
			open = false;

			if (scans && scans.length > 0) {
				if (plan) rememberQuickScanChoice(plan, context === SELECT_NONE ? null : context, presets);
				toast.success('Target added. Scan queued');
				goto(ROUTES.scan(scans[0].id));
			} else {
				toast.error(
					scansStore.error
						? `Target added. Scan not queued. ${scansStore.error}`
						: 'Target added. Scan not queued'
				);
			}
		} catch {
			toast.error('Target not added');
		} finally {
			isSubmitting = false;
		}
	}

	function findByOrganization() {
		const value = targetValue.trim();
		resetForm();
		open = false;
		toolbox.open({ value, tool: ORG_DOMAINS_TOOL, run: value.length > 0 });
	}

	function resetForm() {
		clearTimeout(validateTimeout);
		validateSeq++;
		targetValue = '';
		displayName = '';
		seedText = '';
		isValidating = false;
		validationResult = null;
		selectedOrganizations = [];
		selectedTags = [];
	}

	let isDirty = $derived(
		targetValue.trim().length > 0 ||
			displayName.trim().length > 0 ||
			seedText.trim().length > 0 ||
			selectedOrganizations.length > 0 ||
			selectedTags.length > 0
	);

	function handleOpenChange(isOpen: boolean) {
		if (isOpen) {
			open = true;
			return;
		}
		if (isDirty) return;
		resetForm();
		open = false;
	}

	function requestClose() {
		if (isDirty) {
			showDiscardConfirm = true;
			return;
		}
		resetForm();
		open = false;
	}

	function confirmDiscard() {
		showDiscardConfirm = false;
		resetForm();
		open = false;
	}

	$effect(() => {
		const projectSlug = projectsStore.activeProject?.slug;
		if (open && projectSlug)
			untrack(() => {
				void targetsStore.fetchOrganizations(projectSlug);
				void targetsStore.fetchTags(projectSlug);
			});
	});

	let prefilled = false;
	$effect(() => {
		if (open) {
			if (initialValue && !prefilled) {
				prefilled = true;
				targetValue = initialValue;
				validateValue(initialValue);
			}
			tick().then(() => targetInput?.focus());
		} else {
			prefilled = false;
		}
	});

	let canSubmit = $derived(
		!!validationResult?.valid && !isSubmitting && !isValidating && !scanPending
	);
</script>

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content
		showCloseButton={false}
		interactOutsideBehavior={isDirty ? 'ignore' : 'close'}
		escapeKeydownBehavior={isDirty ? 'ignore' : 'close'}
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			targetInput?.focus();
		}}
		class="grid max-h-[85vh] grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)] gap-0 overflow-hidden p-0 sm:max-w-lg"
	>
		<button
			type="button"
			onclick={requestClose}
			class="ring-offset-background focus:ring-ring absolute end-4 top-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-offset-2 focus:outline-hidden"
			aria-label="Close"
		>
			<X class="size-4" />
		</button>
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>Add target</Dialog.Title>
			<Dialog.Description>Domain, IP address, CIDR range, URL or ASN.</Dialog.Description>
		</Dialog.Header>

		<form
			onsubmit={handleSubmit}
			class="grid min-h-0 grid-cols-[minmax(0,1fr)] grid-rows-[minmax(0,1fr)]"
		>
			<ScrollArea class="min-h-0">
				<div class="space-y-4 px-6 py-5">
					<div class="space-y-3">
						<Label for="target-value">Target value <span class="text-destructive">*</span></Label>
						<div class="relative">
							<Input
								id="target-value"
								type="text"
								bind:ref={targetInput}
								placeholder="example.com, 192.168.1.0/24, AS12345"
								value={targetValue}
								oninput={handleTargetInput}
								class="pr-10"
							/>
							<div class="absolute right-3 top-1/2 -translate-y-1/2">
								{#if isValidating}
									<Spinner class="h-4 w-4 text-muted-foreground" />
								{:else if validationResult?.valid}
									<CircleCheck class="h-4 w-4 text-success" />
								{:else if validationResult && !validationResult.valid}
									<CircleX class="h-4 w-4 text-destructive" />
								{/if}
							</div>
						</div>

						{#if validationResult}
							<div class="flex items-center gap-2 text-sm">
								{#if validationResult.valid && validationResult.target_type}
									<Badge variant="outline" class="gap-1.5 font-normal">
										{#if TypeIcon}
											<TypeIcon class="h-3 w-3" />
										{/if}
										{formatTargetType(validationResult.target_type)}
									</Badge>
								{:else if validationResult.error}
									<span role="alert" class="text-destructive">{validationResult.error}</span>
								{/if}
							</div>
						{/if}
					</div>

					<div class="space-y-3">
						<Label for="display-name">Display name</Label>
						<Input id="display-name" type="text" placeholder="Optional" bind:value={displayName} />
					</div>

					<div class="space-y-3">
						<Label for="target-seeds">Seed assets</Label>
						<Textarea
							id="target-seeds"
							rows={4}
							placeholder="www.example.com"
							bind:value={seedText}
							class="font-mono text-xs"
						/>
						<p class="text-2xs text-muted-foreground">
							One host name, address or URL per line. Every scan of this target starts from them.
						</p>
					</div>

					<div class="space-y-3">
						<Label>Organizations</Label>
						<MultiSelectCombobox
							items={targetsStore.organizationItems}
							selected={selectedOrganizations}
							onSelect={handleSelectOrganization}
							onRemove={handleRemoveOrganization}
							onCreate={handleCreateOrganization}
							placeholder="Search or create organizations"
							emptyText="No organizations"
						/>
					</div>

					<div class="space-y-3">
						<Label>Tags</Label>
						<TagMultiSelect
							items={targetsStore.tagItems}
							selected={selectedTags}
							onSelect={handleSelectTag}
							onRemove={handleRemoveTag}
							onCreate={handleCreateTag}
							placeholder="Search or create tags"
						/>
					</div>
				</div>
			</ScrollArea>

			<Separator />

			<QuickScanFields
				id="add-target-scan"
				title="Scan after adding"
				fallbackNote="The target is added without a scan."
				bind:enabled={scanAfterAdd}
				bind:selection
				bind:contextId
				bind:armed={scanArmed}
				bind:pending={scanPending}
				disabled={isSubmitting}
			/>

			<div class="flex flex-wrap items-center justify-end gap-2 border-t px-6 py-4">
				<Button
					type="button"
					variant="ghost"
					class="mr-auto text-muted-foreground"
					onclick={findByOrganization}
					disabled={isSubmitting}
				>
					<OrgIcon class="size-4" />
					Domains by organization
				</Button>
				<Button type="button" variant="outline" onclick={requestClose} disabled={isSubmitting}>
					Cancel
				</Button>
				<LoadingButton
					type="submit"
					loading={isSubmitting}
					loadingLabel={scanArmed ? 'Queuing' : 'Adding'}
					disabled={!canSubmit}
				>
					{scanArmed ? 'Add & scan' : 'Add target'}
				</LoadingButton>
			</div>
		</form>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	bind:open={showDiscardConfirm}
	title="Discard changes"
	description="Unsaved changes are discarded."
	onOpenChange={(o) => (showDiscardConfirm = o)}
	onConfirm={confirmDiscard}
/>
