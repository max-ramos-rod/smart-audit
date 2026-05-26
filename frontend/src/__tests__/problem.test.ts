import { describe, expect, it } from 'vitest'
import { extractProblemMessage } from '@/services/api/problem'

const FALLBACK = 'Algo deu errado.'

describe('extractProblemMessage', () => {
  it('returns fallback when error has no response', () => {
    expect(extractProblemMessage(new Error('network'), FALLBACK)).toBe(FALLBACK)
  })

  it('returns fallback when error is null', () => {
    expect(extractProblemMessage(null, FALLBACK)).toBe(FALLBACK)
  })

  it('returns detail string directly', () => {
    const err = { response: { data: { detail: 'Email inválido.' } } }
    expect(extractProblemMessage(err, FALLBACK)).toBe('Email inválido.')
  })

  it('skips generic validation detail and uses first error msg with field', () => {
    const err = {
      response: {
        data: {
          detail: 'A requisicao contem dados invalidos.',
          errors: [{ loc: ['body', 'email'], msg: 'field required' }],
        },
      },
    }
    expect(extractProblemMessage(err, FALLBACK)).toBe('email: field required')
  })

  it('returns just msg when error loc is absent', () => {
    const err = {
      response: {
        data: {
          detail: 'A requisicao contem dados invalidos.',
          errors: [{ msg: 'value is not a valid email' }],
        },
      },
    }
    expect(extractProblemMessage(err, FALLBACK)).toBe('value is not a valid email')
  })

  it('falls back to detail when errors array is empty', () => {
    const err = {
      response: {
        data: {
          detail: 'A requisicao contem dados invalidos.',
          errors: [],
        },
      },
    }
    expect(extractProblemMessage(err, FALLBACK)).toBe('A requisicao contem dados invalidos.')
  })

  it('returns fallback when payload has neither detail nor errors', () => {
    const err = { response: { data: {} } }
    expect(extractProblemMessage(err, FALLBACK)).toBe(FALLBACK)
  })
})
