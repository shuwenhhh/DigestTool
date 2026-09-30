import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const projectRoot = new URL('../../../', import.meta.url);
const messagesPath = fileURLToPath(new URL('data/mock_messages.json', projectRoot));

const seedAtlasCommandCallback = async ({ ack, command, client, respond, logger }) => {
  await ack();
  try {
    const messages = JSON.parse(await readFile(messagesPath, 'utf8'));
    for (const message of messages) {
      await client.chat.postMessage({
        channel: command.channel_id,
        text: `[${message.id}] [${message.role} · ${message.author}]\n${message.text}`,
      });
    }
    await respond({
      response_type: 'ephemeral',
      text: `Seeded ${messages.length} Project Atlas updates. Now run \`/digest\`.`,
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
