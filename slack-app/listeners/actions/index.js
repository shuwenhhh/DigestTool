import { digestFeedbackCallback } from './digest-feedback.js';
import { sampleActionCallback } from './sample-action.js';

export const register = (app) => {
  app.action('sample_action_id', sampleActionCallback);
  app.action('digest_feedback_up', digestFeedbackCallback);
  app.action('digest_feedback_down', digestFeedbackCallback);
};
