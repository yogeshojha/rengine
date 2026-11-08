<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ProjectNameForm from './project-name-form.svelte';

	let { open = $bindable(false) }: { open: boolean } = $props();
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Create project</Dialog.Title>
		</Dialog.Header>

		<ProjectNameForm oncreated={() => (open = false)}>
			{#snippet actions({ submitting, valid })}
				<Dialog.Footer>
					<Button
						type="button"
						variant="outline"
						onclick={() => (open = false)}
						disabled={submitting}
					>
						Cancel
					</Button>
					<LoadingButton
						type="submit"
						loading={submitting}
						loadingLabel="Creating"
						disabled={!valid}
					>
						Create project
					</LoadingButton>
				</Dialog.Footer>
			{/snippet}
		</ProjectNameForm>
	</Dialog.Content>
</Dialog.Root>
