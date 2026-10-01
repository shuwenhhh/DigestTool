import assert from 'node:assert/strict';
import { it } from 'node:test';
import { makeDigestFeedbackCallback } from '../../listeners/actions/digest-feedback.js';
import { digestBlocks } from '../../listeners/digest-service.js';

it('keeps feedback private and updates the same ephemeral digest', async () => {
  const result = {
    digest: '# Digest\n- Sensor noise [M007]',
    role: 'electrical_engineer',
    phase: 'dvt',
    top: [{ id: 'M007' }],
    votes: { M007: 'down' },
    feedback_notice: 'Saved privately',
  };
  const calls = [];
  const handler = makeDigestFeedbackCallback(async (args) => {
    calls.push({ generate: args });
    return result;
  });
  await handler({
    ack: async () => calls.push({ ack: true }),
    action: {
      action_id: 'digest_feedback_down',
      value: JSON.stringify({ id: 'M007', role: result.role, phase: result.phase }),
    },
    body: {
      channel: { id: 'C123' },
      user: { id: 'U1' },
      message: { text: 'Digest', blocks: digestBlocks({ ...result, votes: {} }) },
    },
    respond: async (payload) => calls.push({ respond: payload }),
    logger: { error: () => {} },
  });
  assert.equal(calls[0].ack, true);
  assert.deepEqual(calls[1].generate, {
    channel: 'C123',
    role: result.role,
    phase: result.phase,
    user: 'U1',
    feedbackId: 'M007',
    direction: 'down',
  });
  const response = calls[2].respond;
  assert.equal(response.response_type, 'ephemeral');
  assert.equal(response.replace_original, true);
  assert.equal(response.blocks.find((block) => block.block_id === 'rate_M007').elements[1].style, 'danger');
});
