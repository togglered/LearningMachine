<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card, CardHeader, CardTitle, CardDescription, CardContent,
} from '@/components/ui/card'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push({ name: 'tests' })
  } catch {
    error.value = 'Incorrect username or password'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex flex-col items-center gap-7">
    <div class="flex items-center gap-3">
      <div class="w-11 h-11 rounded-xl bg-primary flex items-center justify-center">
        <span class="font-bold text-xl text-primary-foreground tracking-tight">SS</span>
      </div>
      <span class="font-semibold text-2xl tracking-tight">
        <span class="text-foreground">Skill</span><span class="text-[#4f7c97]">Sprint</span>
      </span>
    </div>

    <Card class="w-full rounded-2xl shadow-[0_22px_54px_rgba(20,40,55,.1)]">
      <CardHeader class="text-center">
        <CardTitle class="text-2xl">Login</CardTitle>
        <CardDescription>Log in to continue your training</CardDescription>
      </CardHeader>
      <CardContent>
        <form class="flex flex-col gap-4" @submit.prevent="submit">
          <div class="flex flex-col gap-1.5">
            <label for="username" class="text-sm font-medium">Username</label>
            <Input id="username" v-model="username" placeholder="Your username"
                   autocomplete="username" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label for="password" class="text-sm font-medium">Password</label>
            <Input id="password" v-model="password" type="password"
                   placeholder="••••••••" autocomplete="current-password" />
          </div>
          <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
          <Button type="submit" class="w-full mt-1" :disabled="loading">
            {{ loading ? 'Logging in...' : 'Login' }}
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
