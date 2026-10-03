<script lang="ts">
	import { tick, untrack } from 'svelte';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Kbd } from '$lib/components/ui/kbd';
	import { SurfaceDimension } from '$lib/config/surface';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { cn } from '$lib/utils';
	import { MAX_NOTE_BODY, type Note } from '$lib/types/note';

	interface Props {
		finding: { targetId: string; scanId: string | null; fingerprint: string; label: string };
		state: string;
		autofocus?: boolean;
		onDone?: (note: Note | null) => void;
		class?: string;
	}

	let { finding, state: decided, autofocus = false, onDone, class: className }: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let text = $state('');
	let saving = $state(false);
	let failed = $state('');
	let input = $state<HTMLInputElement | null>(null);

	$effect(() => {
		if (untrack(() => autofocus)) input?.focus();
	});

	async function save() {
		const body = text.trim();
		if (!body) {
			onDone?.(null);
			return;
		}
		if (saving || !projectId) return;
		saving = true;
		failed = '';
		try {
			const note = await notes.create(projectId, {
				target_id: finding.targetId,
				scan_id: finding.scanId,
				dimension: SurfaceDimension.VULNERABILITIES,
				asset_key: finding.fingerprint,
				asset_label: finding.label,
				body,
				triage_state: decided
			});
			text = '';
			onDone?.(note);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Reason not saved.';
		} finally {
			saving = false;
		}
		if (failed) {
			await tick();
			input?.focus();
		}
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.isComposing) {
			e.preventDefault();
			void save();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			onDone?.(null);
		}
	}
</script>

<div class={cn('flex flex-col gap-1', className)}>
	<InputGroup.Root class="h-8">
		<InputGroup.Input
			bind:ref={input}
			bind:value={text}
			placeholder="Reason"
			aria-label="Reason"
			class="text-sm"
			maxlength={MAX_NOTE_BODY}
			disabled={saving}
			onkeydown={onKey}
			oninput={() => (failed = '')}
		/>
		<InputGroup.Addon align="inline-end" class="gap-1">
			<Kbd>⏎</Kbd>
			<Kbd>Esc</Kbd>
		</InputGroup.Addon>
	</InputGroup.Root>
	{#if failed}
		<p role="alert" class="text-xs text-destructive">{failed}</p>
	{/if}
</div>
