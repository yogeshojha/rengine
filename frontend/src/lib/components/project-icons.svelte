<script lang="ts">
	import type { Project } from '$lib/types/project';
	import FolderIcon from '@lucide/svelte/icons/folder';
	import BoxIcon from '@lucide/svelte/icons/box';
	import TargetIcon from '@lucide/svelte/icons/target';
	import ShieldIcon from '@lucide/svelte/icons/shield';
	import GlobeIcon from '@lucide/svelte/icons/globe';
	import ServerIcon from '@lucide/svelte/icons/server';
	import CodeIcon from '@lucide/svelte/icons/code';
	import BugIcon from '@lucide/svelte/icons/bug';
	import NetworkIcon from '@lucide/svelte/icons/network';
	import ScanIcon from '@lucide/svelte/icons/scan';

	let { project, class: className = 'size-4' }: { project: Project; class?: string } = $props();

	const icons = [
		FolderIcon, // Default icon
		TargetIcon,
		ShieldIcon,
		GlobeIcon,
		ServerIcon,
		CodeIcon,
		BugIcon,
		BoxIcon,
		NetworkIcon,
		ScanIcon
	];

	function hashProjectName(str: string): number {
		let hash = 0;
		for (let i = 0; i < str.length; i++) {
			hash = str.charCodeAt(i) + ((hash << 5) - hash);
		}
		return Math.abs(hash);
	}

	let IconComponent = $derived(icons[hashProjectName(project.id) % icons.length] || FolderIcon);
</script>

<IconComponent class={className} />
