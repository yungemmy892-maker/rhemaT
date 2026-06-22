// Mock auth — frontend only
export type User = {
  name: string;
  email: string;
  avatar: string;
  plan: "Free" | "Pro";
};

const KEY = "verseid_user";

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  try {
    return JSON.parse(localStorage.getItem(KEY) || "null");
  } catch {
    return null;
  }
}

function avatarFor(seed: string) {
  return `https://api.dicebear.com/9.x/notionists/svg?seed=${encodeURIComponent(seed)}&backgroundColor=ede9fe`;
}

export function signInGoogle(): User {
  const u: User = {
    name: "Sarah Bennett",
    email: "sarah.bennett@gmail.com",
    avatar: avatarFor("Sarah"),
    plan: "Free",
  };
  localStorage.setItem(KEY, JSON.stringify(u));
  return u;
}

export function signInEmail(email: string): User {
  const name = email.split("@")[0].replace(/[._]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "Friend";
  const u: User = { name, email, avatar: avatarFor(email), plan: "Free" };
  localStorage.setItem(KEY, JSON.stringify(u));
  return u;
}

export function registerEmail(name: string, email: string): User {
  const u: User = { name: name || "Friend", email, avatar: avatarFor(name || email), plan: "Free" };
  localStorage.setItem(KEY, JSON.stringify(u));
  return u;
}

export function upgradeToPro() {
  const u = getUser();
  if (!u) return;
  u.plan = "Pro";
  localStorage.setItem(KEY, JSON.stringify(u));
}

export function signOut() {
  localStorage.removeItem(KEY);
}

export function deleteAccount() {
  localStorage.removeItem(KEY);
}
