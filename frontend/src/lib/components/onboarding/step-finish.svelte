<script lang="ts">
	import { projectsApi } from '$lib/api/projects';
	import { Input } from '$lib/components/ui/input/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import { toast } from 'svelte-sonner';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	let projectName = $state('');
	let busy = $state(false);

	let nameInvalid = $derived(projectName.trim() === '');

	$effect(() => {
		setFooter({
			onNext: handleNext,
			nextLabel: 'Finish setup',
			nextLoading: busy,
			nextLoadingLabel: 'Creating',
			nextDisabled: nameInvalid
		});
	});

	async function handleNext() {
		if (nameInvalid) {
			toast.error('Project name is required');
			return;
		}
		busy = true;
		try {
			await projectsApi.create({ name: projectName.trim() });
			next();
		} catch (e) {
			toast.error(e instanceof Error ? `Project not created. ${e.message}` : 'Project not created');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<section class="space-y-5">
		<FormField label="Name" required>
			{#snippet children({ id })}
				<Input
					{id}
					bind:value={projectName}
					placeholder="Acme Bug Bounty"
					disabled={busy}
					aria-invalid={nameInvalid && projectName.length > 0}
					class="h-9 text-sm"
				/>
			{/snippet}
		</FormField>
	</section>
</div>
