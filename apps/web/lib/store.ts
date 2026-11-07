"use client";
import {create} from "zustand";
import {createJSONStorage, persist} from "zustand/middleware";

interface AuthState {
  token: string | null;
  user: import("./types").User | null;
  setAuth: (token: string, user: import("./types").User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) =>
        set({token, user}),
      logout: () => set({token: null, user: null}),
    }),
    {name: "cineforge-auth", storage: createJSONStorage(() => localStorage)},
  ),
);
