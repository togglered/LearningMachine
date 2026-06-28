<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTest, flattenQuestions, type Question } from '@/api/tests'
import { Button } from '@/components/ui/button'
import { getAttempt, selfAssess, startAttempt, type Attempt, type Answer } from '@/api/attempts'

const route = useRoute()
const router = useRouter()
const attemptId = Number(route.params.id)

const loading = ref(true)
const error = ref('')
const attempt = ref<Attempt | null>(null)
const questions = ref<Question[]>([])
const essayScores = ref<Record<number, Record<string, number>>>({})
const totalPoints = computed(() => questions.value.reduce((s, q) => s + Number(q.points), 0))
const earned = computed(() => Number(attempt.value?.score ?? 0))

onMounted(async () => {
  try {
    const att = await getAttempt(attemptId)
    attempt.value = att
    questions.value = flattenQuestions(await getTest(att.test))
    for (const q of questions.value) {
      if (q.kind === 'essay') {
        essayScores.value[q.id] = Object.fromEntries(
          (q.content.criteria ?? []).map((c) => [c.id, 0]),
        )
      }
    }
  } catch {
    error.value = 'Unable to load results'
  } finally {
    loading.value = false
  }
})

const answerByQ = computed(
  () => new Map((attempt.value?.answers ?? []).map((a) => [a.question, a])),
)
const total = computed(() => questions.value.length)
const correctCount = computed(
  () => (attempt.value?.answers ?? []).filter((a) => a.is_correct).length,
)
const wrongCount = computed(() => total.value - correctCount.value)
const scorePct = computed(() =>
  totalPoints.value ? Math.round((earned.value / totalPoints.value) * 100) : 0,
)

function yourAnswer(q: Question, a?: Answer) {
  if (!a || a.response == null || a.response === '') return 'No response'
  if (q.kind === 'single_choice')
    return q.content.options?.find((o) => o.id === a.response)?.text ?? String(a.response)
  if (q.kind === 'multi_choice' && Array.isArray(a.response))
    return a.response
      .map((id) => q.content.options?.find((o) => o.id === id)?.text ?? id)
      .join(', ')
  if (q.kind === 'gap_fill' && a.response && typeof a.response === 'object') {
    return Object.values(a.response as Record<string, string>).join(', ')
  }
  if (q.kind === 'matching' && a.response && typeof a.response === 'object') {
    const r = a.response as Record<string, string>
    return (q.content.left ?? [])
      .map((l) => {
        const rightText = (q.content.right ?? []).find((x) => x.id === r[l.id])?.text ?? '—'
        return `${l.text} → ${rightText}`
      })
      .join('; ')
  }
  return String(a.response)
}
async function retake() {
  if (!attempt.value) return
  const att = await startAttempt(attempt.value.test)
  router.push({ name: 'test-run', params: { id: att.id } })
}
function essayText(q: Question): string {
  const r = answerByQ.value.get(q.id)?.response
  return typeof r === 'string' && r ? r : '(blank)'
}
async function assessEssay(q: Question) {
  attempt.value = await selfAssess(attemptId, q.id, essayScores.value[q.id])
}
function essayMax(q: Question): number {
  return (q.content.criteria ?? []).reduce((s, c) => s + c.points, 0)
}
function essayVerdict(q: Question): 'full' | 'partial' | 'zero' | null {
  const a = answerByQ.value.get(q.id)
  if (a?.awarded_points == null) return null
  const pts = Number(a.awarded_points)
  if (pts <= 0) return 'zero'
  return pts >= essayMax(q) ? 'full' : 'partial'
}
</script>

