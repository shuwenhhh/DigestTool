import { generate, postDigest } from '../digest-service.js';

export const digestFeedbackCallback = async ({ ack, action, body, client, respond, logger }) => {
  await ack();
  try {
    const { id, role, phase } = JSON.parse(action.value);
    const direction = action.action_id === 'digest_feedback_up' ? 'up' : 'down';
    const channel = body.channel.id;
    const result = await generate({
      channel,
      role,
      phase,
      user: body.user.id,
      feedbackId: id,
      direction,
    });
    await postDigest(client, channel, result);
    await respond({
      response_type: 'ephemeral',
      text: `${direction === 'up' ? '👍' : '👎'} ${id}: #${result.movement.before} → #${result.movement.after}. Your preference was saved.`,
    });
  } catch (error) {
    logger.error(error);
    await respond({ response_type: 'ephemeral', text: error.stderr?.trim() || 'Feedback could not be saved.' });
  }
};
