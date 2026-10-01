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

export const digestBlocks = (result) => [
  { type: 'section', text: { type: 'mrkdwn', text: formatForSlack(result.digest) } },
  { type: 'divider' },
  { type: 'context', elements: [{ type: 'mrkdwn', text: 'Rate a source update to tune your next digest:' }] },
  ...result.top.map((item) => ({
    type: 'actions',
    block_id: `rate_${item.id}`,
    elements: ['up', 'down'].map((direction) => ({
      type: 'button',
      action_id: `digest_feedback_${direction}`,
      text: { type: 'plain_text', text: `${direction === 'up' ? '👍 Useful' : '👎 Not relevant'} · ${item.id}` },
      value: JSON.stringify({ id: item.id, role: result.role, phase: result.phase }),
    })),
  })),
];

export const postDigest = async (client, channel, result) =>
  client.chat.postMessage({
    channel,
    text: formatForSlack(result.digest),
    blocks: digestBlocks(result),
  });
