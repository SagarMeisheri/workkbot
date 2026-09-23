import { describe, it } from 'node:test';
import assert from 'node:assert';
import { AuthStorage } from '../lib/auth';

describe('AuthStorage SecureStore Adapter (Gate B1-G5)', () => {
  it('should store, retrieve, and delete JWT tokens securely', async () => {
    const testToken = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.signature';

    // 1. Set token
    await AuthStorage.setToken(testToken);

    // 2. Get token
    const retrieved = await AuthStorage.getToken();
    assert.strictEqual(retrieved, testToken, 'Token must match the stored value');

    // 3. Delete token
    await AuthStorage.deleteToken();
    const afterDelete = await AuthStorage.getToken();
    assert.strictEqual(afterDelete, null, 'Token must be null after deletion');
  });

  it('should securely serialize and retrieve user profiles', async () => {
    const profile = { id: 'usr_123', email: 'officer@mumbai.gov.in', role: 'admin' };
    await AuthStorage.setUserProfile(profile);

    const retrieved = await AuthStorage.getUserProfile<typeof profile>();
    assert.deepStrictEqual(retrieved, profile, 'Profile must match serialized data');
  });
});
