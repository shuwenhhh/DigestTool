import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { seedAtlasCommandCallback } from '../../listeners/commands/seed-atlas.js';

describe('/seed-atlas', () => {
  it('posts only missing seed updates', async () => {
    const posted = [];
    const responses = [];
    const client = {
      conversations: {
        history: async () => ({
          messages: [{ text: '[M001] [Electrical Engineer · Sarah]\nAlready here.' }],
        }),
      },
      chat: { postMessage: async (message) => posted.push(message) },
    };
    await seedAtlasCommandCallback({
      ack: async () => {},
      command: { channel_id: 'C123' },
      client,
      respond: async (response) => responses.push(response),
      logger: { error: () => {} },
    });
    assert.equal(posted.length, 17);
    assert.ok(posted.every((message) => !message.text.startsWith('[M001]')));
    assert.match(responses[0].text, /Seeded 17 Project Atlas updates \(1 already present\)/);
  });
});
