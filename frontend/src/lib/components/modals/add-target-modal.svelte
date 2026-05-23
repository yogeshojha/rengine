<script lang="ts">
	import {
		CircleCheck,
		CircleX,
		LoaderCircle,
		Globe,
		MapPin,
		Hash,
		Building2,
		Link2
	} from 'lucide-svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Separator } from '$lib/components/ui/separator';
	import MultiSelectCombobox from '$lib/components/multi-select-combobox.svelte';
	import TagMultiSelect from '$lib/components/tag-multi-select.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { organizationsApi } from '$lib/api/organizations';
	import { tagsApi } from '$lib/api/tags';
	import { TargetType, formatTargetType } from '$lib/types/target';
	import { toast } from 'svelte-sonner';

	interface Props {
		open: boolean;
	}

	let { open = $bindable() }: Props = $props();

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

	const typeIcons = {
		[TargetType.DOMAIN]: Globe,
		[TargetType.IP]: MapPin,
		[TargetType.IP_RANGE]: Hash,
		[TargetType.ASN]: Building2,
		[TargetType.URL]: Link2
	};

	let TypeIcon = $derived(
		validationResult?.target_type ? typeIcons[validationResult.target_type] : null
	);

	function handleTargetInput(e: Event) {
		const value = (e.target as HTMLInputElement).value;
		targetValue = value;

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

	// Organization handlers
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
			// Add to selected
			selectedOrganizations = [...selectedOrganizations, { id: newOrg.id, label: newOrg.name }];
			// Refresh store to include new org
			await targetsStore.refresh();
			toast.success(`Organization "${name}" created`);
		} catch (e) {
			toast.error('Failed to create organization');
		}
	}

	// Tag handlers
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
			// Add to selected
			selectedTags = [...selectedTags, { id: newTag.id, label: newTag.name, color: newTag.color }];
			// Refresh store to include new tag
			await targetsStore.refresh();
			toast.success(`Tag "${name}" created`);
		} catch (e) {
			toast.error('Failed to create tag');
		}
	}

	// Submit handler
	async function handleSubmit() {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug || !validationResult?.valid) return;

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
				toast.success('Target added successfully');
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

	function handleOpenChange(isOpen: boolean) {
		if (!isOpen) {
			resetForm();
		}
		open = isOpen;
	}

	let canSubmit = $derived(validationResult?.valid && !isSubmitting && !isValidating);
</script>

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content class="sm:max-w-[500px] gap-0 p-0">
		<Dialog.Header class="p-6 pb-4">
			<Dialog.Title>Add Target</Dialog.Title>
			<Dialog.Description>Add a target for monitoring</Dialog.Description>
		</Dialog.Header>

		<Separator />

		<div class="p-6 space-y-5">
			<!-- Target Value -->
			<div class="space-y-2">
				<Label for="target-value">Target Value <span class="text-destructive">*</span></Label>
				<div class="relative">
					<Input
						id="target-value"
						type="text"
						placeholder="e.g., example.com, 192.168.1.0/24, AS12345"
						value={targetValue}
						oninput={handleTargetInput}
						class="pr-10"
					/>
					<div class="absolute right-3 top-1/2 -translate-y-1/2">
						{#if isValidating}
							<LoaderCircle class="h-4 w-4 animate-spin text-muted-foreground" />
						{:else if validationResult?.valid}
							<CircleCheck class="h-4 w-4 text-green-500" />
						{:else if validationResult && !validationResult.valid}
							<CircleX class="h-4 w-4 text-destructive" />
						{/if}
					</div>
				</div>

				<!-- Validation Result -->
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

			<!-- Display Name -->
			<div class="space-y-2">
				<Label for="display-name">Display Name (Optional)</Label>
				<Input
					id="display-name"
					type="text"
					placeholder="Optional friendly name"
					bind:value={displayName}
				/>
				<p class="text-xs text-muted-foreground">Descriptive label to help identify this target</p>
			</div>

			<!-- Organizations -->
			<div class="space-y-2">
				<Label>Organizations (Optional)</Label>
				<MultiSelectCombobox
					items={organizationItems}
					selected={selectedOrganizations}
					onSelect={handleSelectOrganization}
					onRemove={handleRemoveOrganization}
					onCreate={handleCreateOrganization}
					placeholder="Search or create organizations..."
					emptyText="No organizations found."
				/>
				<p class="text-xs text-muted-foreground">Group targets by organization</p>
			</div>

			<!-- Tags -->
			<div class="space-y-2">
				<Label>Tags (Optional)</Label>
				<TagMultiSelect
					items={tagItems}
					selected={selectedTags}
					onSelect={handleSelectTag}
					onRemove={handleRemoveTag}
					onCreate={handleCreateTag}
					placeholder="Search or create tags..."
				/>
				<p class="text-xs text-muted-foreground">Add tags to categorize and filter targets</p>
			</div>
		</div>

		<Separator />

		<div class="flex items-center justify-end gap-2 p-4 bg-muted/30">
			<Button variant="outline" onclick={() => (open = false)} disabled={isSubmitting}>
				Cancel
			</Button>
			<Button onclick={handleSubmit} disabled={!canSubmit}>
				{#if isSubmitting}
					<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />
					Adding...
				{:else}
					Add Target
				{/if}
			</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>
