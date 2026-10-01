import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const runFile = promisify(execFile);
const projectRoot = fileURLToPath(new URL('../../', import.meta.url));

export const generate = async ({ channel, role, phase, user, feedbackId, direction }) => {
  const args = ['-m', 'slack.bridge', '--channel', channel, '--role', role, '--phase', phase, '--user', user];
  if (feedbackId) args.push('--feedback-id', feedbackId, '--direction', direction);
  const { stdout } = await runFile('python3', args, { cwd: projectRoot, maxBuffer: 1024 * 1024 });
  return JSON.parse(stdout);
};

export const formatForSlack = (markdown) =>
  markdown
    .replace(/^#{1,2} (.+)$/gm, '*$1*')
    .replace(/\[([MS]\d+)\]\((https:\/\/[^\s)]+)\)/g, '<$2|$1>')
    .replace(/^\n{3,}/gm, '\n\n');

const feedbackButtons = (item, result) =>
  ['up', 'down'].map((direction) => ({
    type: 'button',
    action_id: `digest_feedback_${direction}`,
    text: { type: 'plain_text', text: `${direction === 'up' ? '👍 Useful' : '👎 Not relevant'} · ${item.id}` },
    value: JSON.stringify({ id: item.id, role: result.role, phase: result.phase }),
    ...(result.votes?.[item.id] === direction ? { style: direction === 'up' ? 'primary' : 'danger' } : {}),
  }));

export const digestBlocks = (result) => [
  ...(result.adjustment ? [{ type: 'context', elements: [{ type: 'mrkdwn', text: result.adjustment }] }] : []),
  { type: 'section', block_id: 'personal_digest_v2', text: { type: 'mrkdwn', text: formatForSlack(result.digest) } },
  { type: 'divider' },
  {
    type: 'context',
    elements: [
      {
        type: 'mrkdwn',
        text: `${result.tuned ? '🎛 Tuned by your feedback · ' : ''}Rate each item privately for your next digest:`,
      },
    ],
  },
  ...result.top.map((item) => ({
    type: 'actions',
    block_id: `rate_${item.id}`,
    elements: feedbackButtons(item, result),
  })),
  ...Object.keys(result.votes ?? {})
    .filter((id) => !result.top.some((item) => item.id === id))
    .slice(0, 5)
    .flatMap((id) => [
      {
        type: 'context',
        elements: [{ type: 'mrkdwn', text: `${id} is outside your Top 5. You can still change or undo its rating:` }],
      },
      { type: 'actions', block_id: `rate_${id}`, elements: feedbackButtons({ id }, result) },
    ]),
  {
    type: 'context',
    block_id: 'feedback_notice',
    elements: [{ type: 'mrkdwn', text: 'Only you can see these ratings. Tap the selected button again to undo.' }],
  },
];

export const digestPayload = (result) => ({
  text: formatForSlack(result.digest),
  blocks: digestBlocks(result),
});

export const privateDigestResponse = (result) => ({ response_type: 'ephemeral', ...digestPayload(result) });

export const updateFeedbackBlocks = (blocks, result) =>
  blocks.map((block) => {
    if (block.block_id === 'feedback_notice') {
      return { ...block, elements: [{ type: 'mrkdwn', text: result.feedback_notice }] };
    }
    if (block.type !== 'actions' || !block.block_id?.startsWith('rate_')) return block;
    const id = block.block_id.slice(5);
    return {
      ...block,
      elements: block.elements.map((button) => {
        const direction = button.action_id === 'digest_feedback_up' ? 'up' : 'down';
        const { style: _style, ...rest } = button;
        return result.votes?.[id] === direction ? { ...rest, style: direction === 'up' ? 'primary' : 'danger' } : rest;
      }),
    };
  });
