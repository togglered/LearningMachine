import { api } from './client'

export type QuestionKind =
  | 'single_choice'
  | 'multi_choice'
  | 'gap_fill'
  | 'matching'
  | 'short_answer'
  | 'essay'

export interface Option {
  id: string
  text: string
}

export interface Question {
  id: number
  kind: QuestionKind
  prompt: string
  content: {
    options?: Option[] // single/multi
    text?: string // gap_fill: "...{{1}}...{{2}}..."
    gaps?: { id: string }[] // gap_fill
    left?: Option[] // matching
    right?: Option[] // matching
    criteria?: { id: string; text: string; points: number }[] // essay
  } & Record<string, unknown>
  points: string
  position: number
}

export interface TaskGroup {
  id: number
  instructions: string
  passage: string
  audio: string | null
  image: string | null
  position: number
  questions: Question[]
}

export interface Section {
  id: number
  section_type: string
  position: number
  task_groups: TaskGroup[]
}

export interface TestListItem {
  id: number
  subject: number
  time_limit: string | null
  is_published: boolean
}

export interface TestDetail {
  id: number
  subject: number
  time_limit: string | null
  sections: Section[]
}

export const listTests = () => api.get<TestListItem[]>('/tests/').then((r) => r.data)

export const getTest = (id: number | string) =>
  api.get<TestDetail>(`/tests/${id}/`).then((r) => r.data)

export function flattenQuestions(test: TestDetail): Question[] {
  return test.sections.flatMap((s) => s.task_groups).flatMap((tg) => tg.questions)
}
