type ValidationErrorItem = {
  loc?: Array<string | number>
  msg?: string
}

type ProblemPayload = {
  detail?: string
  errors?: ValidationErrorItem[]
}

export function extractProblemMessage(error: unknown, fallback: string): string {
  const payload = (error as { response?: { data?: ProblemPayload } })?.response?.data

  if (!payload) {
    return fallback
  }

  if (
    typeof payload.detail === 'string' &&
    payload.detail !== 'A requisicao contem dados invalidos.'
  ) {
    return payload.detail
  }

  const firstError = payload.errors?.[0]
  if (firstError?.msg) {
    const field = firstError.loc?.[firstError.loc.length - 1]
    return field ? `${String(field)}: ${firstError.msg}` : firstError.msg
  }

  if (typeof payload.detail === 'string') {
    return payload.detail
  }

  return fallback
}
