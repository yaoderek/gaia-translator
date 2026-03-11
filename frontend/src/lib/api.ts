import axios from "axios";
import type { DisciplineInfo, PaperInfo } from "../types";

const client = axios.create({ baseURL: "/api" });

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
