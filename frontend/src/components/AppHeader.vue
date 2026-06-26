<script setup lang="ts">
import { useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
function logout() { auth.logout(); router.push({ name: 'login' }) }
</script>

<template>
  <header class="sticky top-0 z-40 bg-card border-b">
    <div class="max-w-[1180px] mx-auto px-7 h-[68px] flex items-center justify-between">
      <RouterLink to="/" class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
          <span class="font-bold text-xl text-primary-foreground tracking-tight">SS</span>
        </div>
        <span class="font-semibold text-xl tracking-tight">
          <span class="text-foreground">Skill</span><span class="text-[#4f7c97]">Sprint</span>
        </span>
      </RouterLink>

      <nav class="flex items-center gap-7 text-[15px] font-medium text-[#4a6678]">
        <RouterLink to="/" class="hover:text-primary">Home</RouterLink>
      </nav>

      <button class="flex items-center gap-3 cursor-pointer" @click="logout">
        <div class="text-right leading-tight">
          <div class="text-sm font-semibold text-foreground">Sergei Dariukhin</div>
          <div class="text-xs text-muted-foreground">Student</div>
        </div>
        <div class="w-10 h-10 rounded-full bg-accent flex items-center
                    justify-center font-bold text-sm text-primary">SD</div>
      </button>
    </div>
  </header>
</template>
