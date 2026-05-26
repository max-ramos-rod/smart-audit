import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearAccessToken,
  clearCompanyId,
  readAccessToken,
  readCompanyId,
  writeAccessToken,
  writeCompanyId,
} from '@/services/api/storage'

beforeEach(() => {
  localStorage.clear()
})

describe('access token storage', () => {
  it('returns null when nothing stored', () => {
    expect(readAccessToken()).toBeNull()
  })

  it('reads back what was written', () => {
    writeAccessToken('tok_abc123')
    expect(readAccessToken()).toBe('tok_abc123')
  })

  it('clear removes the token', () => {
    writeAccessToken('tok_abc123')
    clearAccessToken()
    expect(readAccessToken()).toBeNull()
  })
})

describe('company id storage', () => {
  it('returns null when nothing stored', () => {
    expect(readCompanyId()).toBeNull()
  })

  it('reads back what was written', () => {
    writeCompanyId('company-uuid-1')
    expect(readCompanyId()).toBe('company-uuid-1')
  })

  it('clear removes the company id', () => {
    writeCompanyId('company-uuid-1')
    clearCompanyId()
    expect(readCompanyId()).toBeNull()
  })
})
