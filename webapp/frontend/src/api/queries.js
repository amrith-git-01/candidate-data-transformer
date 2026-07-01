import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export const queryKeys = {
  configs: ["configs"],
  config: (name) => ["configs", name],
  source: (source, page, pageSize) => ["sample", source, page, pageSize],
  results: (page, pageSize) => ["results", page, pageSize],
};

export function useConfigsQuery() {
  return useQuery({ queryKey: queryKeys.configs, queryFn: api.listConfigs });
}

export function useConfigQuery(name, options = {}) {
  return useQuery({
    queryKey: queryKeys.config(name),
    queryFn: () => api.getConfig(name),
    enabled: Boolean(name),
    ...options,
  });
}

export function useSourcePageQuery(source, page, pageSize) {
  return useQuery({
    queryKey: queryKeys.source(source, page, pageSize),
    queryFn: () => api.getSourcePage(source, page, pageSize),
    // Only reuse placeholder data across a page change *within* the same
    // source — csv/ats/notes rows have different shapes, so carrying rows
    // from one source over into another's column definitions crashes the
    // table (e.g. notes columns reading `.notes` off a csv row).
    placeholderData: (previousData, previousQuery) =>
      previousQuery?.queryKey?.[1] === source ? previousData : undefined,
  });
}

export function useResultsQuery(page, pageSize) {
  return useQuery({
    queryKey: queryKeys.results(page, pageSize),
    queryFn: () => api.getResults(page, pageSize),
    placeholderData: (prev) => prev,
  });
}

export function useGenerateSampleMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ count, seed }) => api.generateSample(count, seed),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sample"] });
    },
  });
}

export function useRunPipelineMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ config, enrichGithub }) => api.runPipeline(config, enrichGithub),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["results"] });
    },
  });
}
