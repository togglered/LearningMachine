<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
</script>

<template>
  <div class="min-h-svh flex flex-col bg-background text-foreground">
    <AppHeader />
    <main class="flex-1"><slot /></main>
    <footer class="border-t bg-card">
      <div class="max-w-[1180px] mx-auto px-7 py-7 flex items-center
                  justify-between text-sm text-muted-foreground">
        <div class="flex items-center gap-2.5">
          <div class="w-7 h-7 rounded-lg bg-primary flex items-center
                      justify-center text-[13px] font-bold text-primary-foreground">
            SS
          </div>
          <span class="text-[#5d7689] font-semibold">SkillSprint</span>
        </div>
        <span>© {{ new Date().getFullYear() }} SkillSprint · Exam Preparation Platform</span>
      </div>
    </footer>
  </div>
</template>
