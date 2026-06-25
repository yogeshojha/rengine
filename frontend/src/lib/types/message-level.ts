export const MESSAGE_LEVELS = ['info', 'success', 'warning', 'error'] as const;

export type MessageLevel = (typeof MESSAGE_LEVELS)[number];
