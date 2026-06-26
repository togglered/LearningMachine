<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'

const route = useRoute()
const layouts = { app: AppLayout, auth: AuthLayout }
const layout = computed(() => layouts[route.meta.layout ?? 'app'])
</script>

<template>
  <component :is="layout">
    <RouterView />
  </component>
</template>
