export type PriorityExplanation = {
  score: number;
  reasons: string[];
};

export type Task = {
  id: number;
  title: string;
  description: string;
  category: string;
  tags: string[];
  start_date: string | null;
  due_date: string | null;
  estimated_minutes: number;
  importance: number;
  is_completed: boolean;
  is_fixed: boolean;
  recurrence: string | null;
  notes: string;
  priority: PriorityExplanation;
};

export type NewTask = {
  title: string;
  category: string;
  due_date: string | null;
  estimated_minutes: number;
  importance: number;
};

