import { render, waitFor } from '@testing-library/react';
import { ServiceWorkerRegister } from '@/components/ServiceWorkerRegister';

describe('ServiceWorkerRegister', () => {
  const originalEnv = process.env.NODE_ENV;
  let register: jest.Mock;
  let unregister: jest.Mock;
  let getRegistrations: jest.Mock;

  beforeEach(() => {
    register = jest.fn().mockResolvedValue(undefined);
    unregister = jest.fn().mockResolvedValue(true);
    getRegistrations = jest.fn().mockResolvedValue([{ unregister }]);
    Object.defineProperty(navigator, 'serviceWorker', {
      configurable: true,
      value: { register, getRegistrations },
    });
  });

  afterEach(() => {
    Object.defineProperty(process.env, 'NODE_ENV', { configurable: true, value: originalEnv });
    jest.clearAllMocks();
  });

  function setEnv(value: string) {
    Object.defineProperty(process.env, 'NODE_ENV', { configurable: true, value });
  }

  it('registers the worker in production, where offline support is wanted', async () => {
    setEnv('production');
    render(<ServiceWorkerRegister />);
    await waitFor(() => expect(register).toHaveBeenCalledWith('/sw.js'));
  });

  it('does not register in development', async () => {
    // sw.js serves /_next/static stale-while-revalidate; in dev that pins the app
    // to a previous build's JavaScript and code changes never appear.
    setEnv('development');
    render(<ServiceWorkerRegister />);
    await waitFor(() => expect(getRegistrations).toHaveBeenCalled());
    expect(register).not.toHaveBeenCalled();
  });

  it('unregisters a worker picked up from an earlier build', async () => {
    setEnv('development');
    render(<ServiceWorkerRegister />);
    await waitFor(() => expect(unregister).toHaveBeenCalled());
  });
});
