import { digestCommandCallback } from './digest-command.js';
import { seedAtlasCommandCallback } from './seed-atlas.js';

export const register = (app) => {
  app.command('/digest', digestCommandCallback);
  app.command('/seed-atlas', seedAtlasCommandCallback);
};
