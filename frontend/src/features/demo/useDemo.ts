import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";

export interface AuthConfig { google_client_id: string | null; demo?: boolean; guest_days?: number }
/** Public settings of this server. `demo` is true only on the public online demo. */
export function useDemo() {
  const q = useQuery({ queryKey: ["auth-config"], queryFn: () => api.get<AuthConfig>("/auth/config"), staleTime: Infinity });
  return { demo: !!q.data?.demo, guestDays: q.data?.guest_days ?? 7 };
}

/** The crawler does not run online, so demo visitors see a dummy Crawler page with invented data. */
export function useNoCrawler() { const { demo } = useDemo(); const { user } = useAuth(); return demo && user?.role !== "admin"; }

export const openTour = () => window.dispatchEvent(new Event("open-tour"));
export const GUEST_DOMAIN = "@guest.demo.example.com";
export const REPO = "https://github.com/emelian-chkaira/ai-career-tracker";
