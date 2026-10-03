<script lang="ts">
	import { projectsApi } from '$lib/api/projects';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
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
		<div class="flex flex-col gap-3">
			<Label for="project-name">
				Name <span class="text-destructive">*</span>
			</Label>
			<Input
				id="project-name"
				bind:value={projectName}
				placeholder="Acme Bug Bounty"
				disabled={busy}
				aria-invalid={nameInvalid && projectName.length > 0}
				class="h-9 text-sm"
			/>
		</div>
	</section>
</div>
