<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Rocket from '@lucide/svelte/icons/rocket';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import * as Dialog from '$lib/components/ui/dialog';
	import UnsavedChangesDialog from '@/components/unsaved-changes-dialog.svelte';
	import { Separator } from '$lib/components/ui/separator';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import MultiSelectCombobox from '$lib/components/multi-select-combobox.svelte';
	import TagMultiSelect from '$lib/components/tag-multi-select.svelte';
	import QuickScanFields from '$lib/components/scans/quick-scan-fields.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { organizationsApi } from '$lib/api/organizations';
	import { tagsApi } from '$lib/api/tags';
	import { TargetType, formatTargetType } from '$lib/types/target';
	import { getTargetTypeIcon } from '$lib/config/icons';
	import { ROUTES } from '$lib/config/routes';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { SELECT_NONE } from '$lib/constants';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import {
		quickScanPlan,
		rememberQuickScanChoice,
		type QuickScanSelection
	} from '$lib/utilities/quick-scan';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { tick } from 'svelte';

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

	let selectedOrganizations = $state<Array<{ id: string; label: string }>>([]);
	let selectedTags = $state<Array<{ id: string; label: string; color: string }>>([]);

	let scanAfterAdd = $state(false);
	let selection = $state<QuickScanSelection | null>(null);
	let contextId = $state(SELECT_NONE);
	let scanArmed = $state(false);
	let scanPending = $state(false);

	let validateTimeout: ReturnType<typeof setTimeout>;

	let organizationItems = $derived(
		targetsStore.organizations.map((org) => ({
			id: org.id,
			label: org.name
		}))
	);

	let tagItems = $derived(
		targetsStore.tags.map((tag) => ({
			id: tag.id,
			label: tag.name,
			color: tag.color
		}))
	);

	let TypeIcon = $derived(
		validationResult?.target_type ? getTargetTypeIcon(validationResult.target_type, true) : null
	);

	function validateValue(value: string) {
		clearTimeout(validateTimeout);

		if (!value.trim()) {
			validationResult = null;
			return;
		}

		isValidating = true;
		validateTimeout = setTimeout(async () => {
			try {
				const result = await targetsApi.validate({ target_value: value });
				validationResult = result;
			} catch {
				validationResult = { valid: false, target_type: null, error: 'Validation failed' };
			} finally {
				isValidating = false;
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

		try {
			const newOrg = await organizationsApi.create({ name, project_slug: projectSlug });
			selectedOrganizations = [...selectedOrganizations, { id: newOrg.id, label: newOrg.name }];
			await targetsStore.refresh();
			toast.success(`Organization "${name}" created`);
		} catch {
			toast.error('Organization could not be created');
		}
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

		try {
			const newTag = await tagsApi.create({ name, color, project_slug: projectSlug });
			selectedTags = [...selectedTags, { id: newTag.id, label: newTag.name, color: newTag.color }];
			await targetsStore.refresh();
			toast.success(`Tag "${name}" created`);
		} catch {
			toast.error('Tag could not be created');
		}
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
				toast.error(targetsStore.error || 'Target could not be added');
				return;
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
				toast.success(`Target added. Scan queued against ${result.target_value}.`);
				goto(ROUTES.scan(scans[0].id));
			} else {
				toast.error(
					scansStore.error
						? `Target added, but the scan could not be queued. ${scansStore.error}`
						: 'Target added, but the scan could not be queued.'
				);
			}
		} catch {
			toast.error('Target could not be added');
		} finally {
			isSubmitting = false;
		}
	}

	function resetForm() {
		clearTimeout(validateTimeout);
		targetValue = '';
		displayName = '';
		isValidating = false;
		validationResult = null;
		selectedOrganizations = [];
		selectedTags = [];
	}

	let isDirty = $derived(
		targetValue.trim().length > 0 ||
			displayName.trim().length > 0 ||
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
		class="grid max-h-[90vh] grid-rows-[auto_auto_minmax(0,1fr)] gap-0 overflow-hidden p-0 sm:max-w-[500px]"
	>
		<button
			type="button"
			onclick={requestClose}
			class="ring-offset-background focus:ring-ring absolute end-4 top-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-offset-2 focus:outline-hidden"
			aria-label="Close"
		>
			<X class="size-4" />
		</button>
		<Dialog.Header class="p-6 pb-4">
			<Dialog.Title>Add target</Dialog.Title>
			<Dialog.Description>Domain, IP, CIDR range, URL, or ASN.</Dialog.Description>
		</Dialog.Header>

		<Separator />

		<form onsubmit={handleSubmit} class="grid min-h-0 grid-rows-[minmax(0,1fr)]">
			<ScrollArea class="min-h-0">
				<div class="space-y-5 p-6">
					<div class="space-y-2">
						<Label for="target-value">Target value <span class="text-destructive">*</span></Label>
						<div class="relative">
							<Input
								id="target-value"
								type="text"
								bind:ref={targetInput}
								placeholder="e.g. example.com, 192.168.1.0/24, AS12345"
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
									<span class="text-destructive">{validationResult.error}</span>
								{/if}
							</div>
						{/if}
					</div>

					<div class="space-y-2">
						<Label for="display-name">Display Name (Optional)</Label>
						<Input
							id="display-name"
							type="text"
							placeholder="Optional friendly name"
							bind:value={displayName}
						/>
						<p class="text-xs text-muted-foreground">Optional label for this target</p>
					</div>

					<div class="space-y-2">
						<Label>Organizations (Optional)</Label>
						<MultiSelectCombobox
							items={organizationItems}
							selected={selectedOrganizations}
							onSelect={handleSelectOrganization}
							onRemove={handleRemoveOrganization}
							onCreate={handleCreateOrganization}
							placeholder="Search or create organizations…"
							emptyText="No organizations found."
						/>
						<p class="text-xs text-muted-foreground">Group targets by organization</p>
					</div>

					<div class="space-y-2">
						<Label>Tags (Optional)</Label>
						<TagMultiSelect
							items={tagItems}
							selected={selectedTags}
							onSelect={handleSelectTag}
							onRemove={handleRemoveTag}
							onCreate={handleCreateTag}
							placeholder="Search or create tags…"
						/>
						<p class="text-xs text-muted-foreground">Tags group and filter targets</p>
					</div>
				</div>
			</ScrollArea>

			<Separator />

			<QuickScanFields
				id="add-target-scan"
				title="Scan after adding"
				description="Queues a scan as soon as the target is created."
				fallbackNote="The target will be added without a scan."
				storageKey={STORAGE_KEYS.addTargetScanAfter}
				bind:enabled={scanAfterAdd}
				bind:selection
				bind:contextId
				bind:armed={scanArmed}
				bind:pending={scanPending}
				disabled={isSubmitting}
			/>

			<Separator />

			<div class="flex items-center justify-end gap-2 p-4 bg-muted/30">
				<Button type="button" variant="outline" onclick={requestClose} disabled={isSubmitting}>
					Cancel
				</Button>
				<Button type="submit" disabled={!canSubmit}>
					{#if isSubmitting}
						<Spinner class="h-4 w-4 mr-2" />
						{scanArmed ? 'Queuing…' : 'Adding…'}
					{:else if scanArmed}
						<Rocket class="h-4 w-4 mr-2" />
						Add & scan
					{:else}
						Add target
					{/if}
				</Button>
			</div>
		</form>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	bind:open={showDiscardConfirm}
	title="Discard changes?"
	description="This target has unsaved input. Closing now discards it."
	onOpenChange={(o) => (showDiscardConfirm = o)}
	onConfirm={confirmDiscard}
/>
