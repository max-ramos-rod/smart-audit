const TOKEN_KEY = 'smart-audit.token'
const COMPANY_KEY = 'smart-audit.company-id'

export function readAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function writeAccessToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function readCompanyId(): string | null {
  return localStorage.getItem(COMPANY_KEY)
}

export function writeCompanyId(companyId: string): void {
  localStorage.setItem(COMPANY_KEY, companyId)
}

export function clearCompanyId(): void {
  localStorage.removeItem(COMPANY_KEY)
}
