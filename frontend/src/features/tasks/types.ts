export type PriorityExplanation = {
  score: number;
  reasons: string[];
};

export type Task = {
  id: number;
  title: string;
  description: string;
  category: string;
  project: string | null;
  tags: string[];
  start_date: string | null;
  due_date: string | null;
  estimated_minutes: number;
  importance: number;
  is_completed: boolean;
  completed_at: string | null;
  is_fixed: boolean;
  recurrence: string | null;
  recurrence_time_zone: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
  priority: PriorityExplanation;
};

export type NewTask = {
  title: string;
  category: string;
  due_date: string | null;
  estimated_minutes: number;
  importance: number;
};

export type TaskUpdate = Omit<
  Task,
  "id" | "priority" | "completed_at" | "created_at" | "updated_at"
>;

