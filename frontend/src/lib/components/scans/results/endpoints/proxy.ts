import { toast } from 'svelte-sonner';
import { connectorsApi } from '$lib/api/connectors';
import type { Connector, ConnectorSpec, HandoffRequest } from '$lib/types/connector';

export function proxyLabel(connector: Connector, catalog: ConnectorSpec[]): string {
	return catalog.find((c) => c.kind === connector.kind)?.title ?? connector.name;
}

export function sendLabel(connectors: Connector[], catalog: ConnectorSpec[]): string {
	if (connectors.length === 1) return `Send to ${proxyLabel(connectors[0], catalog)}`;
	return 'Send to proxy';
}

interface HandoffCall {
	connectorId: string;
	projectId: string;
	scanId?: string | null;
	body: HandoffRequest;
	connectors: Connector[];
	catalog: ConnectorSpec[];
}

/** Queues the rows for the proxy and reports what was queued. */
export async function handoffToProxy(call: HandoffCall): Promise<boolean> {
	const connector = call.connectors.find((c) => c.id === call.connectorId);
	const proxy = connector ? proxyLabel(connector, call.catalog) : 'the proxy';
	try {
		const res = await connectorsApi.handoff(
			call.connectorId,
			call.projectId,
			call.body,
			call.scanId
		);
		const noun = res.queued === 1 ? 'request' : 'requests';
		const skipped = res.skipped
			? ` ${res.skipped.toLocaleString()} without an HTTP request skipped.`
			: '';
		toast.success(
			`${res.queued.toLocaleString()} ${noun} sent to ${res.tool} in ${proxy}.${skipped}`
		);
		return true;
	} catch (e) {
		toast.error(e instanceof Error ? e.message : 'Requests not sent.');
		return false;
	}
}
