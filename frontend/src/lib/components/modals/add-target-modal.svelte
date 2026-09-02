<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import * as Dialog from '$lib/components/ui/dialog';
	import UnsavedChangesDialog from '@/components/unsaved-changes-dialog.svelte';
	import { Separator } from '$lib/components/ui/separator';
	import MultiSelectCombobox from '$lib/components/multi-select-combobox.svelte';
	import TagMultiSelect from '$lib/components/tag-multi-select.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { organizationsApi } from '$lib/api/organizations';
	import { tagsApi } from '$lib/api/tags';
	import { TargetType, formatTargetType } from '$lib/types/target';
	import { getTargetTypeIcon } from '$lib/config/icons';
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
			toast.error('Failed to create organization');
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
			toast.error('Failed to create tag');
		}
	}

	async function handleSubmit(e?: Event) {
		e?.preventDefault();

		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug || !canSubmit) return;

		isSubmitting = true;

		try {
			const result = await targetsStore.createTarget({
				target_value: targetValue.trim(),
				display_name: displayName.trim() || undefined,
				project_slug: projectSlug,
				organization_names: selectedOrganizations.map((o) => o.label),
				tag_names: selectedTags.map((t) => t.label)
			});

			if (result) {
				toast.success('Target added');
				resetForm();
				open = false;
			} else {
				toast.error(targetsStore.error || 'Failed to add target');
			}
		} catch {
			toast.error('Failed to add target');
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

	let canSubmit = $derived(validationResult?.valid && !isSubmitting && !isValidating);
</script>

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content
		showCloseButton={false}
		interactOutsideBehavior={isDirty ? 'ignore' : 'close'}
		escapeKeydownBehavior={isDirty ? 'ignore' : 'close'}
		class="sm:max-w-[500px] gap-0 p-0"
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

		<form onsubmit={handleSubmit}>
			<div class="p-6 space-y-5">
				<div class="space-y-2">
					<Label for="target-value">Target Value <span class="text-destructive">*</span></Label>
					<div class="relative">
						<Input
							id="target-value"
							type="text"
							bind:ref={targetInput}
							placeholder="e.g., example.com, 192.168.1.0/24, AS12345"
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
					<p class="text-xs text-muted-foreground">
						Descriptive label to help identify this target
					</p>
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
					<p class="text-xs text-muted-foreground">Add tags to categorize and filter targets</p>
				</div>
			</div>

			<Separator />

			<div class="flex items-center justify-end gap-2 p-4 bg-muted/30">
				<Button type="button" variant="outline" onclick={requestClose} disabled={isSubmitting}>
					Cancel
				</Button>
				<Button type="submit" disabled={!canSubmit}>
					{#if isSubmitting}
						<Spinner class="h-4 w-4 mr-2" />
						Adding…
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
	title="Discard your changes?"
	description="You have unsaved input for this target. Closing now will discard it."
	onOpenChange={(o) => (showDiscardConfirm = o)}
	onConfirm={confirmDiscard}
/>
