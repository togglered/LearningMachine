<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listTests, type TestListItem } from '@/api/tests'
import { Button } from '@/components/ui/button'

import { useRouter } from 'vue-router'
import { startAttempt } from '@/api/attempts'

const router = useRouter()
const tests = ref<TestListItem[]>([])
const loading = ref(true)
const error = ref('')
const starting = ref<number | null>(null)

onMounted(async () => {
  try {
    tests.value = await listTests()
  } catch {
    error.value = 'Unable to load the tests'
  } finally {
    loading.value = false
  }
})

async function start(testId: number) {
  starting.value = testId
  try {
    const att = await startAttempt(testId)
    router.push({ name: 'test-run', params: { id: att.id } })
  } finally {
    starting.value = null
  }
}
</script>

<template>
  <div class="max-w-[1180px] mx-auto px-7 py-9">
    <h1 class="text-[32px] font-bold tracking-tight mb-7">Tests</h1>

    <div v-if="loading" class="text-muted-foreground">Loading…</div>
    <div v-else-if="error" class="text-destructive">{{ error }}</div>
    <div v-else-if="!tests.length" class="text-muted-foreground">
      No tests have been published yet.
    </div>
    <div v-else class="grid grid-cols-3 gap-5 max-lg:grid-cols-1">
      <div
        v-for="t in tests"
        :key="t.id"
        class="bg-card border rounded-2xl p-6 flex flex-col gap-3.5 transition hover:shadow-[0_10px_28px_rgba(20,40,55,.09)]"
      >
        <div class="font-semibold text-lg">Test #{{ t.id }}</div>
        <div class="text-sm text-muted-foreground">
          {{ t.time_limit ? `Limit: ${t.time_limit}` : 'No time limit' }}
        </div>
        <Button class="self-start mt-1" :disabled="starting === t.id" @click="start(t.id)">
          {{ starting === t.id ? 'Creating…' : 'Start the test' }}
        </Button>
      </div>
    </div>
  </div>
</template>
