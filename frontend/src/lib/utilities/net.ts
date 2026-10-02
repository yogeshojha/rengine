// mirrors shared/utils/net.py
export function bracketed(host: string): string {
	return host.includes(':') && !host.startsWith('[') ? `[${host}]` : host;
}

export function hostPort(host: string, port: number | string): string {
	return `${bracketed(host)}:${port}`;
}

export function splitHostPort(authority: string): [string, string | null] {
	const value = authority.trim();
	if (value.startsWith('[')) {
		const close = value.indexOf(']');
		const rest = close === -1 ? '' : value.slice(close + 1);
		const port = rest.startsWith(':') ? rest.slice(1) : '';
		return [value.slice(1, close === -1 ? undefined : close), port || null];
	}
	if (value.split(':').length === 2) {
		const [host, port] = value.split(':');
		return [host, port || null];
	}
	return [value, null];
}
