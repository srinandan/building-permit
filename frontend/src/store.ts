import { create } from 'zustand';

interface User {
  id: number;
  email: string;
  name: string;
}

interface Property {
  id: number;
  user_id: number;
  address: string;
  city: string;
  zip_code: string;
}

interface AuthState {
  user: User | null;
  currentProperty: Property | null;
  login: (user: User) => void;
  logout: () => void;
  setCurrentProperty: (property: Property | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  currentProperty: null,
  login: (user) => set({ user }),
  logout: () => set({ user: null, currentProperty: null }),
  setCurrentProperty: (property) => set({ currentProperty: property }),
}));
