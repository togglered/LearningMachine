import { api } from './client'

export type AttemptStatus = 'in_progress' | 'submitted' | 'expired'

export interface Answer {
  id: number
  question: number
  response: unknown
  is_correct: boolean | null
  awarded_points: string | null
}

export interface Attempt {
  id: number
  test: number
  status: AttemptStatus
  started_at: string
  time_limit: string | null
  submitted_at: string | null
  score: string | null
  answers: Answer[]
}

export const startAttempt = (test: number, useDefaultTime = true) =>
  api.post<Attempt>('/attempts/', { test, use_default_time: useDefaultTime }).then((r) => r.data)

export const getAttempt = (id: number | string) =>
  api.get<Attempt>(`/attempts/${id}/`).then((r) => r.data)

export const saveAnswer = (attemptId: number, question: number, response: unknown) =>
  api.post<Attempt>(`/attempts/${attemptId}/answers/`, { question, response }).then((r) => r.data)

export const finishAttempt = (attemptId: number) =>
  api.post<Attempt>(`/attempts/${attemptId}/finish/`).then((r) => r.data)
