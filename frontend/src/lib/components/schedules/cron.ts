const FIELD =
	/^(\*|\d+(-\d+)?|[A-Za-z]{3}(-[A-Za-z]{3})?)(\/\d+)?(,(\*|\d+(-\d+)?|[A-Za-z]{3}(-[A-Za-z]{3})?)(\/\d+)?)*$/;

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

/** Why a five-field cron expression is not usable, or null when it is. */
export function cronError(expression: string): string | null {
	const fields = expression.trim().split(/\s+/).filter(Boolean);
	if (fields.length !== 5 || !fields.every((f) => FIELD.test(f))) {
		return 'Enter five fields separated by spaces, for example 0 3 * * 1.';
	}
	return null;
}

function pad(n: string): string {
	return n.padStart(2, '0');
}

/** "Every Monday at 03:00" for common patterns, null for anything else. */
export function describeCron(expression: string | null | undefined): string | null {
	if (!expression) return null;
	const fields = expression.trim().split(/\s+/);
	if (fields.length !== 5) return null;
	const [minute, hour, dom, month, dow] = fields;
	const number = /^\d+$/;
	if (month !== '*') return null;

	if (number.test(minute) && hour === '*' && dom === '*' && dow === '*') {
		return `Every hour at :${pad(minute)}`;
	}
	const step = /^\*\/(\d+)$/.exec(hour);
	if (number.test(minute) && step && dom === '*' && dow === '*') {
		return `Every ${step[1]} hours at :${pad(minute)}`;
	}
	if (!number.test(minute) || !number.test(hour)) return null;
	const time = `${pad(hour)}:${pad(minute)}`;

	if (dom === '*' && dow === '*') return `Every day at ${time}`;
	if (dom === '*' && dow === '1-5') return `Every weekday at ${time}`;
	if (dom === '*' && number.test(dow) && Number(dow) <= 7) {
		return `Every ${DAYS[Number(dow) % 7]} at ${time}`;
	}
	if (number.test(dom) && dow === '*') return `Day ${dom} of every month at ${time}`;
	return null;
}
