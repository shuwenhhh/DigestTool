import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const runFile = promisify(execFile);
const projectRoot = new URL('../../../', import.meta.url);
const demoPath = fileURLToPath(new URL('demo.py', projectRoot));
const roles = new Set([
  'electrical_engineer',
  'supply_chain',
  'engineering_manager',
  'mechanical_engineer',
  'pm',
]);
const phases = new Set(['evt', 'dvt', 'pvt']);

const usage = 'Usage: `/digest [role] [phase]` — for example `/digest supply_chain dvt`.';

const digestCommandCallback = async ({ ack, command, respond, logger }) => {
  await ack();
  const [role = 'electrical_engineer', phase = 'dvt', ...extra] = command.text
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);

  if (extra.length || !roles.has(role) || !phases.has(phase)) {
    await respond({ response_type: 'ephemeral', text: usage });
    return;
  }

  try {
    const { stdout } = await runFile('python3', [
      demoPath,
      '--role',
      role,
      '--phase',
      phase,
    ]);
    const digest = stdout.replace(/^Loaded \d+ Slack messages\.\n\n/, '').trim();
    await respond({ response_type: 'in_channel', text: digest });
  } catch (error) {
    logger.error(error);
    await respond({
      response_type: 'ephemeral',
      text: 'Digest generation failed. Please try again after the local app restarts.',
    });
  }
};

export { digestCommandCallback };
