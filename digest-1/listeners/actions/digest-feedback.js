import { generate, updateFeedbackBlocks } from '../digest-service.js';

export const makeDigestFeedbackCallback =
  (generateDigest = generate) =>
  async ({ ack, action, body, respond, logger }) => {
    await ack();
    try {
      const { id, role, phase } = JSON.parse(action.value);
      const direction = action.action_id === 'digest_feedback_up' ? 'up' : 'down';
      const channel = body.channel.id;
      const result = await generateDigest({
        channel,
        role,
        phase,
        user: body.user.id,
        feedbackId: id,
        direction,
      });
      const privateCard = body.message?.blocks?.some((block) => block.block_id === 'personal_digest_v2');
      if (privateCard) {
        await respond({
          response_type: 'ephemeral',
          replace_original: true,
          text: body.message.text,
          blocks: updateFeedbackBlocks(body.message.blocks, result),
        });
      } else {
        await respond({ response_type: 'ephemeral', text: result.feedback_notice });
      }
    } catch (error) {
      logger.error(error);
      await respond({ response_type: 'ephemeral', text: error.stderr?.trim() || 'Feedback could not be saved.' });
    }
  };

export const digestFeedbackCallback = makeDigestFeedbackCallback();