<template>
  <div class="max-w-[760px] mx-auto px-7 py-9">
    <div v-if="loading" class="text-center text-muted-foreground py-20">Loading…</div>
    <div v-else-if="error" class="text-center text-destructive py-20">{{ error }}</div>

    <template v-else>
      <div class="bg-card border rounded-[18px] p-10 flex flex-col items-center text-center mb-5">
        <div
          class="w-[150px] h-[150px] rounded-full flex items-center justify-center"
          :style="{
            background: `conic-gradient(var(--primary) ${scorePct * 3.6}deg, var(--border) 0deg)`,
          }"
        >
          <div class="w-28 h-28 rounded-full bg-card flex flex-col items-center justify-center">
            <span class="text-[34px] font-bold leading-none">{{ scorePct }}%</span>
            <span class="text-xs text-muted-foreground">result</span>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-3 gap-4 mb-5">
        <div class="bg-card border rounded-[14px] p-5 text-center">
          <div class="text-[28px] font-bold text-success">{{ correctCount }}</div>
          <div class="text-sm text-muted-foreground">Correct</div>
        </div>
        <div class="bg-card border rounded-[14px] p-5 text-center">
          <div class="text-[28px] font-bold text-destructive">{{ wrongCount }}</div>
          <div class="text-sm text-muted-foreground">Incorrect</div>
        </div>
        <div class="bg-card border rounded-[14px] p-5 text-center">
          <div class="text-[28px] font-bold text-primary">{{ total }}</div>
          <div class="text-sm text-muted-foreground">Total</div>
        </div>
      </div>

      <div class="bg-card border rounded-[18px] p-7 mb-5">
        <div class="text-lg font-bold mb-4.5">Analysis of the Answers</div>
        <div class="flex flex-col gap-4">
          <div v-for="q in questions" :key="q.id" class="border-b pb-4 last:border-0 last:pb-0">
            <template v-if="q.kind === 'essay'">
              <div class="text-[15px] font-semibold leading-snug mb-2">{{ q.prompt }}</div>
              <div class="text-sm text-[#5d7689] whitespace-pre-wrap bg-muted rounded-lg p-3 mb-3">
                {{ essayText(q) }}
              </div>
              <div class="flex flex-col gap-2">
                <div
                  v-for="c in q.content.criteria ?? []"
                  :key="c.id"
                  class="flex items-center justify-between gap-3 text-sm"
                >
                  <span>{{ c.text }}</span>
                  <select
                    v-model.number="essayScores[q.id][c.id]"
                    class="px-2 py-1 border-[1.5px] border-border rounded-md bg-card outline-none focus:border-primary"
                  >
                    <option v-for="n in c.points + 1" :key="n - 1" :value="n - 1">
                      {{ n - 1 }} / {{ c.points }}
                    </option>
                  </select>
                </div>
                <div class="flex items-center gap-3 mt-1">
                  <Button size="sm" @click="assessEssay(q)">Save rating</Button>
                  <span
                    v-if="answerByQ.get(q.id)?.awarded_points != null"
                    class="text-sm font-semibold text-success"
                  >
                    Self assessment: {{ answerByQ.get(q.id)?.awarded_points }} points
                  </span>
                  <span
                    v-if="essayVerdict(q)"
                    class="text-xs font-semibold px-2.5 py-[3px] rounded-full"
                    :class="{
                      'bg-success-muted text-success': essayVerdict(q) === 'full',
                      'bg-warning-muted text-warning': essayVerdict(q) === 'partial',
                      'bg-destructive-muted text-destructive': essayVerdict(q) === 'zero',
                    }"
                  >
                    {{
                      {
                        full: 'Absolutely Correct',
                        partial: 'Pertically Correct',
                        zero: 'Absolutely Incorrect',
                      }[essayVerdict(q)!]
                    }}
                  </span>
                </div>
              </div>
            </template>

            <template v-else>
              <div class="flex items-start justify-between gap-3.5 mb-2">
                <span class="text-[15px] font-semibold leading-snug">{{ q.prompt }}</span>
                <span
                  class="flex-none text-xs font-semibold px-2.5 py-[3px] rounded-full"
                  :class="
                    answerByQ.get(q.id)?.is_correct
                      ? 'bg-success-muted text-success'
                      : 'bg-destructive-muted text-destructive'
                  "
                >
                  {{ answerByQ.get(q.id)?.is_correct ? 'Correct' : 'Incorrect' }}
                </span>
              </div>
              <div class="text-sm text-[#5d7689]">
                Your response:
                <span class="font-semibold">{{ yourAnswer(q, answerByQ.get(q.id)) }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="flex gap-3 flex-wrap">
        <Button @click="retake">Try again</Button>
        <Button variant="secondary" @click="router.push({ name: 'tests' })">To the Tests</Button>
      </div>
    </template>
  </div>
</template>
