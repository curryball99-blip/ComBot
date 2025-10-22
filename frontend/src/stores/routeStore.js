import { create } from 'zustand';

const useRouteStore = create((set) => ({
  currentRoute: 'chat',
  setRoute: (route) => set({ currentRoute: route }),
}));

export default useRouteStore;