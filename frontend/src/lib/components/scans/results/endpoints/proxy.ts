import type { Connector, ConnectorSpec } from '$lib/types/connector';

export function proxyLabel(connector: Connector, catalog: ConnectorSpec[]): string {
	return catalog.find((c) => c.kind === connector.kind)?.title ?? connector.name;
}

// one proxy reads as "Send to Burp"; several need the connector's own name to tell them apart
export function sendLabel(connectors: Connector[], catalog: ConnectorSpec[]): string {
	if (connectors.length === 1) return `Send to ${proxyLabel(connectors[0], catalog)}`;
	return 'Send to proxy';
}
