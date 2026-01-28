<script lang="ts">
	import { targetsApi } from '$lib/api/targets';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { TargetType, formatTargetType, getTargetTypeColor } from '$lib/types/target';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import { Loader2, CheckCircle2, AlertCircle, X } from 'lucide-svelte';
	import { toast } from 'svelte-sonner';

	interface Props {
		open: boolean;
	}

	let { open = $bindable(false) }: Props = $props();

	let targetValue = $state('');
	let displayName = $state('');
	let organizationInput = $state('');
	let tagInput = $state('');
	let selectedOrganizations = $state<string[]>([]);
	let selectedTags = $state<string[]>([]);
	let isValidating = $state(false);
	let isSubmitting = $state(false);
	let validationResult = $state<{
		valid: boolean;
		type: TargetType | null;
		error: string | null;
	} | null>(null);

	let debounceTimer: number | undefined;

	function resetForm() {
		targetValue = '';
		displayName = '';
		organizationInput = '';
		tagInput = '';
		selectedOrganizations = [];
		selectedTags = [];
		validationResult = null;
	}

	async function validateTarget(value: string) {
		if (!value.trim()) {
			validationResult = null;
			return;
		}

		isValidating = true;
		try {
			const result = await targetsApi.validate({ target_value: value });
			validationResult = result;
		} catch (error) {
			validationResult = {
				valid: false,
				type: null,
				error: 'Failed to validate target'
			};
		} finally {
			isValidating = false;
		}
	}

	function handleTargetValueChange() {
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			validateTarget(targetValue);
		}, 500) as unknown as number;
	}

	function addOrganization() {
		if (organizationInput.trim() && !selectedOrganizations.includes(organizationInput.trim())) {
			selectedOrganizations = [...selectedOrganizations, organizationInput.trim()];
			organizationInput = '';
		}
	}

	function removeOrganization(org: string) {
		selectedOrganizations = selectedOrganizations.filter((o) => o !== org);
	}

	function addTag() {
		if (tagInput.trim() && !selectedTags.includes(tagInput.trim())) {
			selectedTags = [...selectedTags, tagInput.trim()];
			tagInput = '';
		}
	}

	function removeTag(tag: string) {
		selectedTags = selectedTags.filter((t) => t !== tag);
	}

	async function handleSubmit() {
		const activeProject = projectsStore.activeProject;
		if (!activeProject) {
			toast.error('No active project selected');
			return;
		}

		if (!validationResult?.valid) {
			toast.error('Please enter a valid target');
			return;
		}

		isSubmitting = true;

		const result = await targetsStore.createTarget({
			target_value: targetValue,
			display_name: displayName || undefined,
			project_slug: activeProject.slug,
			organization_names: selectedOrganizations,
			tag_names: selectedTags
		});

		isSubmitting = false;

		if (result) {
			toast.success('Target added successfully');
			open = false;
			resetForm();
		} else {
			toast.error(targetsStore.error || 'Failed to add target');
		}
	}

	function handleOpenChange(newOpen: boolean) {
		open = newOpen;
		if (!newOpen) {
			resetForm();
		}
	}
</script>

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content class="sm:max-w-[600px]">
		<Dialog.Header>
			<Dialog.Title>Add New Target</Dialog.Title>
			<Dialog.Description>
				Add a new target to your attack surface. The target will be automatically validated.
			</Dialog.Description>
		</Dialog.Header>

		<div class="space-y-6 py-4">
			<!-- Target Value Input -->
			<div class="space-y-2">
				<Label for="target-value">Target Value *</Label>
				<div class="relative">
					<Input
						id="target-value"
						type="text"
						placeholder="example.com, 192.168.1.1, AS15169, https://..."
						bind:value={targetValue}
						oninput={handleTargetValueChange}
						class={validationResult?.valid === false ? 'border-destructive' : ''}
					/>
					{#if isValidating}
						<div class="absolute right-3 top-1/2 -translate-y-1/2">
							<Loader2 class="h-4 w-4 animate-spin text-muted-foreground" />
						</div>
					{:else if validationResult?.valid}
						<div class="absolute right-3 top-1/2 -translate-y-1/2">
							<CheckCircle2 class="h-4 w-4 text-green-600" />
						</div>
					{:else if validationResult?.valid === false}
						<div class="absolute right-3 top-1/2 -translate-y-1/2">
							<AlertCircle class="h-4 w-4 text-destructive" />
						</div>
					{/if}
				</div>

				{#if validationResult?.valid && validationResult.type}
					<div class="flex items-center gap-2 mt-2">
						<span class="text-sm text-muted-foreground">Detected type:</span>
						<Badge class={getTargetTypeColor(validationResult.type) + ' border'}>
							{formatTargetType(validationResult.type)}
						</Badge>
					</div>
				{:else if validationResult?.error}
					<p class="text-sm text-destructive mt-1">{validationResult.error}</p>
				{/if}
			</div>

			<!-- Display Name Input -->
			<div class="space-y-2">
				<Label for="display-name">Display Name (Optional)</Label>
				<Input
					id="display-name"
					type="text"
					placeholder="Friendly name for this target"
					bind:value={displayName}
				/>
			</div>

			<!-- Organizations -->
			<div class="space-y-2">
				<Label for="organizations">Organizations (Optional)</Label>
				<div class="flex gap-2">
					<Input
						id="organizations"
						type="text"
						placeholder="Enter organization name"
						bind:value={organizationInput}
						onkeydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								addOrganization();
							}
						}}
					/>
					<Button type="button" variant="outline" onclick={addOrganization}>Add</Button>
				</div>
				{#if selectedOrganizations.length > 0}
					<div class="flex flex-wrap gap-2 mt-2">
						{#each selectedOrganizations as org}
							<Badge variant="secondary" class="gap-1">
								{org}
								<button
									type="button"
									onclick={() => removeOrganization(org)}
									class="ml-1 hover:bg-muted rounded-full p-0.5"
								>
									<X class="h-3 w-3" />
								</button>
							</Badge>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Tags -->
			<div class="space-y-2">
				<Label for="tags">Tags (Optional)</Label>
				<div class="flex gap-2">
					<Input
						id="tags"
						type="text"
						placeholder="Enter tag name"
						bind:value={tagInput}
						onkeydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								addTag();
							}
						}}
					/>
					<Button type="button" variant="outline" onclick={addTag}>Add</Button>
				</div>
				{#if selectedTags.length > 0}
					<div class="flex flex-wrap gap-2 mt-2">
						{#each selectedTags as tag}
							<Badge variant="outline" class="gap-1">
								{tag}
								<button
									type="button"
									onclick={() => removeTag(tag)}
									class="ml-1 hover:bg-muted rounded-full p-0.5"
								>
									<X class="h-3 w-3" />
								</button>
							</Badge>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<Dialog.Footer>
			<Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
			<Button
				onclick={handleSubmit}
				disabled={!validationResult?.valid || isSubmitting}
			>
				{#if isSubmitting}
					<Loader2 class="h-4 w-4 mr-2 animate-spin" />
					Adding...
				{:else}
					Add Target
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
