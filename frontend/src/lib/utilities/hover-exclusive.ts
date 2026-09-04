let openCard: (() => void) | null = null;

export function claimHover(close: () => void) {
	if (openCard && openCard !== close) openCard();
	openCard = close;
}

export function releaseHover(close: () => void) {
	if (openCard === close) openCard = null;
}
