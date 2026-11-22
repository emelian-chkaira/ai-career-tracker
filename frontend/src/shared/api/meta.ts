import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { SectorsOut } from "./types";

/** Fields (sectors), countries, regions and work modes with live job counts. Cached for 10 minutes; used by filters, setup and the crawler. */
export const useSectors = () => useQuery({ queryKey: ["sectors"], staleTime: 600_000, queryFn: () => api.get<SectorsOut>("/jobs/sectors") });
