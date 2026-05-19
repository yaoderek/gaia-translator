import axios from "axios";
import type { DisciplineInfo, PaperInfo } from "../types";
import { getAuthTokenAsync } from "./supabase";

const client = axios.create({ baseURL: "/api" });

client.interceptors.request.use(async (config) => {
  const token = await getAuthTokenAsync();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function fetchDisciplines(): Promise<DisciplineInfo[]> {
  const { data } = await client.get<DisciplineInfo[]>("/disciplines");
  return data;
}

export async function fetchPapers(): Promise<PaperInfo[]> {
  const { data } = await client.get<PaperInfo[]>("/papers");
  return data;
}

export async function triggerIngest(): Promise<{
  papers_ingested: number;
  total_chunks: number;
  total_figures: number;
}> {
  const { data } = await client.post("/ingest");
  return data;
}

export function getFigureUrl(figureId: string): string {
  return `/api/figures/${figureId}`;
}

export async function uploadPaper(file: File): Promise<{
  status: string;
  paper_id: string;
  title?: string;
  message?: string;
  num_chunks?: number;
  num_figures?: number;
}> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post("/papers/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120_000,
  });
  return data;
}

export interface Persona {
  username: string;
  discipline: string;
  bio: string;
  tags: string;
  papers_of_interest: string;
  concepts_focus: string;
  methods_focus: string;
  tech_stack: string;
  updated_at: string | null;
}

export interface MeResponse {
  user_id: string;
  email: string | null;
  username: string;
  persona: Persona;
}

export async function fetchMe(): Promise<MeResponse> {
  const { data } = await client.get<MeResponse>("/me");
  return data;
}

export async function updatePersona(body: Partial<Omit<Persona, "updated_at">>): Promise<void> {
  await client.put("/me/persona", body);
}
