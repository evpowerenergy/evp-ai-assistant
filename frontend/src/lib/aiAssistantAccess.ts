/**
 * Roles allowed to use the AI Assistant web app and authenticated APIs.
 * Keep in sync with backend AI_ASSISTANT_ALLOWED_ROLES / config default.
 */
export const AI_ASSISTANT_ALLOWED_ROLES = [
  'super_admin',
  'manager_sale',
  'manager_marketing',
  'manager_hr',
] as const

export function hasAiAssistantAccess(role: string | null | undefined): boolean {
  if (role == null || role === '') return false
  const r = role.toLowerCase().trim()
  return (AI_ASSISTANT_ALLOWED_ROLES as readonly string[]).includes(r)
}
