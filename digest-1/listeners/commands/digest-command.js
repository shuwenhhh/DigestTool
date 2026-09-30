import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const runFile = promisify(execFile);
const projectRoot = new URL('../../../', import.meta.url);
const demoPath = fileURLToPath(new URL('demo.py', projectRoot));
const roleAliases = new Map([
  ['electrical_engineer', 'electrical_engineer'],
  ['electrical engineer', 'electrical_engineer'],
  ['supply_chain', 'supply_chain'],
  ['supply chain', 'supply_chain'],
  ['engineering_manager', 'engineering_manager'],
  ['engineering manager', 'engineering_manager'],
  ['mechanical_engineer', 'mechanical_engineer'],
  ['mechanical engineer', 'mechanical_engineer'],
  ['pm', 'pm'],
]);
const phases = new Set(['evt', 'dvt', 'pvt']);

const usage = 'Usage: `/digest [role] [phase]` — for example `/digest supply_chain dvt` or `/digest Electrical Engineer`.';

const parseProfile = (text) => {
  const words = text
    .replaceAll('`', '')
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  let phase = 'dvt';
  if (phases.has(words.at(-1))) phase = words.pop();
  const roleInput = words.join(' ') || 'electrical_engineer';
  return { role: roleAliases.get(roleInput), phase };
};

const digestCommandCallback = async ({ ack, command, respond, logger }) => {
  await ack();
  const { role, phase } = parseProfile(command.text);

  if (!role) {
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
      '--slack-channel',
      command.channel_id,
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
