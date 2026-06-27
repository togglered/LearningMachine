<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTest, flattenQuestions, type Question } from '@/api/tests'
import { getAttempt, saveAnswer, finishAttempt, type Attempt } from '@/api/attempts'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const route = useRoute()
const router = useRouter()
const attemptId = Number(route.params.id)

const loading = ref(true)
const error = ref('')
const questions = ref<Question[]>([])
const attempt = ref<Attempt | null>(null)
const responses = ref<Record<number, unknown>>({})
const busy = ref(false)
const finished = ref(false)

const now = ref(Date.now())
let ticker: number | undefined

const TEXT_DEBOUNCE = 10000
const pendingTimers = new Map<number, number>()

const letters = ['A', 'B', 'C', 'D', 'E', 'F']

const total = computed(() => questions.value.length)
function hasAnswer(r: unknown): boolean {
  if (r === undefined || r === null || r === '') return false
  if (Array.isArray(r)) return r.length > 0
  if (typeof r === 'object') return Object.keys(r).length > 0
  return true
}
const answered = computed(
  () => questions.value.filter((q) => hasAnswer(responses.value[q.id])).length,
)
const deadline = computed(() => {
  if (!attempt.value?.time_limit) return null
  return (
    new Date(attempt.value.started_at).getTime() + parseDuration(attempt.value.time_limit) * 1000
  )
})
const remaining = computed(() =>
  deadline.value === null ? null : Math.max(0, Math.floor((deadline.value - now.value) / 1000)),
)
const timeStr = computed(() => {
  if (remaining.value === null) return ''
  const m = Math.floor(remaining.value / 60)
  return `${m}:${String(remaining.value % 60).padStart(2, '0')}`
})
function parseDuration(s: string): number {
  const [daysPart, timePart] = s.includes(' ') ? s.split(' ') : ['0', s]
  const [h, m, sec] = timePart.split(':')
  return Number(daysPart) * 86400 + Number(h) * 3600 + Number(m) * 60 + parseFloat(sec)
}
async function saveResponse(qid: number, response: unknown) {
  if (!attempt.value) return
  try {
    await saveAnswer(attempt.value.id, qid, response)
  } catch {}
}
function scheduleTextSave(qid: number) {
  const existing = pendingTimers.get(qid)
  if (existing) clearTimeout(existing)
  pendingTimers.set(
    qid,
    window.setTimeout(() => {
      pendingTimers.delete(qid)
      saveResponse(qid, responses.value[qid])
    }, TEXT_DEBOUNCE),
  )
}
async function flushPending() {
  for (const t of pendingTimers.values()) clearTimeout(t)
  const ids = [...pendingTimers.keys()]
  pendingTimers.clear()
  for (const qid of ids) await saveResponse(qid, responses.value[qid])
}
function selectSingle(qid: number, optId: string) {
  responses.value[qid] = optId
  saveResponse(qid, optId)
}
type Segment = { type: 'text'; value: string } | { type: 'gap'; id: string }
function gapSegments(q: Question): Segment[] {
  const text = q.content.text ?? ''
  const out: Segment[] = []
  let last = 0
  for (const m of text.matchAll(/\{\{(\w+)\}\}/g)) {
    const idx = m.index
    if (idx > last) out.push({ type: 'text', value: text.slice(last, idx) })
    out.push({ type: 'gap', id: m[1] })
    last = idx + m[0].length
  }
  if (last < text.length) out.push({ type: 'text', value: text.slice(last) })
  return out
}
function gapVal(qid: number, gapId: string): string {
  return ((responses.value[qid] as Record<string, string>) ?? {})[gapId] ?? ''
}
function setGap(qid: number, gapId: string, val: string) {
  const cur = (responses.value[qid] as Record<string, string>) ?? {}
  responses.value[qid] = { ...cur, [gapId]: val }
  scheduleTextSave(qid)
}
function matchVal(qid: number, leftId: string): string {
  return ((responses.value[qid] as Record<string, string>) ?? {})[leftId] ?? ''
}
function setMatch(qid: number, leftId: string, rightId: string) {
  const cur = (responses.value[qid] as Record<string, string>) ?? {}
  responses.value[qid] = { ...cur, [leftId]: rightId }
  saveResponse(qid, responses.value[qid])
}
function isSingle(qid: number, optId: string) {
  return responses.value[qid] === optId
}
function isMulti(qid: number, optId: string) {
  return ((responses.value[qid] as string[]) ?? []).includes(optId)
}
function toggleMulti(qid: number, optId: string) {
  const cur = (responses.value[qid] as string[]) ?? []
  const next = cur.includes(optId) ? cur.filter((x) => x !== optId) : [...cur, optId]
  responses.value[qid] = next
  saveResponse(qid, next)
}
function onText(qid: number, val: string) {
  responses.value[qid] = val
  scheduleTextSave(qid)
}
async function finish() {
  if (!attempt.value || finished.value) return
  finished.value = true
  busy.value = true
  try {
    await flushPending()
    const done = await finishAttempt(attempt.value.id)
    router.push({ name: 'results', params: { id: done.id } })
  } finally {
    busy.value = false
  }
}
watch(remaining, (r) => {
  if (r === 0 && !finished.value) finish()
})
onMounted(async () => {
  try {
    const att = await getAttempt(attemptId)
    if (att.status !== 'in_progress') {
      router.replace({ name: 'results', params: { id: att.id } })
      return
    }
    attempt.value = att
    questions.value = flattenQuestions(await getTest(att.test))
    for (const a of att.answers) responses.value[a.question] = a.response
    ticker = window.setInterval(() => {
      now.value = Date.now()
    }, 1000)
  } catch {
    error.value = 'Unable to load the test'
  } finally {
    loading.value = false
  }
})
onUnmounted(() => {
  if (ticker) clearInterval(ticker)
  for (const [qid, t] of pendingTimers) {
    clearTimeout(t)
    saveResponse(qid, responses.value[qid])
  }
  pendingTimers.clear()
})
</script>

