const LOCAL_ORIGIN = 'http://local.invalid';

export const isExternalHref = (href: string) => /^https?:\/\//i.test(href);

const isLocalPath = (href: string) => {
	if (!href.startsWith('/')) return false;
	try {
		return new URL(href, LOCAL_ORIGIN).origin === LOCAL_ORIGIN;
	} catch {
		return false;
	}
};

/** An http or https URL, else undefined. */
export function externalHref(value: string | null | undefined): string | undefined {
	return value && isExternalHref(value) ? value : undefined;
}

/** An http or https URL or a same-origin path, else undefined. */
export function safeHref(value: string | null | undefined): string | undefined {
	return value && (isExternalHref(value) || isLocalPath(value)) ? value : undefined;
}

/** A same-origin path, else undefined. */
export function localPath(value: string | null | undefined): string | undefined {
	return value && isLocalPath(value) ? value : undefined;
}

export function openExternal(value: string | null | undefined): void {
	const href = externalHref(value);
	if (href) window.open(href, '_blank', 'noopener,noreferrer');
}
