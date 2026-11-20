<script lang="ts">
	import { toast } from 'svelte-sonner';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import ProjectChecklist from './project-checklist.svelte';
	import { usersApi, type UserAccount } from '$lib/api/users';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { accessSummary, PROJECT_ACCESS_LABELS } from '$lib/config/users';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';

	interface Props {
		user: UserAccount | null;
		onclose: () => void;
		onsaved: (user: UserAccount) => void;
	}

	let { user, onclose, onsaved }: Props = $props();

	let selected = $state<string[]>([]);
	let canCreate = $state(false);
	let saving = $state(false);

	const projects = $derived(projectsStore.projects);
	const listed = $derived(new Set(projects.map((p) => p.id)));
	const held = $derived(selected.filter((id) => listed.has(id)));
	const before = $derived(user?.project_ids.filter((id) => listed.has(id)) ?? []);
	const unlisted = $derived(user?.project_ids.filter((id) => !listed.has(id)) ?? []);
	const projectsMoved = $derived(
		held.length !== before.length || held.some((id) => !before.includes(id))
	);
	const createMoved = $derived(!!user && canCreate !== user.can_create_projects);
	const dirty = $derived(projectsMoved || createMoved);
	const guard = new DiscardGuard(
		() => dirty,
		() => onclose()
	);

	$effect(() => {
		if (!user) return;
		selected = [...user.project_ids];
		canCreate = user.can_create_projects;
	});

	async function save() {
		if (!user || saving) return;
		if (!dirty) {
			onclose();
			return;
		}
		saving = true;
		try {
			let updated = user;
			if (projectsMoved) updated = await usersApi.setProjects(user.id, [...held, ...unlisted]);
			if (createMoved) updated = await usersApi.update(user.id, { can_create_projects: canCreate });
			onsaved(updated);
			toast.success(`Project access of ${user.username} saved`);
			onclose();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Project access not saved');
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root open={user !== null} onOpenChange={(next) => !next && !saving && guard.close()}>
	<Dialog.Content class="grid-cols-[minmax(0,1fr)] gap-0 p-0 sm:max-w-md">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{PROJECT_ACCESS_LABELS.title}</Dialog.Title>
			<Dialog.Description class="wrap-anywhere">{user?.username}</Dialog.Description>
		</Dialog.Header>
		<div class="flex flex-col gap-4 px-6 py-5">
			<div class="flex flex-col gap-2">
				<ProjectChecklist {projects} bind:selected disabled={saving} />
				{#if user && projects.length > 0}
					<p class="text-xs text-muted-foreground">
						{accessSummary(held.length, projects.length, user.username)}
					</p>
				{/if}
			</div>
			<label
				class="flex cursor-pointer items-center justify-between gap-4 rounded-lg border px-4 py-3"
				for="access-create"
			>
				<span class="text-sm font-medium">{PROJECT_ACCESS_LABELS.create}</span>
				<Switch id="access-create" bind:checked={canCreate} disabled={saving} />
			</label>
		</div>
		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" disabled={saving} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton loading={saving} loadingLabel="Saving" onclick={save}>Save</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