<template>
  <div class="max-w-[780px] mx-auto px-7 py-8">
    <div v-if="loading" class="text-center text-muted-foreground py-20">Loading…</div>
    <div v-else-if="error" class="text-center text-destructive py-20">{{ error }}</div>

    <template v-else>
      <div class="flex items-center justify-between mb-6">
        <button
          class="text-[15px] font-medium text-muted-foreground hover:text-primary"
          @click="router.push({ name: 'tests' })"
        >
          ← To the Tests
        </button>
        <div class="flex items-center gap-2.5">
          <span
            v-if="remaining !== null"
            class="text-sm font-semibold px-3.5 py-1.5 rounded-full"
            :class="
              remaining <= 60 ? 'bg-destructive-muted text-destructive' : 'bg-accent text-primary'
            "
          >
            ⏱ {{ timeStr }}
          </span>
          <span class="text-sm font-semibold text-primary bg-accent px-3.5 py-1.5 rounded-full">
            Answered {{ answered }} / {{ total }}
          </span>
        </div>
      </div>

      <div class="flex flex-col gap-5">
        <div v-for="(q, qi) in questions" :key="q.id" class="bg-card border rounded-[18px] p-7">
          <div class="flex gap-3 mb-5">
            <div
              class="flex-none w-7 h-7 rounded-lg bg-muted flex items-center justify-center font-bold text-[13px] text-[#4a6678]"
            >
              {{ qi + 1 }}
            </div>
            <div class="text-lg font-semibold leading-snug pt-0.5">{{ q.prompt }}</div>
          </div>

          <div
            v-if="q.kind === 'single_choice' || q.kind === 'multi_choice'"
            class="flex flex-col gap-3"
          >
            <button
              v-for="(opt, i) in q.content.options"
              :key="opt.id"
              class="flex items-center gap-3.5 px-4 py-3 border-[1.5px] rounded-xl text-left transition"
              :class="
                (q.kind === 'single_choice' ? isSingle(q.id, opt.id) : isMulti(q.id, opt.id))
                  ? 'border-primary bg-accent'
                  : 'border-border hover:border-[#d4e2ec]'
              "
              @click="
                q.kind === 'single_choice' ? selectSingle(q.id, opt.id) : toggleMulti(q.id, opt.id)
              "
            >
              <div
                class="flex-none w-7 h-7 rounded-lg flex items-center justify-center font-bold text-[13px]"
                :class="
                  (q.kind === 'single_choice' ? isSingle(q.id, opt.id) : isMulti(q.id, opt.id))
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-[#4a6678]'
                "
              >
                {{ letters[i] }}
              </div>
              <span>{{ opt.text }}</span>
            </button>
          </div>

          <Input
            v-else-if="q.kind === 'short_answer'"
            :model-value="(responses[q.id] as string) ?? ''"
            placeholder="Your response"
            @update:model-value="onText(q.id, String($event))"
          />

          <div v-else-if="q.kind === 'gap_fill'" class="text-base leading-loose">
            <template v-for="(seg, si) in gapSegments(q)" :key="si">
              <span v-if="seg.type === 'text'">{{ seg.value }}</span>
              <input
                v-else
                :value="gapVal(q.id, seg.id)"
                class="mx-1 inline-block w-32 px-2 py-1 border-[1.5px] border-border rounded-md bg-card outline-none focus:border-primary"
                @input="setGap(q.id, seg.id, ($event.target as HTMLInputElement).value)"
              />
            </template>
          </div>

          <div v-else-if="q.kind === 'matching'" class="flex flex-col gap-3">
            <div v-for="l in q.content.left ?? []" :key="l.id" class="flex items-center gap-3">
              <span class="flex-1 font-medium">{{ l.text }}</span>
              <select
                :value="matchVal(q.id, l.id)"
                class="flex-1 px-3 py-2 border-[1.5px] border-border rounded-lg bg-card outline-none focus:border-primary"
                @change="setMatch(q.id, l.id, ($event.target as HTMLSelectElement).value)"
              >
                <option value="" disabled>— choose —</option>
                <option v-for="r in q.content.right ?? []" :key="r.id" :value="r.id">
                  {{ r.text }}
                </option>
              </select>
            </div>
          </div>

          <div v-else class="text-muted-foreground">
            The “{{ q.kind }}” type is not yet supported.
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between mt-7">
        <span class="text-sm text-muted-foreground"
          >{{ answered }} out of {{ total }} have been answered</span
        >
        <Button
          class="bg-success hover:bg-success/90 text-success-foreground"
          :disabled="busy"
          @click="finish"
        >
          {{ busy ? 'Sending…' : 'Finish the test' }}
        </Button>
      </div>
    </template>
  </div>
</template>
