import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const projectRoot = new URL('../../../', import.meta.url);
const messagesPath = fileURLToPath(new URL('data/mock_messages.json', projectRoot));

const existingSeedIds = async (client, channel) => {
  const ids = new Set();
  let cursor;
  do {
    const result = await client.conversations.history({ channel, limit: 200, cursor });
    for (const message of result.messages ?? []) {
      const match = /^\[(M\d{3})\] \[/.exec(message.text ?? '');
      if (match) ids.add(match[1]);
    }
    cursor = result.response_metadata?.next_cursor || undefined;
  } while (cursor && ids.size < 18);
  return ids;
};

const seedAtlasCommandCallback = async ({ ack, command, client, respond, logger }) => {
  await ack();
  try {
    const messages = JSON.parse(await readFile(messagesPath, 'utf8'));
    const existing = await existingSeedIds(client, command.channel_id);
    let posted = 0;
    for (const message of messages) {
      if (existing.has(message.id)) continue;
      await client.chat.postMessage({
        channel: command.channel_id,
        text: `[${message.id}] [${message.role} · ${message.author}]\n${message.text}`,
      });
      posted += 1;
    }
    await respond({
      response_type: 'ephemeral',
      text: `Seeded ${posted} Project Atlas updates (${messages.length - posted} already present). Now run \`/digest\`.`,
    });
  } catch (error) {
    logger.error(error);
    await respond({
      response_type: 'ephemeral',
      text: 'Could not seed Project Atlas messages. Please try again.',
    });
  }
};

export { seedAtlasCommandCallback };
