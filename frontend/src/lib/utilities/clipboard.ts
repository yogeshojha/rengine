function fallbackCopy(text: string): boolean {
	const active = document.activeElement;
	const host = active?.closest('[role="dialog"], [role="alertdialog"]') ?? document.body;
	const ta = document.createElement('textarea');
	ta.value = text;
	ta.setAttribute('readonly', '');
	ta.style.position = 'fixed';
	ta.style.top = '0';
	ta.style.left = '0';
	ta.style.opacity = '0';
	ta.style.pointerEvents = 'none';
	host.appendChild(ta);
	try {
		ta.focus({ preventScroll: true });
		ta.select();
		ta.setSelectionRange(0, text.length);
		return document.execCommand('copy');
	} catch {
		return false;
	} finally {
		ta.remove();
		if (active instanceof HTMLElement) active.focus({ preventScroll: true });
	}
}

export async function writeClipboard(text: string): Promise<boolean> {
	if (navigator.clipboard && window.isSecureContext) {
		try {
			await navigator.clipboard.writeText(text);
			return true;
		} catch {
			/* empty */
		}
	}
	return fallbackCopy(text);
}
