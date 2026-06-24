import { setupServer } from "msw/node";

// Empty by default — each test registers the handlers it needs with server.use().
export const server = setupServer();
