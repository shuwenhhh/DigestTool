import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  digestBlocks,
  formatForSlack,
  privateDigestResponse,
  updateFeedbackBlocks,
} from '../../listeners/digest-service.js';

describe('digest feedback blocks', () => {
  it('provides two actions for every cited Top-5 item', () => {
    const result = {
      digest: '# EverCurrent Daily Digest\n- Update [M001]',
      role: 'pm',
      phase: 'pvt',
      top: [{ id: 'M001' }, { id: 'M002' }],
    };
    const blocks = digestBlocks(result);
    const actions = blocks.filter((block) => block.type === 'actions');
    assert.equal(actions.length, 2);
    assert.deepEqual(
      actions[0].elements.map((item) => item.action_id),
      ['digest_feedback_up', 'digest_feedback_down'],
    );
    assert.deepEqual(JSON.parse(actions[0].elements[0].value), {
      id: 'M001',
      role: 'pm',
      phase: 'pvt',
    });
    assert.equal(formatForSlack('# Heading\n## Section'), '*Heading*\n*Section*');
    assert.equal(
      formatForSlack('- Update [M001](https://app.slack.com/archives/C123/p1760000000000100)'),
      '- Update <https://app.slack.com/archives/C123/p1760000000000100|M001>',
    );
    assert.equal(privateDigestResponse(result).response_type, 'ephemeral');
    assert.equal(blocks[0].block_id, 'personal_digest_v2');
  });

  it('updates only the private button state and supports undo', () => {
    const result = {
      digest: '# Digest\n- Update [M007]',
      role: 'electrical_engineer',
      phase: 'dvt',
      top: [{ id: 'M007' }],
    };
    const original = digestBlocks(result);
    const selected = updateFeedbackBlocks(original, {
      votes: { M007: 'down' },
      feedback_notice: 'Saved privately',
    });
    const actions = selected.find((block) => block.block_id === 'rate_M007');
    assert.equal(actions.elements[1].style, 'danger');
    assert.equal(actions.elements[0].style, undefined);
    assert.equal(selected.find((block) => block.block_id === 'feedback_notice').elements[0].text, 'Saved privately');
    const undone = updateFeedbackBlocks(selected, { votes: {}, feedback_notice: 'Undone' });
    assert.equal(undone.find((block) => block.block_id === 'rate_M007').elements[1].style, undefined);
  });

  it('keeps a hidden rated item available for undo on the next digest', () => {
    const blocks = digestBlocks({
      digest: '# Digest',
      role: 'electrical_engineer',
      phase: 'dvt',
      top: [{ id: 'M001' }],
      votes: { M007: 'down' },
      tuned: true,
    });
    const hidden = blocks.find((block) => block.block_id === 'rate_M007');
    assert.equal(hidden.elements[1].style, 'danger');
  });
});
