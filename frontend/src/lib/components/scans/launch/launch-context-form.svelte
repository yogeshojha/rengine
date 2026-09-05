<script lang="ts">
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import Plus from '@lucide/svelte/icons/plus';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Separator } from '$lib/components/ui/separator';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ContextSections from '$lib/components/contexts/context-sections.svelte';
	import {
		buildContextPayload,
		validateDraft,
		type ContextFormSection
	} from '$lib/components/contexts/context-form';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { DEFAULT_SCAN_CONTEXT, type ScanContextCreate } from '$lib/types/scan-context';

	interface Props {
		targetValue: string;
		onBack: () => void;
		onCreated: (id: string, name: string) => void;
	}

	let { targetValue, onBack, onCreated }: Props = $props();

	const SECTIONS: ContextFormSection[] = ['scope', 'auth', 'rate', 'runtime', 'proxy'];

	let draft = $state<ScanContextCreate>(seed());
	let touched = new SvelteSet<string>();
	let nameEl = $state<HTMLInputElement | null>(null);
	let saving = $state(false);
	let sectionsOpen = $state<Record<ContextFormSection, boolean>>({
		identity: false,
		auth: false,
		rate: false,
		scope: true,
		runtime: false,
		proxy: false
	});

	let validation = $derived(validateDraft(draft));

	function seed(): ScanContextCreate {
		const d = DEFAULT_SCAN_CONTEXT();
		d.name = targetValue ? `${targetValue} scope` : '';
		return d;
	}

	onMount(() => {
		nameEl?.focus();
		nameEl?.select();
	});

	function patch(updates: Partial<ScanContextCreate>) {
		draft = { ...draft, ...updates };
	}

	async function create() {
		const project = projectsStore.activeProject;
		if (!project || saving) return;
		const issue = validateDraft(draft);
		if (issue) {
			if (issue.section === 'identity') nameEl?.focus();
			else sectionsOpen[issue.section] = true;
			toast.error(issue.message);
			return;
		}
		saving = true;
		try {
			const created = await scanContextsStore.createContext(
				project.id,
				buildContextPayload(draft, touched)
			);
			if (created) onCreated(created.id, created.name);
			else toast.error(scanContextsStore.error ?? 'Failed to create context');
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Header class="px-6 pt-6 pb-4">
	<Button
		variant="ghost"
		size="sm"
		class="-ml-2 h-7 w-fit gap-1 px-2 text-xs text-muted-foreground"
		onclick={onBack}
	>
		<ChevronLeft class="size-3.5" /> Back
	</Button>
	<Dialog.Title>New context</Dialog.Title>
	<Dialog.Description>
		Scope, authentication and rate limits{targetValue ? ` for ${targetValue}` : ''}. Saved as a
		reusable scan context.
	</Dialog.Description>
</Dialog.Header>

<Separator />

<ScrollArea class="h-[60vh]">
	<div class="flex flex-col gap-4 p-6">
		<div class="flex flex-col gap-1.5">
			<Label for="ctx-name">Name</Label>
			<Input
				id="ctx-name"
				bind:ref={nameEl}
				value={draft.name}
				oninput={(e) => patch({ name: e.currentTarget.value })}
				placeholder="e.g. staging excluded"
				class="h-9"
			/>
		</div>
		<ContextSections
			{draft}
			bind:open={sectionsOpen}
			{touched}
			onPatch={patch}
			sections={SECTIONS}
		/>
	</div>
</ScrollArea>

<Separator />

<div class="flex items-center justify-end gap-3 bg-muted/30 px-6 py-4">
	{#if validation}
		<span class="mr-auto text-xs text-muted-foreground">{validation.message}</span>
	{/if}
	<Button variant="outline" onclick={onBack} disabled={saving}>Cancel</Button>
	<LoadingButton loading={saving} disabled={!draft.name.trim()} onclick={create} class="gap-2">
		<Plus class="size-4" />
		Create and use
	</LoadingButton>
</div>
