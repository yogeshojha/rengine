<script lang="ts">
	import { Label } from '$lib/components/ui/label';
	import * as Select from '$lib/components/ui/select';
	import type { ScanContextRead, ScanContextCreate, HttpProtocol } from '$lib/types/scan-context';

	type CtxLike = ScanContextRead | ScanContextCreate;

	interface Props {
		context: CtxLike;
		onChange: (updates: Partial<CtxLike>) => void;
	}

	let { context, onChange }: Props = $props();

	const PROTOCOL_OPTS: { value: HttpProtocol; label: string }[] = [
		{ value: 'both', label: 'Both' },
		{ value: 'https_only', label: 'HTTPS only' },
		{ value: 'http_only', label: 'HTTP only' }
	];

	const REDIRECT_OPTS = [
		{ value: 'null', label: 'Engine default' },
		{ value: 'true', label: 'Always follow' },
		{ value: 'false', label: 'Never follow' }
	];

	let redirectValue = $derived(
		context.follow_redirects_override == null ? 'null' : String(context.follow_redirects_override)
	);

	function setProtocol(v: string | undefined) {
		onChange({ http_protocol: (v ?? 'both') as HttpProtocol });
	}

	function setRedirect(v: string | undefined) {
		const next = v === 'true' ? true : v === 'false' ? false : null;
		onChange({ follow_redirects_override: next });
	}
</script>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
	<div class="space-y-1.5">
		<Label class="text-xs">HTTP protocol</Label>
		<Select.Root type="single" value={context.http_protocol} onValueChange={setProtocol}>
			<Select.Trigger class="h-9 w-full text-sm">
				{PROTOCOL_OPTS.find((o) => o.value === context.http_protocol)?.label ?? 'Both'}
			</Select.Trigger>
			<Select.Content>
				{#each PROTOCOL_OPTS as opt (opt.value)}
					<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>

	<div class="space-y-1.5">
		<Label class="text-xs">Follow redirects</Label>
		<Select.Root type="single" value={redirectValue} onValueChange={setRedirect}>
			<Select.Trigger class="h-9 w-full text-sm">
				{REDIRECT_OPTS.find((o) => o.value === redirectValue)?.label ?? 'Engine default'}
			</Select.Trigger>
			<Select.Content>
				{#each REDIRECT_OPTS as opt (opt.value)}
					<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>
</div>
