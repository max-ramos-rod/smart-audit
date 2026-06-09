export const SCORE_THRESHOLD_OK = 85
export const SCORE_THRESHOLD_WARN = 65

export function scoreClass(score: number): 'ok' | 'warn' | 'err' {
  return score >= SCORE_THRESHOLD_OK ? 'ok' : score >= SCORE_THRESHOLD_WARN ? 'warn' : 'err'
}

export function scoreColorVar(score: number): string {
  return score >= SCORE_THRESHOLD_OK
    ? 'var(--sa-ok)'
    : score >= SCORE_THRESHOLD_WARN
      ? 'var(--sa-warn)'
      : 'var(--sa-danger)'
}

export function scoreChipClass(score: number): string {
  return score >= SCORE_THRESHOLD_OK
    ? ''
    : score >= SCORE_THRESHOLD_WARN
      ? 'status-chip--warn'
      : 'status-chip--inactive'
}

export function scoreText(score: number): string {
  return score >= SCORE_THRESHOLD_OK
    ? 'Aprovado'
    : score >= SCORE_THRESHOLD_WARN
      ? 'Atenção'
      : 'Reprovado'
}
