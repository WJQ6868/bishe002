export const clearAuthState = () => {
  const keys = [
    'token',
    'is_login',
    'user_role',
    'user_account',
    'user_id',
    'user_name',
  ]
  keys.forEach((key) => localStorage.removeItem(key))
}
