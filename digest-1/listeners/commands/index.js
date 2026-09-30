import { digestCommandCallback } from './digest-command.js';

export const register = (app) => {
  app.command('/digest', digestCommandCallback);
};
