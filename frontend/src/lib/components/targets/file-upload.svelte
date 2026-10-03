<script lang="ts">
	import Upload from '@lucide/svelte/icons/upload';
	import FileText from '@lucide/svelte/icons/file-text';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import * as Tabs from '$lib/components/ui/tabs';
	import { cn } from '$lib/utils';
	import { formatBytes } from '$lib/utilities/format';

	interface Props {
		accept?: string;
		file?: File | null;
		textValue?: string;
		onFileSelect: (file: File) => void;
		onFileRemove: () => void;
		onTextChange?: (text: string) => void;
		placeholder?: string;
		mode?: 'file' | 'text';
		showTextInput?: boolean;
	}

	let {
		accept = '.csv,.json,.txt',
		file = null,
		textValue = '',
		onFileSelect,
		onFileRemove,
		onTextChange,
		placeholder = 'Enter data',
		mode = $bindable('text'),
		showTextInput = true
	}: Props = $props();

	let isDragging = $state(false);
	let fileInputRef = $state<HTMLInputElement | undefined>(undefined);

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}

	function handleDragLeave() {
		isDragging = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;

		const droppedFile = e.dataTransfer?.files[0];
		if (droppedFile) {
			onFileSelect(droppedFile);
		}
	}

	function handleFileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		const selectedFile = input.files?.[0];
		if (selectedFile) {
			onFileSelect(selectedFile);
		}
	}

	function handleRemoveFile() {
		if (fileInputRef) {
			fileInputRef.value = '';
		}
		onFileRemove();
	}

	function handleClick() {
		fileInputRef?.click();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			fileInputRef?.click();
		}
	}
</script>

{#snippet dropzone()}
	<div
		role="button"
		tabindex="0"
		class={cn(
			'relative border-2 border-dashed rounded-lg p-8 transition-colors cursor-pointer min-h-[300px] flex items-center justify-center',
			'hover:border-primary/50 hover:bg-accent/50',
			isDragging && 'border-primary bg-accent'
		)}
		ondragover={handleDragOver}
		ondragleave={handleDragLeave}
		ondrop={handleDrop}
		onclick={handleClick}
		onkeydown={handleKeydown}
	>
		<input
			bind:this={fileInputRef}
			type="file"
			{accept}
			onchange={handleFileInput}
			class="hidden"
		/>

		<div class="flex flex-col items-center gap-3 text-center">
			<div class="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
				<Upload class="h-6 w-6 text-primary" />
			</div>

			<div class="space-y-1">
				<p class="text-sm font-medium">
					Drop a file here, or <span class="text-primary">browse</span>
				</p>
				<p class="text-xs text-muted-foreground">
					{accept.replace(/\./g, '').replace(/,/g, ', ').toUpperCase()}
				</p>
			</div>
		</div>
	</div>
{/snippet}

{#snippet selected(f: File)}
	<div class="flex items-center gap-3 p-4 rounded-lg border bg-accent/30">
		<div class="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
			<FileText class="h-5 w-5 text-primary" />
		</div>

		<div class="flex-1 min-w-0">
			<p class="text-sm font-medium truncate">{f.name}</p>
			<p class="text-xs text-muted-foreground">
				{formatBytes(f.size)}
			</p>
		</div>

		<Button
			variant="ghost"
			size="icon-sm"
			class="shrink-0"
			aria-label="Remove file"
			onclick={handleRemoveFile}
		>
			<X class="h-4 w-4" />
		</Button>
	</div>
{/snippet}

{#if showTextInput}
	<Tabs.Root bind:value={mode} class="w-full">
		<Tabs.List class="grid w-full grid-cols-2">
			<Tabs.Trigger value="text">Text input</Tabs.Trigger>
			<Tabs.Trigger value="file">File upload</Tabs.Trigger>
		</Tabs.List>

		<Tabs.Content value="text" class="mt-3">
			<Textarea
				{placeholder}
				value={textValue}
				oninput={(e) => onTextChange?.((e.target as HTMLTextAreaElement).value)}
				class="font-mono text-sm min-h-[300px]"
			/>
		</Tabs.Content>

		<Tabs.Content value="file" class="mt-3">
			{#if file}
				{@render selected(file)}
			{:else}
				{@render dropzone()}
			{/if}
		</Tabs.Content>
	</Tabs.Root>
{:else if file}
	{@render selected(file)}
{:else}
	{@render dropzone()}
{/if}
