"use client";
import {create} from "zustand";
import {createJSONStorage, persist} from "zustand/middleware";

interface AuthState {
  token: string | null;
  user: import("./types").User | null;
  /** true once the persisted auth state has been restored (localStorage is async). */
  hydrated: boolean;
  setAuth: (token: string, user: import("./types").User) => void;
  markHydrated: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hydrated: false,
      setAuth: (token, user) =>
        set({token, user, hydrated: true}),
      markHydrated: () => set({hydrated: true}),
      logout: () => set({token: null, user: null, hydrated: true}),
    }),
    {
      name: "cineforge-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({token: s.token, user: s.user}),
      /** The guarded layout must wait for this before redirecting ("Redirecting to login" races). */
      onRehydrateStorage: () => (state) => state?.markHydrated(),
    },
  ),
);
