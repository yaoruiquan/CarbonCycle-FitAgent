const USER_ID_KEY = "user_id";
const AUTH_TOKEN_KEY = "auth_token";
const USER_NAME_KEY = "user_name";

const isBrowser = () => typeof window !== "undefined";

export const userStorage = {
  getUserId(): string | null {
    if (!isBrowser()) return null;
    return localStorage.getItem(USER_ID_KEY);
  },
  setUserId(id: string) {
    if (!isBrowser()) return;
    localStorage.setItem(USER_ID_KEY, id);
  },
  clearUserId() {
    if (!isBrowser()) return;
    localStorage.removeItem(USER_ID_KEY);
  },
  getAuthToken(): string | null {
    if (!isBrowser()) return null;
    return localStorage.getItem(AUTH_TOKEN_KEY);
  },
  setAuthToken(token: string) {
    if (!isBrowser()) return;
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  },
  clearAuthToken() {
    if (!isBrowser()) return;
    localStorage.removeItem(AUTH_TOKEN_KEY);
  },
  getUserName(): string | null {
    if (!isBrowser()) return null;
    return localStorage.getItem(USER_NAME_KEY);
  },
  setUserName(name: string) {
    if (!isBrowser()) return;
    localStorage.setItem(USER_NAME_KEY, name);
  },
  clearUserName() {
    if (!isBrowser()) return;
    localStorage.removeItem(USER_NAME_KEY);
  },
  clearAll() {
    if (!isBrowser()) return;
    localStorage.removeItem(USER_ID_KEY);
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USER_NAME_KEY);
  },
};
