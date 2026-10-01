import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { digestBlocks, formatForSlack } from '../../listeners/digest-service.js';

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
  });
});
