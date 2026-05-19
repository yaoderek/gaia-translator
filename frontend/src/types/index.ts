export type Discipline =
  | "hydrology"
  | "seismology"
  | "atmospheric_science"
  | "climatology"
  | "geology"
  | "computer_science"
  | "applied_mathematics";

/** Target selector can be a discipline or "Personalized" when logged in. */
export type TargetDiscipline = Discipline | "personalized";

export interface DisciplineInfo {
  value: Discipline;
  label: string;
  description: string;
  key_concepts: string[];
}

export interface Citation {
  index: number;
  paper_id: string;
  title: string;
  authors: string;
  excerpt: string;
  doi: string | null;
}

export interface FigureRef {
  figure_id: string;
  paper_id: string;
  caption: string;
  page: number;
}

export interface TranslateResponse {
  translation: string;
  citations: Citation[];
  figures: FigureRef[];
  follow_up_questions: string[];
}

export interface StreamMetadata {
  type: "metadata";
  citations: Citation[];
  figures: FigureRef[];
  personalized?: boolean;
}

export interface StreamToken {
  type: "token";
  content: string;
}

export type StreamEvent = StreamMetadata | StreamToken;

export interface PaperInfo {
  paper_id: string;
  title: string;
  authors: string;
  filename: string;
  num_chunks: number;
  num_figures: number;
  ingested_at: string;
  uploaded_by_user_id?: string | null;
}
