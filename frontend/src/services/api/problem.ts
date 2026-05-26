type ValidationErrorItem = {
  loc?: Array<string | number>
  msg?: string
}

export function extractProblemMessage(error: any, fallback: string): string {
  const payload = error?.response?.data

  if (!payload) {
    return fallback
  }

  if (typeof payload.detail === 'string' && payload.detail !== 'A requisicao contem dados invalidos.') {
    return payload.detail
  }

  const firstError = payload.errors?.[0] as ValidationErrorItem | undefined
  if (firstError?.msg) {
    const field = firstError.loc?.[firstError.loc.length - 1]
    return field ? `${String(field)}: ${firstError.msg}` : firstError.msg
  }

  if (typeof payload.detail === 'string') {
    return payload.detail
  }

  return fallback
}
